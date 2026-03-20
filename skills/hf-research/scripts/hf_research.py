#!/usr/bin/env python3
"""HF Research CLI — upload, download, search, and track Hugging Face Hub assets.

Usage:
    hf_research.py upload --repo REPO_ID --path LOCAL_PATH [--commit-msg TEXT] [--private] [--exp EXP-ID]
    hf_research.py download --repo REPO_ID [--out PATH] [--type model|dataset|space]
    hf_research.py search QUERY [--type model|dataset] [--limit N] [--task TASK]
    hf_research.py status REPO_ID [--type model|dataset|space]
    hf_research.py push-exp EXP-ID --repo REPO_ID [--checkpoint PATH] [--note TEXT]
    hf_research.py log [--exp EXP-ID] [--limit N]
"""

import argparse
import json
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: resolve workspace root and shared module
# ---------------------------------------------------------------------------

def _find_workspace() -> Path:
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.home() / ".openclaw" / "workspace"


WORKSPACE = _find_workspace()
sys.path.insert(0, str(WORKSPACE / "skills" / "shared"))

from jsonl_store import JsonlStore  # noqa: E402

push_store = JsonlStore("memory/hf-research/pushes.jsonl", prefix="HFP")
exp_store = JsonlStore("memory/experiments/experiments.jsonl", prefix="EXP")

HF_API = "https://huggingface.co/api"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run_hf(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run the `hf` CLI and return the CompletedProcess."""
    cmd = ["hf", *args]
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def hf_api_get(path: str) -> dict | list:
    """Fetch JSON from the HF API."""
    url = f"{HF_API}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "hf-research/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_upload(args) -> int:
    """Upload a local path to HF Hub using the `hf` CLI."""
    local_path = Path(args.path)
    if not local_path.exists():
        print(f"❌ Path not found: {args.path}", file=sys.stderr)
        return 1

    hf_args = ["upload", args.repo, str(local_path)]
    if args.commit_msg:
        hf_args += ["--commit-message", args.commit_msg]
    if args.private:
        hf_args.append("--private")

    print(f"⬆️  Uploading {local_path} → {args.repo} …")
    result = run_hf(*hf_args)

    if result.returncode != 0:
        print(f"❌ Upload failed:\n{result.stderr}", file=sys.stderr)
        return 1

    if result.stdout:
        print(result.stdout.rstrip())

    # Log the push
    record = push_store.append({
        "repo": args.repo,
        "type": "model",
        "local_path": str(local_path),
        "commit_msg": args.commit_msg or "",
        "exp_id": args.exp or None,
        "note": "",
        "pushed_at": now_iso(),
    })
    print(f"✅ Logged as {record['id']} — {args.repo}")

    # Backlink onto experiment record if given
    if args.exp:
        updated = exp_store.update(args.exp, {"hf_repo": args.repo})
        if updated:
            print(f"   Linked to {args.exp}")
        else:
            print(f"⚠️  Experiment {args.exp} not found — push logged but not linked", file=sys.stderr)
    return 0


def cmd_download(args) -> int:
    """Download a repo from HF Hub using the `hf` CLI."""
    hf_args = ["download", args.repo]
    if args.out:
        hf_args += ["--local-dir", args.out]

    repo_type = args.type or "model"
    if repo_type != "model":
        hf_args += ["--repo-type", repo_type]

    print(f"⬇️  Downloading {args.repo} ({repo_type}) …")
    result = run_hf(*hf_args)

    if result.returncode != 0:
        print(f"❌ Download failed:\n{result.stderr}", file=sys.stderr)
        return 1

    if result.stdout:
        print(result.stdout.rstrip())
    print(f"✅ Downloaded {args.repo}" + (f" → {args.out}" if args.out else ""))
    return 0


def cmd_search(args) -> int:
    """Search models or datasets via the HF Hub API."""
    repo_type = args.type or "model"
    params: dict[str, str | int] = {"search": args.query, "limit": args.limit or 10}
    if args.task:
        params["pipeline_tag"] = args.task

    endpoint = "models" if repo_type == "model" else "datasets"
    qs = urllib.parse.urlencode(params)
    try:
        results = hf_api_get(f"{endpoint}?{qs}")
    except Exception as exc:
        print(f"❌ Search failed: {exc}", file=sys.stderr)
        return 1

    if not results:
        print(f"🔍 No {repo_type}s found for '{args.query}'.")
        return 0

    print(f"🔍 {repo_type.capitalize()}s matching '{args.query}' ({len(results)} results):\n")
    for item in results:
        repo_id = item.get("id") or item.get("modelId") or "?"
        downloads = item.get("downloads", item.get("downloadCount", "?"))
        likes = item.get("likes", "?")
        tags = ", ".join((item.get("tags") or item.get("cardData", {}).get("tags") or [])[:5])
        task = item.get("pipeline_tag", "")
        print(f"  📦 {repo_id}")
        if task:
            print(f"     task: {task}")
        if tags:
            print(f"     tags: {tags}")
        print(f"     ⬇️  {downloads}  ❤️  {likes}")
        print()
    return 0


def cmd_status(args) -> int:
    """Check the status of a model, dataset, or Space on HF Hub."""
    repo_type = args.type or "model"
    endpoint_map = {"model": "models", "dataset": "datasets", "space": "spaces"}
    endpoint = endpoint_map.get(repo_type, "models")

    try:
        info = hf_api_get(f"{endpoint}/{args.repo_id}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(f"❌ {args.repo_id} not found on HF Hub ({repo_type})", file=sys.stderr)
        else:
            print(f"❌ API error {exc.code}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ Status check failed: {exc}", file=sys.stderr)
        return 1

    repo_id = info.get("id") or info.get("modelId") or args.repo_id
    print(f"📊 {repo_type.capitalize()}: {repo_id}")
    print(f"   Author  : {info.get('author', '?')}")
    print(f"   Private : {info.get('private', False)}")
    print(f"   Downloads: {info.get('downloads', '?')}")
    print(f"   Likes   : {info.get('likes', '?')}")

    if repo_type == "space":
        runtime = info.get("runtime", {})
        stage = runtime.get("stage", "?")
        hardware = runtime.get("hardware", {}).get("current", "?")
        print(f"   Stage   : {stage}")
        print(f"   Hardware: {hardware}")

    last_modified = info.get("lastModified") or info.get("updatedAt", "?")
    print(f"   Updated : {last_modified}")

    tags = (info.get("tags") or [])[:8]
    if tags:
        print(f"   Tags    : {', '.join(tags)}")

    url = f"https://huggingface.co/{repo_id}"
    print(f"   URL     : {url}")
    return 0


def cmd_push_exp(args) -> int:
    """Upload a checkpoint and link the push to an experiment entry."""
    exp = exp_store.find(args.exp_id)
    if not exp:
        print(f"❌ Experiment {args.exp_id} not found in experiment-manager", file=sys.stderr)
        return 1

    print(f"🔗 Pushing results for {args.exp_id}: {exp.get('name', '?')}")

    # Upload checkpoint if provided
    if args.checkpoint:
        local_path = Path(args.checkpoint)
        if not local_path.exists():
            print(f"❌ Checkpoint path not found: {args.checkpoint}", file=sys.stderr)
            return 1

        hf_args = ["upload", args.repo, str(local_path),
                   "--commit-message", f"[{args.exp_id}] {args.note or 'push via hf-research'}"]
        print(f"⬆️  Uploading checkpoint {local_path} → {args.repo} …")
        result = run_hf(*hf_args)
        if result.returncode != 0:
            print(f"❌ Upload failed:\n{result.stderr}", file=sys.stderr)
            return 1
        if result.stdout:
            print(result.stdout.rstrip())

    # Log the push
    record = push_store.append({
        "repo": args.repo,
        "type": "model",
        "local_path": args.checkpoint or "",
        "commit_msg": args.note or "",
        "exp_id": args.exp_id,
        "note": args.note or "",
        "pushed_at": now_iso(),
    })

    # Backlink on experiment
    exp_store.update(args.exp_id, {"hf_repo": args.repo})

    print(f"✅ {record['id']} — {args.exp_id} → {args.repo}")
    if args.note:
        print(f"   Note: {args.note}")
    return 0


def cmd_log(args) -> int:
    """Show push history."""
    pushes = push_store.load()
    if args.exp:
        pushes = [p for p in pushes if p.get("exp_id") == args.exp]
    if args.limit:
        pushes = pushes[-args.limit:]

    if not pushes:
        print("📋 No pushes logged yet.")
        return 0

    print(f"📋 HF pushes ({len(pushes)}):\n")
    for p in pushes:
        exp_label = f" [{p['exp_id']}]" if p.get("exp_id") else ""
        note = f" — {p['note']}" if p.get("note") else ""
        print(f"  {p['id']}{exp_label} → {p['repo']}")
        print(f"     {p.get('pushed_at', '?')}{note}")
        if p.get("local_path"):
            print(f"     src: {p['local_path']}")
        print()
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HF Research — Hugging Face Hub operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd")

    # upload
    p = sub.add_parser("upload", help="Upload local path to HF Hub")
    p.add_argument("--repo", required=True, help="HF repo ID, e.g. user/model-name")
    p.add_argument("--path", required=True, help="Local file or directory to upload")
    p.add_argument("--commit-msg", help="Commit message")
    p.add_argument("--private", action="store_true", help="Create private repo")
    p.add_argument("--exp", help="Link to experiment ID (e.g. EXP-001)")

    # download
    p = sub.add_parser("download", help="Download repo from HF Hub")
    p.add_argument("--repo", required=True, help="HF repo ID")
    p.add_argument("--out", help="Local output directory")
    p.add_argument("--type", choices=["model", "dataset", "space"], default="model")

    # search
    p = sub.add_parser("search", help="Search models or datasets on HF Hub")
    p.add_argument("query", help="Search query")
    p.add_argument("--type", choices=["model", "dataset"], default="model")
    p.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    p.add_argument("--task", help="Filter by pipeline task (e.g. automatic-speech-recognition)")

    # status
    p = sub.add_parser("status", help="Check HF Hub repo status")
    p.add_argument("repo_id", help="HF repo ID")
    p.add_argument("--type", choices=["model", "dataset", "space"], default="model")

    # push-exp
    p = sub.add_parser("push-exp", help="Push experiment result to HF Hub")
    p.add_argument("exp_id", help="Experiment ID (e.g. EXP-001)")
    p.add_argument("--repo", required=True, help="Target HF repo ID")
    p.add_argument("--checkpoint", help="Local checkpoint path to upload")
    p.add_argument("--note", help="Short note about this push")

    # log
    p = sub.add_parser("log", help="Show push history")
    p.add_argument("--exp", help="Filter by experiment ID")
    p.add_argument("--limit", type=int, help="Max entries to show")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.cmd:
        parser.print_help()
        return 1

    dispatch = {
        "upload": cmd_upload,
        "download": cmd_download,
        "search": cmd_search,
        "status": cmd_status,
        "push-exp": cmd_push_exp,
        "log": cmd_log,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
