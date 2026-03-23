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

activations = rng.standard_normal((N_IMAGES, N_LAYERS, N_PATCHES, N_FEATURES)).astype(np.float32)

# Inject visual-grounding signal into early-mid layers (layers 4-14 ~ "visual commitment zone")
# AND-gate features are high-variance patch-specific; OR-gate features are image-mean + noise
v_star_true = 10  # true visual commitment layer

for img_idx in range(N_IMAGES):
    # ground truth: images 0-19 are "visually grounded" (high AND-gate), 20-39 are "hallucination-prone"
    is_grounded = img_idx < N_IMAGES // 2
    signal_strength = 2.0 if is_grounded else 0.5

    for layer in range(max(0, v_star_true - 2), min(N_LAYERS, v_star_true + 3)):
        # AND-gate features (0-63): patch-specific, high variance across patches
        patch_specific = rng.standard_normal((N_PATCHES, N_FEATURES // 2)) * signal_strength
        activations[img_idx, layer, :, :N_FEATURES // 2] += patch_specific

        # OR-gate features (64-127): image-mean (language prior), low patch variance
        image_mean_signal = rng.standard_normal(N_FEATURES // 2) * (1.0 - signal_strength * 0.3)
        activations[img_idx, layer, :, N_FEATURES // 2:] += image_mean_signal[None, :]

# ──────────────────────────────────────────────
# 2. AND/OR gate classification per feature per layer
#    AND-gate: feature variance across patches > threshold (image-conditional)
#    OR-gate: feature variance across patches ≤ threshold (language-prior)
# ──────────────────────────────────────────────
AND_VARIANCE_THRESHOLD = 0.9  # features with cross-patch std > threshold = AND-gate

def compute_and_frac_per_layer(acts_img):
    """
    acts_img: (N_LAYERS, N_PATCHES, N_FEATURES)
    Returns: (N_LAYERS,) array of AND-frac values
    """
    and_frac = np.zeros(N_LAYERS)
    for layer in range(N_LAYERS):
        # Variance across patches for each feature
        patch_variance = acts_img[layer].std(axis=0)  # (N_FEATURES,)
        and_mask = patch_variance > AND_VARIANCE_THRESHOLD
        and_frac[layer] = and_mask.mean()
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
    "Peak AND-frac > 0.4": mean_curve[v_star_detected] > 0.4,
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
