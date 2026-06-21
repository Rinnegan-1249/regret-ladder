"""Build the static (GitHub Pages) export of the web demo into docs/.

Renders every page route from web/app.py with the SAME templates (just a
plain jinja2.Environment instead of FastAPI's Jinja2Templates - no Request
object needed for any of these pages), with static_mode=True so kuhn.html /
leduc.html render their walkthrough widgets instead of the live ones, and a
`base` path prefix for GitHub Pages project-page subpaths.

Requires scripts/build_web_static_data.py to have been run first (it
populates web/static/data/, which this script just copies verbatim).

Usage (from the repo root):
    .venv/Scripts/python.exe scripts/build_static_site.py
    .venv/Scripts/python.exe scripts/build_static_site.py --base /regret-ladder

NOTE: defaults to writing into .gh-pages-build/ (gitignored), NOT docs/ -
the repo's docs/ folder is already used for project documentation (roadmap
PDF, repo audit, structure notes). The site is deployed via a separate
gh-pages branch (see scripts/deploy_gh_pages.py), not committed on main.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import jinja2

from web.bots import list_kuhn_bots, list_leduc_bots

WEB = ROOT / "web"
TEMPLATES = WEB / "templates"
STATIC = WEB / "static"
WALKTHROUGH_MANIFEST = STATIC / "data" / "walkthroughs" / "manifest.json"

# route -> (template, output filename, extra context)
ROUTES = [
    ("index.html", "index.html", {"page": "home"}),
    ("games.html", "games.html", {"page": "games"}),
    ("foundations.html", "foundations.html", {"page": "foundations"}),
    ("regret.html", "regret.html", {"page": "regret"}),
    ("rps.html", "rps.html", {"page": "games"}),
    ("kuhn.html", "kuhn.html", {"page": "games"}),  # bots/walkthroughs added below
    ("leduc.html", "leduc.html", {"page": "games"}),  # bots/walkthroughs added below
    ("results.html", "results.html", {"page": "results"}),
    ("references.html", "references.html", {"page": "references"}),
]


def _walkthroughs(game: str) -> list[dict]:
    if not WALKTHROUGH_MANIFEST.exists():
        print(f"WARNING: {WALKTHROUGH_MANIFEST} missing - run scripts/build_web_static_data.py first.")
        return []
    return json.loads(WALKTHROUGH_MANIFEST.read_text(encoding="utf-8")).get(game, [])


def build(out_dir: Path, base: str) -> None:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    env.globals["base"] = base
    env.globals["v"] = str(int(time.time()))
    env.globals["static_mode"] = True

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    for template_name, out_name, context in ROUTES:
        ctx = dict(context)
        if template_name == "kuhn.html":
            ctx["bots"] = list_kuhn_bots()
            ctx["walkthroughs"] = _walkthroughs("kuhn")
        elif template_name == "leduc.html":
            ctx["bots"] = list_leduc_bots()
            ctx["walkthroughs"] = _walkthroughs("leduc")
        html = env.get_template(template_name).render(**ctx)
        (out_dir / out_name).write_text(html, encoding="utf-8")
        print(f"  wrote {out_dir.name}/{out_name}")

    shutil.copytree(STATIC, out_dir / "static", dirs_exist_ok=True)
    papers_src = ROOT / "Research_Papers"
    if papers_src.exists():
        shutil.copytree(papers_src, out_dir / "papers", dirs_exist_ok=True)
    figures_src = ROOT / "results" / "figures"
    if figures_src.exists():
        shutil.copytree(figures_src, out_dir / "figures", dirs_exist_ok=True)

    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Static site built at {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static GitHub Pages export.")
    parser.add_argument("--base", default="", help="URL subpath prefix, e.g. /regret-ladder")
    parser.add_argument("--out", default=str(ROOT / ".gh-pages-build"), help="Output directory")
    args = parser.parse_args()
    build(Path(args.out), args.base.rstrip("/"))


if __name__ == "__main__":
    main()
