"""
vcbench_mock.py — VLM AND/OR Gate Pipeline Scaffold (Mock Activations)
=======================================================================
Mirrors gcbench_mock.py but for Vision-Language Models.

Pipeline:
  Mock image-patch activations
  → vc(k) curve (fraction of variance explained by audio-grounded = visual-grounded features)
  → AND-frac at vc_peak (image-conditional / model-grounded split)
  → Pearson r with mock CHAIR hallucination labels

Analogy to audio:
  audio phoneme frames  →  image patches (16x16 ViT-style)
  gc(k) commitment gate →  vc(k) visual commitment gate
  AND-gate (audio-grounded)  →  AND-gate (image-grounded, visual features)
  OR-gate (text-predictable)  →  OR-gate (language-prior features)
  t* (commitment layer)  →  v* (visual commitment layer)

Expected result:
  High AND-frac at v* → model uses image; correlates with low CHAIR (fewer hallucinations)
  Low AND-frac at v* → model relies on language priors → higher CHAIR scores
  Pearson r(AND-frac_v*, -CHAIR) > 0.6
"""

import numpy as np
import json
def pearsonr(x, y):
    x, y = np.array(x), np.array(y)
    xm, ym = x - x.mean(), y - y.mean()
    r = (xm * ym).sum() / (np.sqrt((xm**2).sum()) * np.sqrt((ym**2).sum()) + 1e-12)
    n = len(x)
    t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2 + 1e-12)
    from math import erfc, sqrt
    p = erfc(abs(t) / sqrt(2))
    return float(r), float(p)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
RNG_SEED = 42
N_IMAGES = 40          # number of mock images
N_PATCHES = 196        # 14×14 ViT patches (ViT-B/16 style)
N_LAYERS = 24          # transformer depth (ViT-L / LLaVA-style)
N_FEATURES = 128       # mock SAE features per token
CHAIR_NOISE = 0.15     # noise on CHAIR mock labels

rng = np.random.default_rng(RNG_SEED)

# ──────────────────────────────────────────────
# 1. Mock image-patch activations
#    Shape: (N_IMAGES, N_LAYERS, N_PATCHES, N_FEATURES)
# ──────────────────────────────────────────────
print("=== vcbench_mock.py: VLM AND/OR Gate Pipeline ===\n")
print(f"Config: {N_IMAGES} images, {N_PATCHES} patches, {N_LAYERS} layers, {N_FEATURES} features")

v_star_true = 10  # true visual commitment layer

# Base activations: small noise floor (so signals dominate)
activations = (rng.standard_normal((N_IMAGES, N_LAYERS, N_PATCHES, N_FEATURES)) * 0.1).astype(np.float32)

# Feature layout:
#   features 0-63:  AND-gate (image-conditional, high cross-patch variance when grounded)
#   features 64-127: OR-gate (language prior, low cross-patch variance = image-mean pattern)

# Per-feature amplitude multipliers (uniform [0.3, 1.7]) → smooth threshold crossing curve
and_amplitudes = rng.uniform(0.3, 1.7, N_FEATURES // 2)  # (64,) per-feature gain
or_amplitudes = rng.uniform(0.3, 1.7, N_FEATURES // 2)

for img_idx in range(N_IMAGES):
    # Grounded images: high AND-gate signal at commitment layers
    # Hallucination-prone: only OR-gate signal (language priors, no patch specificity)
    is_grounded = img_idx < N_IMAGES // 2

    for layer in range(N_LAYERS):
        # Strength envelope: Gaussian peak at v_star_true, width=2 layers
        layer_strength = np.exp(-0.5 * ((layer - v_star_true) / 2.0) ** 2)

        if is_grounded:
            # AND-gate features: each patch gets a DIFFERENT activation (high cross-patch variance)
            # Scale = per-feature amplitude * global strength * layer envelope
            for fi in range(N_FEATURES // 2):
                patch_vals = rng.standard_normal(N_PATCHES) * 3.0 * layer_strength * and_amplitudes[fi]
                activations[img_idx, layer, :, fi] += patch_vals.astype(np.float32)
            # OR-gate features: same activation across all patches (image-mean, low patch variance)
            or_signal = rng.standard_normal(N_FEATURES // 2) * 0.4
            activations[img_idx, layer, :, N_FEATURES // 2:] += or_signal[None, :].astype(np.float32)
        else:
            # AND-gate features: near-zero patch-specific variance (not using image input)
            for fi in range(N_FEATURES // 2):
                same_val = rng.standard_normal() * 0.15
                activations[img_idx, layer, :, fi] += float(same_val)
            # OR-gate features: strong image-mean signal (language prior dominant)
            or_signal = rng.standard_normal(N_FEATURES // 2) * 2.5 * layer_strength * or_amplitudes
            activations[img_idx, layer, :, N_FEATURES // 2:] += or_signal[None, :].astype(np.float32)

# ──────────────────────────────────────────────
# 2. AND/OR gate classification per feature per layer
#    AND-gate: feature variance across patches > threshold (image-conditional)
#    OR-gate: feature variance across patches ≤ threshold (language-prior)
# ──────────────────────────────────────────────
def compute_and_frac_per_layer(acts_img):
    """
    acts_img: (N_LAYERS, N_PATCHES, N_FEATURES)
    Returns: (N_LAYERS,) array of AND-frac (continuous).

    AND-frac = mean cross-patch std of AND-gate features (0-63)
               / (mean cross-patch std of ALL features + eps)
    High AND-frac → model relies more on patch-specific (image-conditional) features.
    Low AND-frac → model relies more on image-mean (language-prior) features.
    """
    eps = 1e-6
    and_frac = np.zeros(N_LAYERS)
    for layer in range(N_LAYERS):
        patch_std = acts_img[layer].std(axis=0)  # (N_FEATURES,) cross-patch std per feature
        mean_and = patch_std[:N_FEATURES // 2].mean()   # AND-gate features (image-conditional)
        mean_all = patch_std.mean()
        and_frac[layer] = mean_and / (mean_all + eps)
    return and_frac

# ──────────────────────────────────────────────
# 3. vc(k) curve: AND-frac vs layer (commitment gate)
#    v* = argmax(AND-frac) = visual commitment layer
# ──────────────────────────────────────────────
all_and_frac = []
v_stars = []

for img_idx in range(N_IMAGES):
    and_frac = compute_and_frac_per_layer(activations[img_idx])
    all_and_frac.append(and_frac)
    v_star = int(np.argmax(and_frac))
    v_stars.append(v_star)

all_and_frac = np.array(all_and_frac)  # (N_IMAGES, N_LAYERS)
mean_curve = all_and_frac.mean(axis=0)
v_star_detected = int(np.argmax(mean_curve))

print(f"\n[vc(k) Curve]")
print(f"  v* (true)     = layer {v_star_true}")
print(f"  v* (detected) = layer {v_star_detected}")
print(f"  Peak AND-frac = {mean_curve[v_star_detected]:.3f}")
print(f"  Mean AND-frac @ v* per image: {all_and_frac[:, v_star_detected].mean():.3f} ± {all_and_frac[:, v_star_detected].std():.3f}")

# ──────────────────────────────────────────────
# 4. AND-frac at v* per image → proxy for visual grounding
# ──────────────────────────────────────────────
and_frac_at_vstar = all_and_frac[:, v_star_detected]  # (N_IMAGES,)

# ──────────────────────────────────────────────
# 5. Mock CHAIR scores (hallucination metric)
#    Visually grounded images → low CHAIR (real objects cited)
#    Language-prior images → high CHAIR (hallucinated objects)
# ──────────────────────────────────────────────
chair_scores = np.zeros(N_IMAGES)
for img_idx in range(N_IMAGES):
    is_grounded = img_idx < N_IMAGES // 2
    base_chair = 0.15 if is_grounded else 0.65
    chair_scores[img_idx] = np.clip(base_chair + rng.normal(0, CHAIR_NOISE), 0, 1)

print(f"\n[CHAIR Scores]")
print(f"  Grounded images:  CHAIR = {chair_scores[:N_IMAGES//2].mean():.3f} ± {chair_scores[:N_IMAGES//2].std():.3f}")
print(f"  Hallucination:    CHAIR = {chair_scores[N_IMAGES//2:].mean():.3f} ± {chair_scores[N_IMAGES//2:].std():.3f}")

# ──────────────────────────────────────────────
# 6. Pearson r: AND-frac at v* vs -CHAIR (should be positive: high AND-frac → low CHAIR)
# ──────────────────────────────────────────────
r_and_chair, p_val = pearsonr(and_frac_at_vstar, -chair_scores)
r_direct, _ = pearsonr(and_frac_at_vstar, chair_scores)

print(f"\n[Correlation: AND-frac(v*) vs CHAIR]")
print(f"  Pearson r(AND-frac, -CHAIR) = {r_and_chair:.3f}  (p={p_val:.4f})")
print(f"  Pearson r(AND-frac,  CHAIR) = {r_direct:.3f}")

# ──────────────────────────────────────────────
# 7. Group-level summary
# ──────────────────────────────────────────────
grounded_and_frac = and_frac_at_vstar[:N_IMAGES // 2]
halluc_and_frac = and_frac_at_vstar[N_IMAGES // 2:]

print(f"\n[Group AND-frac @ v*={v_star_detected}]")
print(f"  Grounded images:     AND-frac = {grounded_and_frac.mean():.3f} ± {grounded_and_frac.std():.3f}")
print(f"  Hallucination images: AND-frac = {halluc_and_frac.mean():.3f} ± {halluc_and_frac.std():.3f}")
print(f"  Delta = {grounded_and_frac.mean() - halluc_and_frac.mean():.3f}")

# ──────────────────────────────────────────────
# 8. Layer-profile printout (every 4 layers)
# ──────────────────────────────────────────────
print(f"\n[Mean vc(k) curve — every 4 layers]")
for layer in range(0, N_LAYERS, 4):
    bar = "█" * int(mean_curve[layer] * 40)
    marker = " ← v*" if layer == v_star_detected else ""
    print(f"  Layer {layer:2d}: {mean_curve[layer]:.3f} {bar}{marker}")

# ──────────────────────────────────────────────
# 9. Validation check
# ──────────────────────────────────────────────
print(f"\n[Validation]")
checks = {
    "v* detected correctly (within ±3 layers)": abs(v_star_detected - v_star_true) <= 3,
    "Grounded AND-frac at v* > 0.6": grounded_and_frac.mean() > 0.6,
    "Pearson r(AND-frac, -CHAIR) > 0.6": r_and_chair > 0.6,
    "Delta AND-frac (grounded - halluc) > 0.1": (grounded_and_frac.mean() - halluc_and_frac.mean()) > 0.1,
    "p-value < 0.05": p_val < 0.05,
}

all_pass = True
for check, result in checks.items():
    status = "✓" if result else "✗"
    print(f"  [{status}] {check}")
    if not result:
        all_pass = False

print(f"\n{'=== ALL CHECKS PASSED ===' if all_pass else '=== SOME CHECKS FAILED ==='}")

# ──────────────────────────────────────────────
# 10. Export summary
# ──────────────────────────────────────────────
summary = {
    "artifact": "vcbench_mock",
    "task": "Q160",
    "n_images": N_IMAGES,
    "n_patches": N_PATCHES,
    "n_layers": N_LAYERS,
    "v_star_true": v_star_true,
    "v_star_detected": v_star_detected,
    "peak_and_frac": float(mean_curve[v_star_detected]),
    "pearson_r_and_neg_chair": float(r_and_chair),
    "p_value": float(p_val),
    "delta_and_frac_grounded_vs_halluc": float(grounded_and_frac.mean() - halluc_and_frac.mean()),
    "all_checks_passed": all_pass,
    "interpretation": (
        "VLM AND/OR gate scaffold validated. "
        f"v*=layer{v_star_detected} detected (true={v_star_true}). "
        f"AND-frac at v* correlates with -CHAIR (r={r_and_chair:.3f}): "
        "image-grounded features → fewer hallucinations. "
        "Pipeline ready for real LLaVA/BLIP-2 activations."
    )
}

print(f"\n[Export summary]")
print(json.dumps(summary, indent=2))
