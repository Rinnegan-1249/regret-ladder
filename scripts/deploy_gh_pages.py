"""Deploy the static site (scripts/build_static_site.py's output) to the
gh-pages branch via a git worktree, without disturbing main.

Steps:
  1. Build the static site into .gh-pages-build/ (via build_static_site.build).
  2. Create/reuse a worktree at .gh-pages-worktree/ checked out on the
     gh-pages branch (created fresh from an empty/orphan-ish history if it
     doesn't exist yet, locally or on origin).
  3. Mirror the built output into that worktree and commit.
  4. Push only if --push is given - otherwise this prints the push command
     and stops, so a human reviews the diff first.

Usage (from the repo root):
    .venv/Scripts/python.exe scripts/deploy_gh_pages.py --base /regret-ladder
    .venv/Scripts/python.exe scripts/deploy_gh_pages.py --base /regret-ladder --push
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

import build_static_site  # noqa: E402

BUILD_DIR = ROOT / ".gh-pages-build"
WORKTREE_DIR = ROOT / ".gh-pages-worktree"
BRANCH = "gh-pages"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=True, **kwargs)


def ensure_worktree() -> None:
    if WORKTREE_DIR.exists():
        return
    remote_branches = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", BRANCH],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout.strip()
    if remote_branches:
        run(["git", "fetch", "origin", BRANCH])
        run(["git", "worktree", "add", str(WORKTREE_DIR), BRANCH])
    else:
        print(f"No origin/{BRANCH} yet - creating a fresh local branch.")
        run(["git", "worktree", "add", "-B", BRANCH, str(WORKTREE_DIR)])
        # Strip it down to an empty root so the site's history doesn't carry
        # the entire main tree as a starting point.
        for item in WORKTREE_DIR.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        subprocess.run(["git", "add", "-A"], cwd=WORKTREE_DIR, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initialize gh-pages branch (empty)", "--allow-empty"],
            cwd=WORKTREE_DIR, check=True,
        )


def sync_build_into_worktree() -> None:
    for item in WORKTREE_DIR.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    for item in BUILD_DIR.iterdir():
        dest = WORKTREE_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and deploy the static site to gh-pages.")
    parser.add_argument("--base", default="", help="URL subpath prefix, e.g. /regret-ladder")
    parser.add_argument("--push", action="store_true", help="Push gh-pages to origin after committing")
    args = parser.parse_args()

    print("Building static site...")
    build_static_site.build(BUILD_DIR, args.base.rstrip("/"))

    print("Preparing gh-pages worktree...")
    ensure_worktree()
    sync_build_into_worktree()

    diff = subprocess.run(
        ["git", "status", "--short"], cwd=WORKTREE_DIR, capture_output=True, text=True
    ).stdout
    if not diff.strip():
        print("No changes to deploy - gh-pages is already up to date.")
        return

    print("Changes to deploy:")
    print(diff)
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    subprocess.run(["git", "add", "-A"], cwd=WORKTREE_DIR, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Deploy static site from main@{sha}"],
        cwd=WORKTREE_DIR, check=True,
    )

    if args.push:
        subprocess.run(["git", "push", "origin", BRANCH], cwd=WORKTREE_DIR, check=True)
        print(f"Pushed to origin/{BRANCH}.")
    else:
        print(f"Committed locally on {BRANCH}. To publish:")
        print(f"  cd {WORKTREE_DIR} && git push origin {BRANCH}")
        print("(or rerun this script with --push)")


if __name__ == "__main__":
    main()
