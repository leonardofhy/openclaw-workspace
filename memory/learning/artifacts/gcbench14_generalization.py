"""
gcbench14_generalization.py — Q154

GCBench-14 Generalization: t* boundary detector for speaker turns and musical onsets.

Hypothesis:
  The cross-attention density dip (GCBench-14 proxy) is a general-purpose boundary
  signal — not limited to phoneme/word boundaries. Speaker turns and musical onsets
  should also produce detectable dips because they represent transitions between
  distinct acoustic regimes, forcing the decoder to re-anchor.

Experiment Design:
  1. Phoneme boundaries (baseline, already done) — included for comparison
  2. Speaker turns: two synthetic "speakers" (male ~120Hz, female ~220Hz) alternating
  3. Musical onsets: distinct pitched notes separated by silence gaps

Ground truth boundaries are known (synthetic), so F1 is computable.

Result format (per condition):
  {"condition": str, "n_boundaries": int, "f1": float, "precision": float, "recall": float}
"""

import sys
import os
import json
import math
import wave
import struct
import numpy as np
import warnings
warnings.filterwarnings("ignore")

ARTIFACTS_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Audio generation ───────────────────────────────────────────────────────────

def write_wav(path, audio, sr=16000):
    audio = np.clip(audio, -1.0, 1.0)
    audio_int = (audio * 32767).astype(np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int.tobytes())


def voiced_segment(freq, duration, sr=16000, harmonics=3):
    """Voiced speech-like segment at given fundamental frequency."""
    t = np.arange(int(sr * duration)) / sr
    sig = sum(
        (1.0 / (h + 1)) * np.sin(2 * np.pi * freq * (h + 1) * t)
        for h in range(harmonics)
    )
    # Amplitude envelope: quick attack + sustain + quick decay
    n = len(t)
    env = np.ones(n)
    ramp = min(int(0.05 * sr), n // 4)
    env[:ramp] = np.linspace(0, 1, ramp)
    env[-ramp:] = np.linspace(1, 0, ramp)
    return sig * env


def silence_segment(duration, sr=16000):
    return np.zeros(int(sr * duration))


def generate_phoneme_audio(path, sr=16000):
    """Baseline: 5 phoneme-like segments, 0.6s each (same as gcbench14_real)."""
    freqs = [220, 330, 280, 370, 440]
    seg_dur = 0.6
    segments = [voiced_segment(f, seg_dur, sr) for f in freqs]
    audio = np.concatenate(segments)
    boundaries_sec = [seg_dur * i for i in range(1, len(freqs))]
    write_wav(path, audio / (np.abs(audio).max() + 1e-8) * 0.8, sr)
    print(f"  [phoneme] {len(freqs)} segs, boundaries at {[round(b,2) for b in boundaries_sec]}s")
    return path, boundaries_sec, len(segments)


def generate_speaker_turn_audio(path, sr=16000):
    """
    Speaker turns: male (~120Hz) and female (~220Hz) alternating.
    3 turns × 2 speakers = 6 segments, 0.5s each.
    Boundaries at 0.5, 1.0, 1.5, 2.0, 2.5s (5 boundaries).
    """
    male_freq = 120    # Fundamental for "male" speaker
    female_freq = 220  # Fundamental for "female" speaker
    seg_dur = 0.5
    
    # Add slight pitch variation within each segment to sound more natural
    segments = []
    speakers = []
    for i in range(6):
        freq = male_freq if i % 2 == 0 else female_freq
        # Add slight jitter ±5% to fundamental
        jitter = freq * 0.05 * (np.random.rand() - 0.5)
        segments.append(voiced_segment(freq + jitter, seg_dur, sr, harmonics=4))
        speakers.append("M" if i % 2 == 0 else "F")
    
    audio = np.concatenate(segments)
    boundaries_sec = [seg_dur * i for i in range(1, len(segments))]
    write_wav(path, audio / (np.abs(audio).max() + 1e-8) * 0.8, sr)
    print(f"  [speaker_turns] speakers={speakers}, boundaries at {[round(b,2) for b in boundaries_sec]}s")
    return path, boundaries_sec, len(segments)


def generate_musical_onset_audio(path, sr=16000):
    """
    Musical onsets: discrete pitched notes with short silence gaps between them.
    4 notes (C4=261Hz, E4=330Hz, G4=392Hz, C5=523Hz), 0.5s each, 0.05s silence gap.
    Onsets at 0.55, 1.10, 1.65s (3 boundaries = onset of notes 2,3,4).
    """
    note_freqs = [261, 330, 392, 523]  # C4, E4, G4, C5
    note_dur = 0.5
    gap_dur = 0.05
    
    segments = []
    for i, freq in enumerate(note_freqs):
        # Note: sine-heavy (musical timbre)
        note = voiced_segment(freq, note_dur, sr, harmonics=5)
        segments.append(note)
        if i < len(note_freqs) - 1:
            segments.append(silence_segment(gap_dur, sr))  # inter-onset gap
    
    audio = np.concatenate(segments)
    # Boundaries = start of each note after the first (silence gap + note onset)
    boundaries_sec = []
    t = 0.0
    for i in range(len(note_freqs)):
        if i > 0:
            boundaries_sec.append(round(t, 3))
        t += note_dur + (gap_dur if i < len(note_freqs) - 1 else 0)
    
    write_wav(path, audio / (np.abs(audio).max() + 1e-8) * 0.8, sr)
    print(f"  [musical_onsets] notes=C4,E4,G4,C5, onset boundaries at {boundaries_sec}s")
    return path, boundaries_sec, len(note_freqs)


# ── Whisper boundary detection (shared) ───────────────────────────────────────

def run_boundary_detection(audio_path, label=""):
    """Extract cross-attention density from Whisper-base, return density array."""
    import whisper
    import torch
    import torch.nn.functional as F

    model = whisper.load_model("base")
    model.eval()

    # Disable SDPA to get actual qk weights
    import whisper.model as wm
    wm.MultiHeadAttention.use_sdpa = False

    step_attentions = []

    def make_hook(layer_idx):
        def hook_fn(module, input, output):
            if isinstance(output, tuple) and len(output) == 2:
                qk = output[1]
                if qk is not None and qk.ndim == 4:
                    w = F.softmax(qk.float(), dim=-1)
                    attn = w[0, :, -1, :].detach().cpu().float()  # [heads, n_audio]
                    if layer_idx >= len(step_attentions):
                        step_attentions.append([attn])
                    else:
                        step_attentions[layer_idx].append(attn)
        return hook_fn

    hooks = []
    for i, block in enumerate(model.decoder.blocks):
        h = block.cross_attn.register_forward_hook(make_hook(i))
        hooks.append(h)

    audio = whisper.load_audio(audio_path)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    options = whisper.DecodingOptions(language="en", without_timestamps=False, fp16=False)
    result = whisper.decode(model, mel, options)

    for h in hooks:
        h.remove()

    if not step_attentions or not step_attentions[0]:
        print(f"  [{label}] ⚠️  No attention weights captured.")
        return np.array([]), result.text

    n_layers = len(step_attentions)
    n_steps = len(step_attentions[0])
    THRESHOLD = 0.05

    density = []
    for step_idx in range(n_steps):
        layer_dens = []
        for layer_idx in range(n_layers):
            if step_idx < len(step_attentions[layer_idx]):
                attn = step_attentions[layer_idx][step_idx]
                frac = (attn > THRESHOLD).float().mean().item()
                layer_dens.append(frac)
        density.append(float(np.mean(layer_dens)) if layer_dens else 0.0)

    return np.array(density), result.text


# ── Boundary detector ──────────────────────────────────────────────────────────

def detect_boundaries(density, n_expected, tolerance=2):
    """
    Detect top-n_expected local dips in density curve.
    Uses soft scoring: score = mean(neighbors) - density[t].
    Returns detected step indices.
    """
    window = 2
    n = len(density)
    scores = []
    for t in range(window, n - window):
        neighbors = [density[t - w] for w in range(1, window + 1)] + \
                    [density[t + w] for w in range(1, window + 1)]
        score = float(np.mean(neighbors) - density[t])
        scores.append((t, score))
    scores.sort(key=lambda x: -x[1])
    top = [t for t, s in scores[:n_expected] if s > 0]
    top.sort()
    return top


def steps_to_seconds(steps, n_steps, audio_duration):
    """Convert decoder step indices to seconds (approximate)."""
    return [round(s / n_steps * audio_duration, 3) for s in steps]


def compute_f1(detected_sec, true_sec, tolerance_sec=0.15):
    """F1 with ±tolerance_sec slack."""
    true_set = list(true_sec)
    tp = 0
    matched = set()
    for d in detected_sec:
        for i, b in enumerate(true_set):
            if abs(d - b) <= tolerance_sec and i not in matched:
                tp += 1
                matched.add(i)
                break
    precision = tp / len(detected_sec) if detected_sec else 0.0
    recall = tp / len(true_sec) if true_sec else 0.0
    f1 = 2 * precision * recall / (precision + recall + 1e-12)
    return round(f1, 3), round(precision, 3), round(recall, 3), tp


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Q154: GCBench-14 Generalization — Speaker Turns + Musical Onsets")
    print("=" * 70)
    print()

    conditions = [
        ("phoneme",        "/tmp/gcbench14_phoneme.wav",    generate_phoneme_audio),
        ("speaker_turns",  "/tmp/gcbench14_speaker.wav",    generate_speaker_turn_audio),
        ("musical_onsets", "/tmp/gcbench14_music.wav",      generate_musical_onset_audio),
    ]

    results = []

    # Load whisper once (it will be reloaded per call, but that's OK for this script)
    for cond_name, wav_path, gen_fn in conditions:
        print(f"\n── {cond_name.upper()} ──────────────────────────────────────────────")

        # Generate audio
        _, true_boundaries_sec, n_segs = gen_fn(wav_path)
        n_expected = len(true_boundaries_sec)
        audio_duration = n_segs * (0.6 if cond_name == "phoneme" else
                                   0.5 if cond_name == "speaker_turns" else
                                   0.55)  # approx with gap

        # Extract Whisper cross-attention density
        print(f"  Running Whisper-base...")
        density, transcription = run_boundary_detection(wav_path, label=cond_name)

        if len(density) == 0:
            print(f"  ❌ No density extracted.")
            results.append({"condition": cond_name, "error": "no density", "f1": 0.0})
            continue

        n_steps = len(density)
        print(f"  Decoder steps: {n_steps} | Transcription: '{transcription[:60]}'")

        # Detect boundaries
        detected_steps = detect_boundaries(density, n_expected)
        detected_sec = steps_to_seconds(detected_steps, n_steps, audio_duration)

        f1, prec, rec, tp = compute_f1(detected_sec, true_boundaries_sec, tolerance_sec=0.2)

        print(f"  True boundaries (sec):     {[round(b, 2) for b in true_boundaries_sec]}")
        print(f"  Detected boundaries (sec): {detected_sec}")
        print(f"  TP={tp}  F1={f1:.3f}  P={prec:.3f}  R={rec:.3f}")
        print(f"  {'✅ DoD met' if f1 >= 0.6 else '⚠️  Below DoD (F1 < 0.6)'}")

        # Density trace
        print(f"\n  Density trace (step → density):")
        for t, d in enumerate(density):
            bar = "█" * int(d * 20)
            det_mark = " ← detected" if t in detected_steps else ""
            print(f"    t={t:2d}: {d:.3f} [{bar:<20}]{det_mark}")

        results.append({
            "condition": cond_name,
            "n_segments": n_segs,
            "n_boundaries": n_expected,
            "n_decoder_steps": n_steps,
            "true_boundaries_sec": true_boundaries_sec,
            "detected_boundaries_sec": detected_sec,
            "detected_steps": detected_steps,
            "tp": tp,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "transcription": transcription[:80],
            "dod_met": f1 >= 0.6,
        })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY — GCBench-14 Generalization")
    print("=" * 70)
    print(f"{'Condition':<20} {'F1':>6} {'P':>6} {'R':>6} {'DoD':>6}")
    print("-" * 50)
    for r in results:
        if "error" in r:
            print(f"{r['condition']:<20}  ERROR")
        else:
            dod = "✅" if r["dod_met"] else "❌"
            print(f"{r['condition']:<20} {r['f1']:>6.3f} {r['precision']:>6.3f} {r['recall']:>6.3f} {dod:>6}")

    # Verdict
    n_pass = sum(1 for r in results if r.get("dod_met", False))
    verdict = f"{n_pass}/{len(conditions)} conditions pass DoD (F1 ≥ 0.6)"
    print(f"\nVerdict: {verdict}")

    if n_pass >= 2:
        print("✅ GCBench-14 generalizes beyond phonemes.")
        conclusion = "GENERALIZES"
    elif n_pass == 1:
        print("⚠️  Partial generalization — phoneme-specific bias likely.")
        conclusion = "PARTIAL"
    else:
        print("❌ GCBench-14 does NOT generalize — proxy is phoneme-specific.")
        conclusion = "DOES_NOT_GENERALIZE"

    # Save
    out = {
        "experiment": "GCBench-14 Generalization (Q154)",
        "hypothesis": "Cross-attention density dip detects boundaries beyond phonemes",
        "model": "whisper-base",
        "conditions": results,
        "verdict": verdict,
        "conclusion": conclusion,
    }
    out_path = os.path.join(ARTIFACTS_DIR, "gcbench14_generalization_result.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {out_path}")
    return out


if __name__ == "__main__":
    main()
