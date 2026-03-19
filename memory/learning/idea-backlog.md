
## 2026-03-19 Q109 follow-up

- **phoneme_mdas.py**: CPU build. Load Whisper-base, extract SAE activations at each encoder layer for minimal-pair audio (/p/–/b/, /t/–/d/, /k/–/g/). Compute per-feature Cause(voicing) and Isolate(voicing|place) via regression. Output: layer×feature (Cause, Isolate) matrix. Add to queue when slots free up (currently at 29/25 — needs cleanup).
