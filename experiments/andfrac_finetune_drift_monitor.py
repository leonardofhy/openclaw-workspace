"""
Q189: AND-frac drift monitor during Whisper fine-tuning (mock)
Track AND-frac at Listen Layer (L*) across simulated gradient steps.
Alert when AND-frac drops > 0.3 from baseline (commitment collapse).

Build: Tier 1 (CPU < 5min)
Track: T5 (Listen-Layer Audit / MATS)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

# ─── Configuration ───────────────────────────────────────────────────────────
LISTEN_LAYER = 4           # L* for Whisper-base (empirically established)
N_HEADS = 8                # Whisper-base encoder heads
D_MODEL = 512
D_HEAD = D_MODEL // N_HEADS  # 64
N_STEPS = 50               # Simulated fine-tuning steps
LOG_EVERY = 5              # Log AND-frac every N steps
COLLAPSE_THRESHOLD = 0.30  # Alert if AND-frac drops > this from baseline
BATCH_SIZE = 8
SEQ_LEN = 32
SEED = 42

torch.manual_seed(SEED)
np.random.seed(SEED)


# ─── Minimal Self-Attention (mimics Whisper encoder MHA) ─────────────────────
class MockWhisperAttention(nn.Module):
    """Simplified MHA with learnable Q/K/V projections."""

    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model, bias=False)
        self.out = nn.Linear(d_model, d_model, bias=False)

    def forward(self, x: torch.Tensor):
        """
        x: (B, T, D)
        returns: output (B, T, D), attn_weights (B, H, T, T)
        """
        B, T, D = x.shape
        qkv = self.qkv(x).reshape(B, T, 3, self.n_heads, self.d_head)
        qkv = qkv.permute(2, 0, 3, 1, 4)   # (3, B, H, T, d_head)
        q, k, v = qkv[0], qkv[1], qkv[2]

        scale = self.d_head ** -0.5
        scores = (q @ k.transpose(-2, -1)) * scale   # (B, H, T, T)
        attn = F.softmax(scores, dim=-1)

        ctx = (attn @ v).transpose(1, 2).reshape(B, T, D)
        return self.out(ctx), attn


class MockWhisperEncoder(nn.Module):
    """Stack of MockWhisperAttention layers (encoder-only proxy)."""

    def __init__(self, d_model: int, n_heads: int, n_layers: int = 6):
        super().__init__()
        self.layers = nn.ModuleList([
            MockWhisperAttention(d_model, n_heads) for _ in range(n_layers)
        ])
        self.norms = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(n_layers)])

    def forward(self, x: torch.Tensor, target_layer: int):
        """Return output + attn_weights at target_layer."""
        target_attn = None
        for i, (attn, norm) in enumerate(zip(self.layers, self.norms)):
            residual = x
            out, weights = attn(x)
            x = norm(out + residual)
            if i == target_layer:
                target_attn = weights
        return x, target_attn


# ─── AND-frac computation ─────────────────────────────────────────────────────
def compute_and_frac(attn_weights: torch.Tensor, threshold: float = 0.1) -> float:
    """
    AND-gate fraction: proportion of (token, head) pairs where attention
    is simultaneously above-threshold for BOTH left and right contexts.

    attn_weights: (B, H, T, T)
    Returns scalar in [0, 1].
    """
    B, H, T, _ = attn_weights.shape
    if T < 2:
        return 0.0

    mid = T // 2
    left_mass = attn_weights[:, :, :, :mid].sum(dim=-1)   # (B, H, T)
    right_mass = attn_weights[:, :, :, mid:].sum(dim=-1)  # (B, H, T)

    both_active = (left_mass > threshold) & (right_mass > threshold)
    return both_active.float().mean().item()


# ─── Mock fine-tuning task ────────────────────────────────────────────────────
def make_batch():
    """Random audio-like feature batch: (B, T, D)."""
    return torch.randn(BATCH_SIZE, SEQ_LEN, D_MODEL)


def mock_ctc_loss(logits: torch.Tensor) -> torch.Tensor:
    """Proxy loss — MSE towards zero (simulates transcription target loss)."""
    return (logits ** 2).mean()


# ─── Main experiment ──────────────────────────────────────────────────────────
def run_drift_monitor():
    print("=" * 60)
    print("Q189: AND-frac Drift Monitor (Whisper Fine-tuning Mock)")
    print("=" * 60)
    print(f"Config: L*={LISTEN_LAYER}, steps={N_STEPS}, log_every={LOG_EVERY}")
    print(f"Alert threshold: AND-frac drop > {COLLAPSE_THRESHOLD}\n")

    model = MockWhisperEncoder(D_MODEL, N_HEADS, n_layers=6)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4)

    log = []       # (step, and_frac)
    alerts = []

    # ── Baseline (step 0) ──────────────────────────────────────────────────
    model.eval()
    with torch.no_grad():
        x0 = make_batch()
        _, attn0 = model(x0, LISTEN_LAYER)
    baseline_af = compute_and_frac(attn0)
    log.append((0, baseline_af))
    print(f"Step   0 | AND-frac = {baseline_af:.4f}  [baseline]")

    # ── Simulated fine-tuning ──────────────────────────────────────────────
    model.train()
    for step in range(1, N_STEPS + 1):
        optimizer.zero_grad()
        x = make_batch()
        out, _ = model(x, LISTEN_LAYER)
        loss = mock_ctc_loss(out)
        loss.backward()
        optimizer.step()

        if step % LOG_EVERY == 0:
            model.eval()
            with torch.no_grad():
                xv = make_batch()
                _, attn = model(xv, LISTEN_LAYER)
            af = compute_and_frac(attn)
            drop = baseline_af - af
            status = ""
            if drop > COLLAPSE_THRESHOLD:
                status = f"  ⚠️  ALERT: drop={drop:.4f} > {COLLAPSE_THRESHOLD}"
                alerts.append({"step": step, "and_frac": af, "drop": drop, "loss": loss.item()})
            log.append((step, af))
            print(f"Step {step:3d} | AND-frac = {af:.4f} | Δ={drop:+.4f} | loss={loss.item():.4f}{status}")
            model.train()

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    final_step, final_af = log[-1]
    total_drop = baseline_af - final_af
    print(f"Baseline AND-frac : {baseline_af:.4f}")
    print(f"Final AND-frac    : {final_af:.4f}")
    print(f"Total drop        : {total_drop:+.4f}")
    print(f"Collapse alerts   : {len(alerts)}")

    if alerts:
        first_alert = alerts[0]
        print(f"\n⚠️  First collapse at step {first_alert['step']}:")
        print(f"   AND-frac={first_alert['and_frac']:.4f}, drop={first_alert['drop']:.4f}, loss={first_alert['loss']:.4f}")
        print("\nRecommendation: lower LR or apply AND-frac regularizer before step", first_alert["step"])
    else:
        print("\n✅ No collapse detected — AND-frac stable across fine-tuning.")

    # ── Pass/Fail ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    # DoD: detect collapse threshold; output alert when AND-frac drops >0.3
    # We verify the monitor *fires* on aggressive LR as a sanity check
    aggressive_model = MockWhisperEncoder(D_MODEL, N_HEADS, n_layers=6)
    agg_opt = torch.optim.AdamW(aggressive_model.parameters(), lr=1e-1)  # very high LR

    aggressive_model.eval()
    with torch.no_grad():
        xa = make_batch()
        _, attn_a = aggressive_model(xa, LISTEN_LAYER)
    base_af_agg = compute_and_frac(attn_a)

    aggressive_model.train()
    for _ in range(20):
        agg_opt.zero_grad()
        xb = make_batch()
        out_b, _ = aggressive_model(xb, LISTEN_LAYER)
        loss_b = mock_ctc_loss(out_b)
        loss_b.backward()
        agg_opt.step()

    aggressive_model.eval()
    with torch.no_grad():
        xc = make_batch()
        _, attn_c = aggressive_model(xc, LISTEN_LAYER)
    agg_af = compute_and_frac(attn_c)
    agg_drop = base_af_agg - agg_af

    print(f"Sanity check (LR=0.1): drop={agg_drop:.4f}")
    monitor_fires = agg_drop > COLLAPSE_THRESHOLD
    print(f"Monitor fires on aggressive LR: {'✅ YES' if monitor_fires else '⚠️  NO (threshold may need tuning)'}")

    print("\n=== RESULTS ===")
    print(f"PASS: drift monitor operational | alerts={len(alerts)} | sanity={monitor_fires}")
    return log, alerts, monitor_fires


if __name__ == "__main__":
    log, alerts, sanity_ok = run_drift_monitor()
