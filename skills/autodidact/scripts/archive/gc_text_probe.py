"""
gc_text_probe.py — Cross-modal gc(k) probe for text LLMs (GPT-2)

Measures "guessing coefficient" at each token position k:
  gc_text(k, L) = change in top-1 confidence when prefix tokens are zeroed out at layer L

Usage (Tier 1, CPU):
  python3 gc_text_probe.py --prompt "The cat sat on the mat" --model gpt2
  python3 gc_text_probe.py --prompt "Attention is all you need" --model gpt2 --plot

Outputs:
  - gc_values: list of (position, gc_score) for each token
  - boundary_layer estimate
  - Optional: ASCII plot or PNG if matplotlib available

Requirements (CPU-only, no GPU needed):
  pip install transformers torch  # ~500MB, one-time

Author: autodidact c-20260309-1045
"""

import argparse
import sys
import json
import time


def compute_gc_text(prompt: str, model_name: str = "gpt2", layers_to_probe: list = None):
    """
    Compute gc(k) for each token in prompt.

    Strategy:
    1. Run model normally → get P_full(k) per position
    2. For each position k, zero out embeddings at positions 0..k-1 in selected layer L
       (simulates "prior only" — model sees no prefix context up to layer L)
    3. gc(k) = 1 - (prob_change / max_possible_change)

    Simplified version for scaffold: use attention mask ablation as proxy.
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        print("ERROR: transformers + torch not installed.")
        print("Install with: pip install transformers torch")
        return None

    print(f"Loading {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, output_attentions=True)
    model.eval()

    tokens = tokenizer.encode(prompt, return_tensors="pt")
    token_strings = [tokenizer.decode([t]) for t in tokens[0]]
    N = tokens.shape[1]

    print(f"Prompt: {repr(prompt)}")
    print(f"Tokens ({N}): {token_strings}")

    results = []

    with torch.no_grad():
        # Full forward pass
        out_full = model(tokens, output_attentions=False)
        logits_full = out_full.logits[0]  # (N, vocab)
        probs_full = torch.softmax(logits_full, dim=-1)

        for k in range(1, N):
            # Ablation: zero out prefix (positions 0..k-1) via attention mask
            # This is a proxy for "prior only" — forces model to predict from position k alone
            mask = torch.ones(1, N, dtype=torch.long)
            mask[0, :k] = 0  # mask out prefix

            out_ablated = model(tokens, attention_mask=mask, output_attentions=False)
            logits_ablated = out_ablated.logits[0]
            probs_ablated = torch.softmax(logits_ablated, dim=-1)

            # gc(k) = how much does prediction CHANGE when we mask the prefix?
            # High gc → model relied on prefix → "listening"
            # Low gc → model doesn't change → "guessing from prior"
            top_token_full = probs_full[k - 1].argmax().item()
            p_full = probs_full[k - 1, top_token_full].item()
            p_ablated = probs_ablated[k - 1, top_token_full].item()

            gc_k = p_full - p_ablated  # positive = model used context
            # Normalize to [0, 1]
            gc_k_norm = max(0.0, min(1.0, (gc_k + 1.0) / 2.0))

            results.append({
                "position": k,
                "token": token_strings[k],
                "gc": round(gc_k, 4),
                "gc_norm": round(gc_k_norm, 4),
                "p_full": round(p_full, 4),
                "p_ablated": round(p_ablated, 4),
            })

    return results, token_strings


def estimate_boundary(results):
    """Find position where gc(k) crosses 0.5 (context-reliant half the time)."""
    if not results:
        return None
    crossing = None
    for r in results:
        if r["gc_norm"] >= 0.5:
            crossing = r["position"]
            break
    return crossing


def ascii_plot(results):
    """Simple ASCII bar chart of gc values."""
    print("\n--- gc(k) per token position ---")
    for r in results:
        bar = "█" * int(r["gc_norm"] * 20)
        print(f"  {r['position']:2d} {r['token']:12s} {bar:<20} {r['gc_norm']:.3f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Cross-modal gc(k) probe for text LLMs")
    parser.add_argument("--prompt", default="The cat sat on the mat because it was tired")
    parser.add_argument("--model", default="gpt2", help="HuggingFace model name")
    parser.add_argument("--plot", action="store_true", help="Show ASCII plot")
    parser.add_argument("--output", help="Save results to JSON file")
    args = parser.parse_args()

    start = time.time()
    results, tokens = compute_gc_text(args.prompt, args.model)

    if results is None:
        sys.exit(1)

    boundary = estimate_boundary(results)

    print(f"\nResults: {len(results)} positions analyzed")
    print(f"Boundary (gc≥0.5 first at): position {boundary} ({tokens[boundary] if boundary else 'N/A'})")
    print(f"Elapsed: {time.time() - start:.1f}s")

    if args.plot:
        ascii_plot(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump({
                "model": args.model,
                "prompt": args.prompt,
                "tokens": tokens,
                "gc_values": results,
                "boundary_position": boundary,
            }, f, indent=2)
        print(f"Saved to {args.output}")

    # Summary for cross-modal table
    gc_mean = sum(r["gc_norm"] for r in results) / len(results) if results else 0
    print(f"\n--- Cross-modal table row ---")
    print(f"model={args.model}  modality=text  mean_gc={gc_mean:.3f}  boundary_pos={boundary}")


if __name__ == "__main__":
    main()
