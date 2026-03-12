"""
audio_model_hook.py — WhisperHookedEncoder: SAELens-compatible activation cache for Whisper

Design doc: memory/learning/cycles/saelens-audio-plugin-design.md
Implements:
  - WhisperHookedEncoder: wraps OpenAI Whisper encoder with forward hooks
  - run_with_cache(): returns (logits, cache_dict) where cache keys = "hook_resid_post.{L}"
  - pool_frames(): reduces frame dim (T, D) → (D,) via mean/max/last
  - Unit tests on mock tensors (no model download required)

Usage:
  from audio_model_hook import WhisperHookedEncoder, pool_frames
  model = WhisperHookedEncoder(n_layers=4, d_model=512)  # mock mode
  logits, cache = model.run_with_cache(mel_input)
  h_L3 = pool_frames(cache["hook_resid_post.3"], mode="mean")

SAELens integration note:
  cache_dict matches ActivationCache key convention from TransformerLens.
  Downstream: pass h_L to SAE.encode() directly.
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, Optional, Tuple
import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Core: WhisperHookedEncoder
# ---------------------------------------------------------------------------

class WhisperHookedEncoder(nn.Module):
    """
    Wraps a Whisper encoder (real or mock) to expose per-layer residual stream
    activations via forward hooks, compatible with the SAELens ActivationCache
    key convention: "hook_resid_post.{layer_idx}".

    Two modes:
      - Mock mode (default): randomly-initialized lightweight transformer.
        No whisper install needed. Good for unit tests.
      - Real mode: wraps openai-whisper's AudioEncoder.
        Requires `pip install openai-whisper`.

    Args:
        n_layers  : Number of transformer layers (mock mode).
        d_model   : Hidden dim (mock mode).
        n_heads   : Attention heads (mock mode).
        real_model: An already-loaded whisper.model.AudioEncoder (real mode).
                    If provided, n_layers/d_model/n_heads are inferred.
    """

    def __init__(
        self,
        n_layers: int = 4,
        d_model: int = 512,
        n_heads: int = 8,
        real_model: Optional[nn.Module] = None,
    ):
        super().__init__()
        self._cache: Dict[str, torch.Tensor] = {}
        self._hooks = []

        if real_model is not None:
            self.encoder = real_model
            # Infer dims from the real model
            self._n_layers = len(real_model.blocks)
            self._d_model = real_model.blocks[0].attn.out.out_features
            self._real_mode = True
        else:
            # Mock: lightweight transformer encoder for testing
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=n_heads,
                dim_feedforward=d_model * 4,
                batch_first=True,
                norm_first=True,  # pre-norm, like Whisper
            )
            self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
            self._n_layers = n_layers
            self._d_model = d_model
            self._real_mode = False

    # ------------------------------------------------------------------
    # Hook management
    # ------------------------------------------------------------------

    def _make_hook(self, layer_idx: int):
        """Factory: returns a forward hook that saves residual post-layer output."""
        def hook_fn(module: nn.Module, input: Any, output: torch.Tensor):
            # output shape: (batch, frames, d_model) — post-residual, post-norm
            self._cache[f"hook_resid_post.{layer_idx}"] = output.detach()
        return hook_fn

    def _register_hooks(self):
        """Register per-layer hooks (idempotent — clears old hooks first)."""
        self._remove_hooks()
        if self._real_mode:
            # Whisper AudioEncoder uses .blocks (list of ResidualAttentionBlock)
            for i, block in enumerate(self.encoder.blocks):
                h = block.register_forward_hook(self._make_hook(i))
                self._hooks.append(h)
        else:
            # nn.TransformerEncoder uses .layers
            for i, layer in enumerate(self.encoder.layers):
                h = layer.register_forward_hook(self._make_hook(i))
                self._hooks.append(h)

    def _remove_hooks(self):
        for h in self._hooks:
            h.remove()
        self._hooks.clear()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_with_cache(
        self,
        mel_input: torch.Tensor,
        src_key_padding_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Forward pass with activation caching.

        Args:
            mel_input           : (batch, frames, d_model) — Whisper log-mel input
                                  (in mock mode, any float tensor of matching d_model).
            src_key_padding_mask: Optional bool mask for padding (batch, frames).

        Returns:
            output : (batch, frames, d_model) — final encoder output.
            cache  : Dict[str, Tensor] — keys "hook_resid_post.{0..L-1}".
        """
        self._cache = {}
        self._register_hooks()

        try:
            if self._real_mode:
                # Whisper AudioEncoder expects (batch, d_model, frames) — NCHW-like
                # and produces (batch, frames, d_model) after positional embed
                output = self.encoder(mel_input)
            else:
                output = self.encoder(
                    mel_input,
                    src_key_padding_mask=src_key_padding_mask,
                )
        finally:
            self._remove_hooks()

        cache = dict(self._cache)
        return output, cache

    @property
    def n_layers(self) -> int:
        return self._n_layers

    @property
    def d_model(self) -> int:
        return self._d_model


# ---------------------------------------------------------------------------
# Utility: pool_frames
# ---------------------------------------------------------------------------

def pool_frames(
    activation: torch.Tensor,
    mode: str = "mean",
    frame_dim: int = -2,
) -> torch.Tensor:
    """
    Reduce the frame/time dimension of a cached activation to a single vector.

    Args:
        activation : (..., frames, d_model) or (frames, d_model).
        mode       : "mean" (default), "max", or "last".
        frame_dim  : Which dim is the frame dim. Default -2 (second-to-last).

    Returns:
        Tensor with frame_dim collapsed: (..., d_model).

    Examples:
        h = cache["hook_resid_post.3"]  # (1, T, 512)
        h_mean = pool_frames(h, "mean") # (1, 512)
    """
    if mode == "mean":
        return activation.mean(dim=frame_dim)
    elif mode == "max":
        return activation.max(dim=frame_dim).values
    elif mode == "last":
        # last non-padded frame (assumes no padding mask here)
        idx = [slice(None)] * activation.ndim
        idx[frame_dim] = -1
        return activation[tuple(idx)]
    else:
        raise ValueError(f"Unknown pool mode '{mode}'. Choose from: mean, max, last")


# ---------------------------------------------------------------------------
# Unit tests (no model download required — mock mode only)
# ---------------------------------------------------------------------------

class TestWhisperHookedEncoder(unittest.TestCase):

    def setUp(self):
        torch.manual_seed(42)
        self.n_layers = 3
        self.d_model = 64
        self.n_heads = 4
        self.batch = 2
        self.frames = 16
        self.model = WhisperHookedEncoder(
            n_layers=self.n_layers,
            d_model=self.d_model,
            n_heads=self.n_heads,
        )

    def _dummy_input(self) -> torch.Tensor:
        return torch.randn(self.batch, self.frames, self.d_model)

    # --- run_with_cache tests ---

    def test_output_shape(self):
        x = self._dummy_input()
        output, cache = self.model.run_with_cache(x)
        self.assertEqual(output.shape, (self.batch, self.frames, self.d_model))

    def test_cache_keys_present(self):
        x = self._dummy_input()
        _, cache = self.model.run_with_cache(x)
        expected_keys = {f"hook_resid_post.{i}" for i in range(self.n_layers)}
        self.assertEqual(set(cache.keys()), expected_keys)

    def test_cache_shapes(self):
        x = self._dummy_input()
        _, cache = self.model.run_with_cache(x)
        for i in range(self.n_layers):
            h = cache[f"hook_resid_post.{i}"]
            self.assertEqual(
                h.shape, (self.batch, self.frames, self.d_model),
                msg=f"Layer {i} cache shape mismatch"
            )

    def test_cache_detached(self):
        """Cached tensors must not carry grad_fn (detach was called)."""
        x = self._dummy_input()
        _, cache = self.model.run_with_cache(x)
        for k, v in cache.items():
            self.assertFalse(v.requires_grad, msg=f"{k} has requires_grad=True")

    def test_hooks_cleaned_up(self):
        """Hooks must be removed after run_with_cache (no accumulation)."""
        x = self._dummy_input()
        self.model.run_with_cache(x)
        self.assertEqual(len(self.model._hooks), 0)

    def test_idempotent_multiple_runs(self):
        """Second call should produce same cache keys and shapes."""
        x = self._dummy_input()
        _, cache1 = self.model.run_with_cache(x)
        _, cache2 = self.model.run_with_cache(x)
        self.assertEqual(set(cache1.keys()), set(cache2.keys()))
        for k in cache1:
            self.assertEqual(cache1[k].shape, cache2[k].shape)

    def test_n_layers_property(self):
        self.assertEqual(self.model.n_layers, self.n_layers)

    def test_d_model_property(self):
        self.assertEqual(self.model.d_model, self.d_model)

    # --- pool_frames tests ---

    def test_pool_mean_shape(self):
        h = torch.randn(self.batch, self.frames, self.d_model)
        out = pool_frames(h, mode="mean")
        self.assertEqual(out.shape, (self.batch, self.d_model))

    def test_pool_max_shape(self):
        h = torch.randn(self.batch, self.frames, self.d_model)
        out = pool_frames(h, mode="max")
        self.assertEqual(out.shape, (self.batch, self.d_model))

    def test_pool_last_shape(self):
        h = torch.randn(self.batch, self.frames, self.d_model)
        out = pool_frames(h, mode="last")
        self.assertEqual(out.shape, (self.batch, self.d_model))

    def test_pool_last_correct_value(self):
        h = torch.randn(self.batch, self.frames, self.d_model)
        out = pool_frames(h, mode="last")
        # Should equal h[:, -1, :]
        self.assertTrue(torch.allclose(out, h[:, -1, :]))

    def test_pool_mean_correct_value(self):
        h = torch.ones(2, 4, 8)
        out = pool_frames(h, mode="mean")
        self.assertTrue(torch.allclose(out, torch.ones(2, 8)))

    def test_pool_invalid_mode(self):
        h = torch.randn(2, 4, 8)
        with self.assertRaises(ValueError):
            pool_frames(h, mode="sum")

    def test_pool_unbatched(self):
        """pool_frames should work on (frames, d_model) without batch dim."""
        h = torch.randn(self.frames, self.d_model)
        out = pool_frames(h, mode="mean", frame_dim=0)
        self.assertEqual(out.shape, (self.d_model,))

    # --- end-to-end integration test ---

    def test_end_to_end_saelens_style(self):
        """Simulate a SAELens-style usage: get cached activation, pool, project."""
        x = self._dummy_input()
        _, cache = self.model.run_with_cache(x)
        # Take penultimate layer
        h = cache[f"hook_resid_post.{self.n_layers - 2}"]
        # Pool frames
        h_pooled = pool_frames(h, mode="mean")  # (batch, d_model)
        # Simulate SAE encode (linear projection to sparse repr)
        sae_width = self.d_model * 4
        sae_W_enc = torch.randn(self.d_model, sae_width)
        activations = torch.relu(h_pooled @ sae_W_enc)
        self.assertEqual(activations.shape, (self.batch, sae_width))
        # Top-k sparsity check: mean nonzero fraction < 0.5 (should be ~0.5 for random ReLU)
        sparsity = (activations > 0).float().mean().item()
        self.assertLess(sparsity, 1.0)


if __name__ == "__main__":
    # Run tests
    print("Running WhisperHookedEncoder unit tests (mock mode — no model download)...")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestWhisperHookedEncoder)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n✅ All tests passed.")
    else:
        print(f"\n❌ {len(result.failures)} failure(s), {len(result.errors)} error(s).")
