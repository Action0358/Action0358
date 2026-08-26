"""Render light_mode.svg / dark_mode.svg for the profile README.

Pulls live counts from the GitHub API and lays them out neofetch-style next to
the ASCII portrait in assets/ascii-art.txt.

Needs a token in ACCESS_TOKEN so that private repositories are counted. A
read-only fine-grained PAT is enough: all repositories, Contents + Metadata
read. Falls back to GITHUB_TOKEN, which only sees public repositories.
"""

import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

import requests

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "assets" / "ascii-art.txt"

USER = os.environ.get("PROFILE_USER", "Action0358")
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
HEAD = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

# --- layout metrics (Consolas 16px, 20px leading) -------------------------
CHAR_W = 8.93
LINE_H = 20
PAD_X = 15
GAP = 34
COL_W = 74  # characters available to the right-hand column

THEMES = {
    "dark": dict(
        bg="#161b22", fg="#c9d1d9", key="#ffa657", val="#a5d6ff",
        dots="#616e7f", add="#3fb950", dele="#f85149",
    ),
    "light": dict(
        bg="#ffffff", fg="#24292f", key="#953800", val="#0a3069",
        dots="#8c959f", add="#1a7f37", dele="#cf222e",
    ),
}


# --- data -----------------------------------------------------------------
def rest(path, **params):
    r = requests.get(f"{API}{path}", headers=HEAD, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def profile():
    """Everything here is REST, not GraphQL, so a read-only fine-grained
    token works. GraphQL still requires a classic token."""
    me = rest("/user")
    repos, page = [], 1
    while True:
        batch = rest("/user/repos", affiliation="owner", per_page=100, page=page)
        repos += [r for r in batch if not r["fork"]]
        if len(batch) < 100:
            break
        page += 1
    return {
        "created": datetime.fromisoformat(me["created_at"].replace("Z", "+00:00")),
        "followers": me["followers"],
        "repos": len(repos),
        "private": sum(1 for r in repos if r["private"]),
        "stars": sum(r["stargazers_count"] for r in repos),
        "names": [r["name"] for r in repos],
    }


def repo_stats(names):
    """Sum this user's commits/additions/deletions across every owned repo.

    Uses REST contributor stats rather than contributionsCollection: the latter
    reports 0 for private repositories, which is most of this account.
    """
    commits = add = dele = 0
    for name in names:
        url = f"{API}/repos/{USER}/{name}/stats/contributors"
        for _ in range(8):
            r = requests.get(url, headers=HEAD, timeout=60)
            if r.status_code == 202:  # GitHub is computing the stats; retry
                time.sleep(3)
                continue
            if r.status_code != 200 or not r.text.strip():
                break
            for c in r.json() or []:
                if (c.get("author") or {}).get("login", "").lower() != USER.lower():
                    continue
                commits += c["total"]
                for wk in c["weeks"]:
                    add += wk["a"]
                    dele += wk["d"]
            break
    return commits, add, dele


def uptime(created):
    today = date.today()
    d0 = created.date()
    y = today.year - d0.year
    m = today.month - d0.month
    d = today.day - d0.day
    if d < 0:
        m -= 1
        first = today.replace(day=1)
        d += (first - timedelta(days=1)).day
    if m < 0:
        y -= 1
        m += 12
    parts = [f"{y} year{'s' * (y != 1)}", f"{m} month{'s' * (m != 1)}",
             f"{d} day{'s' * (d != 1)}"]
    return ", ".join(parts)


# --- text model -----------------------------------------------------------
class Seg:
    def __init__(self, text, cls=None):
        self.text = text
        self.cls = cls

    def __len__(self):
        return len(self.text)


def field(key, value, extra=None):
    """`. key: ....... value` with the dots stretched so values right-align."""
    segs = [Seg(". ", "cc")]
    for i, part in enumerate(key.split(".")):
        if i:
            segs.append(Seg(".", "key"))
        segs.append(Seg(part, "key"))
    segs.append(Seg(":", "key"))
    tail = extra or [Seg(value, "value")]
    used = sum(len(s) for s in segs) + sum(len(s) for s in tail)
    segs.append(Seg(" " + "." * max(1, COL_W - used - 2) + " ", "cc"))
    segs.extend(tail)
    return segs


def rule(title):
    head = f"- {title} "
    return [Seg(head, None), Seg("-" + "—" * (COL_W - len(head) - 4) + "-—-", None)]


def build_lines(p, commits, add, dele):
    loc = add - dele
    n = lambda v: f"{v:,}"
    L = []
    head = f"{USER}@github "
    L.append([Seg(head, None),
              Seg("-" + "—" * (COL_W - len(head) - 4) + "-—-", None)])
    L.append(field("OS", "macOS (Apple Silicon), Linux containers"))
    L.append(field("Uptime", uptime(p["created"])))
    L.append(field("Host", "In-house SE — HR services (Japan)"))
    L.append(field("Kernel", "Requirements, design review, UAT, maintenance"))
    L.append(field("Editor", "Neovim, VS Code, Claude Code"))
    L.append([Seg(". ", "cc")])
    L.append(field("Languages.Programming", "Go, TypeScript, JavaScript, Python"))
    L.append(field("Languages.Markup", "HTML, CSS, SQL, YAML, Markdown"))
    L.append(field("Languages.Real", "Japanese (native), English (reading)"))
    L.append([Seg(". ", "cc")])
    L.append(field("Stack.Frontend", "Next.js, React, Tailwind, TanStack Query"))
    L.append(field("Stack.Backend", "Go, Gin, REST, OpenAPI, PostgreSQL"))
    L.append(field("Stack.Infra", "Docker, Fly.io, Cloudflare Pages, Actions"))
    L.append(field("Stack.Testing", "Jest, Testing Library, MSW"))
    L.append(field("Stack.Tooling", "mise, uv, Orval, Neovim + LSP"))
    L.append([Seg(". ", "cc")])
    L.append(rule("Now"))
    L.append(field("Building", "MyAnimeLogs — anime tracking web app"))
    L.append(field("Shipping", "Beta release, October 2026"))
    L.append(field("Learning", "Frontend implementation, LP production"))
    L.append(field("Reading", "Go concurrency, React Server Components"))
    L.append([Seg(". ", "cc")])
    L.append(rule("Contact"))
    L.append(field("Email", "TBD"))
    L.append(field("X", "TBD"))
    L.append(field("LinkedIn", "TBD"))
    L.append([Seg(". ", "cc")])
    L.append(rule("GitHub Stats"))
    L.append(field("Repos", "", [
        Seg(n(p["repos"]), "value"), Seg(" {", None), Seg("Private", "key"),
        Seg(": ", None), Seg(n(p["private"]), "value"), Seg("} | ", None),
        Seg("Stars", "key"), Seg(": ", None), Seg(n(p["stars"]), "value"),
    ]))
    L.append(field("Commits", "", [
        Seg(n(commits), "value"), Seg(" | ", None), Seg("Followers", "key"),
        Seg(": ", None), Seg(n(p["followers"]), "value"),
    ]))
    L.append(field("Lines of Code on GitHub", "", [
        Seg(n(loc), "value"), Seg(" ( ", None), Seg(f"{n(add)}++", "addColor"),
        Seg(", ", None), Seg(f"{n(dele)}--", "delColor"), Seg(" )", None),
    ]))
    return L


# --- render ---------------------------------------------------------------
def render(theme, art, lines):
    t = THEMES[theme]
    art_cols = max(len(a) for a in art)
    col_x = PAD_X + int(art_cols * CHAR_W) + GAP
    width = col_x + int(COL_W * CHAR_W) + PAD_X
    height = max(len(art), len(lines)) * LINE_H + 2 * LINE_H

    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'font-family="ConsolasFallback,Consolas,monospace" '
        f'width="{width}px" height="{height}px" font-size="16px">',
        "<style>",
        "@font-face {src: local('Consolas'), local('Consolas Bold');"
        "font-family: 'ConsolasFallback'; font-display: swap; size-adjust: 109%;}",
        f".key {{fill: {t['key']};}} .value {{fill: {t['val']};}}",
        f".addColor {{fill: {t['add']};}} .delColor {{fill: {t['dele']};}}",
        f".cc {{fill: {t['dots']};}}",
        "text, tspan {white-space: pre;}",
        "</style>",
        f'<rect width="{width}px" height="{height}px" fill="{t["bg"]}" rx="15"/>',
        f'<text x="{PAD_X}" y="{LINE_H + 10}" fill="{t["fg"]}">',
    ]
    off = max(0, (len(lines) - len(art)) // 2)  # centre a short art block
    for i, row in enumerate(art):
        out.append(
            f'<tspan x="{PAD_X}" y="{(i + 1 + off) * LINE_H + 10}">{escape(row)}</tspan>'
        )
    out.append("</text>")
    out.append(f'<text x="{col_x}" y="{LINE_H + 10}" fill="{t["fg"]}">')
    for i, segs in enumerate(lines):
        y = (i + 1) * LINE_H + 10
        parts = []
        for j, s in enumerate(segs):
            attrs = f' x="{col_x}" y="{y}"' if j == 0 else ""
            cls = f' class="{s.cls}"' if s.cls else ""
            parts.append(f"<tspan{attrs}{cls}>{escape(s.text)}</tspan>")
        out.append("".join(parts))
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    art = ART.read_text().rstrip("\n").split("\n")
    if not TOKEN:
        sys.exit("no token: set ACCESS_TOKEN or GITHUB_TOKEN")

    p = profile()
    commits, add, dele = repo_stats(p["names"])
    lines = build_lines(p, commits, add, dele)

    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(theme, art, lines))
        print(f"wrote {theme}_mode.svg")


if __name__ == "__main__":
    main()
