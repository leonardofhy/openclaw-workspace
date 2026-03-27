# Q175: gc(k) / AND-frac as Epistemic Uncertainty

**Key insight**: AND-frac fits as conformal nonconformity score for ASR.
- s(x) = 1 - mean_k(AND-frac(k)) → higher = more "guessing"
- CP coverage guarantee preserved (distribution-free)
- Step-wise resolution → possible word-level uncertainty (novel contribution)
- Advantage over softmax: mechanism-grounded, no output prob needed
- Build: CP calibration on Whisper-base dev set, compare AUROC vs softmax
- Connection: Q180 (accented/distribution shift), Q174 (L* layer), T5 jailbreak detection
