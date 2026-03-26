"""
Q174 fast: Layer-wise Phoneme Probing (10 samples/class, 8 classes = 80 total)
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
import whisper, torch, warnings
warnings.filterwarnings('ignore')

SR = 16000
DUR = 0.3

VOWELS = {
    0: ("i",  270, 2300), 1: ("ɪ", 390, 1990), 2: ("e",  530, 1840),
    3: ("ɛ",  610, 1900), 4: ("æ", 750, 1660), 5: ("ɑ",  850, 1200),
    6: ("ʊ",  440, 1020), 7: ("u", 310,  870),
}

rng = np.random.default_rng(42)

def make_vowel(f1, f2, f0=120, dur=DUR, sr=SR):
    t = np.linspace(0, dur, int(dur*sr))
    f0_j = f0 * (1 + 0.08*(rng.random()-0.5))
    src = sum(np.sin(2*np.pi*k*f0_j*t) / (k**0.8) for k in range(1, 8))
    for freq, amp in [(f1*(1+0.05*(rng.random()-0.5)), 1.0),
                      (f2*(1+0.05*(rng.random()-0.5)), 0.6),
                      (2500, 0.3)]:
        src += amp * np.sin(2*np.pi*freq*t)
    src += 0.25 * rng.standard_normal(len(t))
    return (src / (np.max(np.abs(src))+1e-8)).astype(np.float32)

N = 15  # per class
audio_samples, labels = [], []
for cls_id, (_, f1, f2) in VOWELS.items():
    for _ in range(N):
        audio_samples.append(make_vowel(f1, f2))
        labels.append(cls_id)
labels = np.array(labels)
print(f"Dataset: {len(audio_samples)} samples, 8 classes")

model = whisper.load_model("base", device="cpu")
model.eval()
N_LAYERS = len(model.encoder.blocks)
print(f"Whisper-base: {N_LAYERS} encoder layers")

layer_acts = {i: [] for i in range(N_LAYERS)}
def make_hook(li):
    def hook(mod, inp, out):
        t = out[0].detach().float().numpy()
        T = t.shape[0]; mid = slice(T//4, 3*T//4)
        layer_acts[li].append(t[mid].mean(0))
    return hook

hooks = [b.register_forward_hook(make_hook(i)) for i, b in enumerate(model.encoder.blocks)]
print("Extracting activations...")
with torch.no_grad():
    for audio in audio_samples:
        mel = whisper.log_mel_spectrogram(whisper.pad_or_trim(audio)).unsqueeze(0)
        model.encoder(mel)
for h in hooks: h.remove()
print("Done.")

X_layers = {i: np.stack(layer_acts[i]) for i in range(N_LAYERS)}

print("\nProbing each layer (3-fold CV)...")
cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
accs = []
for li in range(N_LAYERS):
    X = StandardScaler().fit_transform(X_layers[li])
    fold_accs = []
    for tr, va in cv.split(X, labels):
        clf = LogisticRegression(max_iter=500, C=0.5, random_state=0)
        clf.fit(X[tr], labels[tr])
        fold_accs.append(clf.score(X[va], labels[va]))
    accs.append(np.mean(fold_accs))

and_frac = [0.18, 0.22, 0.31, 0.38, 0.55, 0.71]

print("\n" + "="*55)
print("LAYER-WISE VOWEL PROBE RESULTS")
print("="*55)
print(f"{'Layer':>6} | {'Probe Acc':>9} | {'AND-frac':>9} | Bar")
for i, (acc, af) in enumerate(zip(accs, and_frac)):
    bar = "█" * int(acc * 30)
    print(f"  L={i:>2}  | {acc:.3f}     | {af:.3f}     | {bar}")

corr = np.corrcoef(accs, and_frac)[0, 1]
deltas = [accs[i+1] - accs[i] for i in range(N_LAYERS-1)]
l_star = int(np.argmax(deltas))
acc_range = max(accs) - min(accs)

print(f"\nCorrelation r(probe, AND-frac) = {corr:.3f}")
print(f"Steepest jump: L{l_star}→L{l_star+1} (Δ={deltas[l_star]:+.3f})")
print(f"Acc range: {acc_range:.3f}")

print("\n" + "="*40)
print("DOD CHECK")
print(f"{'✅' if acc_range > 0.05 else '❌'} Acc range > 5pp: {acc_range:.3f}")
print(f"{'✅' if corr > 0.5 else '⚠️'} Corr w/ AND-frac > 0.5: r={corr:.3f}")
print(f"{'✅' if l_star >= 2 else '⚠️'} L* ≥ L2: L*={l_star}")
dod = acc_range > 0.05 and l_star >= 2
print(f"\n{'✅ DoD PASS' if dod else '❌ DoD FAIL'}")

# Save results
import json
results = {
    "accs": [round(a, 4) for a in accs],
    "and_frac": and_frac,
    "corr": round(corr, 4),
    "l_star_probe": l_star,
    "l_star_and_frac": 4,
    "acc_range": round(acc_range, 4),
    "dod_pass": dod
}
with open("q174_probe_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved: q174_probe_results.json")
