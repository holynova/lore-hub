#!/usr/bin/env python3
"""Merge the 7 lore sites into lore-hub sub-paths.

Runs in GitHub Actions (see .github/workflows/merge.yml) after the 7 source
repos are shallow-cloned into _sources/.

Idempotent: every run rebuilds the 7 sub-paths and the shared font from
scratch, so re-running produces the same tree (no-op commit).

Layout after merge:
  /index.html                 hub homepage (committed separately)
  /assets/PingFang.ttc        the ONE shared font copy (5 sites had their own)
  /elden-ring/ ...            one sub-path per site (site files verbatim,
                              minus wrangler.jsonc, worker/, .assetsignore,
                              .gitignore, the per-site font, player.html)

Rewrites (text files only):
  - font URLs -> /assets/PingFang.ttc (absolute, shared copy)
  - old subdomain links -> new sub-paths (e.g. witcher-3-lore.xiaosang.cc/
    becomes /witcher-3/)
  - series nav gains a "全部游戏" link back to the hub (sites that have one)
"""
import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "_sources"

# (source repo, sub-path, video file relative to the site root)
SITES = [
    ("elden-ring-lore", "elden-ring", "elden_ring_lore.mp4"),
    ("witcher-3-lore", "witcher-3", "witcher_3_lore.mp4"),
    ("gta5-lore", "gta5", "gta5_lore.mp4"),
    ("rdr2-lore", "rdr2", "rdr2_lore.mp4"),
    ("cyberpunk-2077-lore", "cyberpunk-2077", "cyberpunk_2077_lore.mp4"),
    ("elden-ring-lore-video", "elden-ring-video", "out/elden_ring_lore.mp4"),
    ("dark-souls-3-lore", "dark-souls-3", "dark_souls_3_lore.mp4"),
]

# Top-level names never copied into a sub-path (replaced by the hub's own).
SKIP_NAMES = {"wrangler.jsonc", "worker", ".assetsignore", ".gitignore",
              ".git", "player.html"}
FONT_REL = Path("assets") / "PingFang.ttc"

HOST_TO_SUB = {
    "elden-ring-lore.xiaosang.cc": "elden-ring",
    "witcher-3-lore.xiaosang.cc": "witcher-3",
    "gta5-lore.xiaosang.cc": "gta5",
    "rdr2-lore.xiaosang.cc": "rdr2",
    "cyberpunk-2077-lore.xiaosang.cc": "cyberpunk-2077",
    "elden-ring-lore-video.xiaosang.cc": "elden-ring-video",
    "dark-souls-3-lore.xiaosang.cc": "dark-souls-3",
}

TEXT_EXTS = {".html", ".css", ".js", ".json", ".py", ".md", ".mjs", ".txt"}
HUB_LINK = '<a href="/" class="series-link">全部游戏</a>'
NAV_RE = re.compile(r'(<nav class="series-nav-bar"[^>]*>.*?</nav>)', re.S)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_site(repo, sub):
    src = SOURCES / repo
    dst = ROOT / sub
    if dst.exists():
        shutil.rmtree(dst)

    def ignore(dirpath, names):
        rel = Path(dirpath).relative_to(src)
        ignored = [n for n in names if n in SKIP_NAMES]
        if rel == Path("assets"):
            ignored += [n for n in names if n == "PingFang.ttc"]
        return ignored

    shutil.copytree(src, dst, ignore=ignore)
    return dst


def rewrite_text(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, ValueError):
        return 0
    orig = text
    # Font: point at the single shared copy (longest match first).
    text = text.replace("../assets/PingFang.ttc", "/assets/PingFang.ttc")
    text = text.replace("assets/PingFang.ttc", "/assets/PingFang.ttc")
    # Old subdomain links -> new sub-paths (longest host first).
    for host in sorted(HOST_TO_SUB, key=len, reverse=True):
        sub = HOST_TO_SUB[host]
        text = text.replace(f"https://{host}/", f"/{sub}/")
        text = text.replace(f"https://{host}", f"/{sub}")
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def add_hub_link(index_path):
    """Append a hub link to the series nav, if the page has one."""
    text = index_path.read_text(encoding="utf-8")
    if HUB_LINK in text:
        return False
    match = NAV_RE.search(text)
    if not match:
        return False
    nav = match.group(1)
    new_nav = nav.replace("</nav>", HUB_LINK + "</nav>", 1)
    index_path.write_text(text.replace(nav, new_nav, 1), encoding="utf-8")
    return True


def main():
    for repo, sub, _mp4 in SITES:
        if not (SOURCES / repo / "index.html").exists():
            print(f"ERROR: missing source {repo} (not cloned?)", file=sys.stderr)
            return 1

    for repo, sub, _mp4 in SITES:
        dst = copy_site(repo, sub)
        rewritten = sum(
            rewrite_text(p) for p in dst.rglob("*")
            if p.is_file() and p.suffix.lower() in TEXT_EXTS
        )
        hub = add_hub_link(dst / "index.html")
        print(f"{sub}: copied, {rewritten} files rewritten, "
              f"hub-link={'added' if hub else 'n/a'}")

    # Shared font: verify every copy is identical, keep one at /assets/.
    present = [SOURCES / repo / FONT_REL for repo, _, _ in SITES]
    present = [p for p in present if p.exists()]
    hashes = {sha256(p) for p in present}
    if len(hashes) != 1:
        print(f"WARNING: font copies differ ({len(hashes)} distinct "
              f"hashes), using the first", file=sys.stderr)
    target = ROOT / FONT_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    shutil.copyfile(present[0], target)
    print(f"font: {len(present)} copies -> 1 shared "
          f"({target.stat().st_size} bytes)")

    # Verify the merged tree (excluding _sources, which is removed anyway).
    ok = True
    for _repo, sub, mp4 in SITES:
        if not (ROOT / sub / "index.html").exists():
            print(f"ERROR: {sub}/index.html missing", file=sys.stderr)
            ok = False
        if not (ROOT / sub / mp4).exists():
            print(f"ERROR: {sub}/{mp4} missing", file=sys.stderr)
            ok = False
    fonts = [p for p in ROOT.rglob("PingFang.ttc")
             if "_sources" not in p.parts]
    if len(fonts) != 1:
        print(f"ERROR: PingFang.ttc count is {len(fonts)}, want 1",
              file=sys.stderr)
        ok = False
    total = sum(p.stat().st_size for p in ROOT.rglob("*")
                if p.is_file() and "_sources" not in p.parts
                and ".git" not in p.parts)
    print(f"total merged size: {total / 1048576:.1f} MB")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
