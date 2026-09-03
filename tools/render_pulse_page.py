"""Render the static AION Pulse status page from the two small public
JSON snapshots (aion-workflow-status.json, aion-brain-summary.json)
and the HTML template (pulse_template.html), then hand the output to
`Artifact.publish` -- there is no client-side rendering step any more.

Why this exists (2026-09-03): AION Pulse used to be a page that
fetched its own data live, in the viewer's browser, from
api.github.com and raw.githubusercontent.com. That turned out to be
categorically impossible -- a page published through the Artifact
platform cannot make ANY network call from the browser at all, a
platform security restriction with no per-host exception, discovered
live when the user opened the page and both sections showed a bare
fetch failure. The fix moves ALL data-fetching and rendering to
publish time instead: this script is run periodically (by Claude, on
a schedule) to pull the two already-public JSON files this repo's own
GitHub Actions workflows already produce, render them into plain
HTML fragments, and produce a fully self-contained static page with
zero runtime network calls. The page can therefore only be as fresh
as the last time this script ran and its output was republished --
see the scheduled task that calls this (not tracked in this repo)
for the actual cadence.

Usage:
    python tools/render_pulse_page.py \
        --workflow-status public/aion-workflow-status.json \
        --brain-summary public/aion-brain-summary.json \
        --template tools/pulse_template.html \
        --out /tmp/aion_pulse_rendered.html

Each of --workflow-status/--brain-summary accepts either a local file
path or an http(s) URL (fetched with urllib, no auth needed --
raw.githubusercontent.com serves both files as plain public files).
A missing/unreachable brain summary renders a friendly "not published
yet" note instead of failing the whole page; a missing/unreachable
workflow status renders a visible error box in that section instead
(there is always SOME workflow-status file once this repo's own
publish-public-summary.yml has run at least once, so treating that
one as harder-required is deliberate, not an oversight).
"""

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

CATEGORY_ORDER = ["post", "think", "approve", "growth", "infra", "other"]

MIND_LABELS = [
    ("total_memories", "ความจำทั้งหมด"),
    ("beliefs", "ความเชื่อ"),
    ("questions", "คำถามเปิด"),
    ("goals", "เป้าหมาย"),
    ("reflections", "การทบทวน"),
    ("forecasts", "การคาดการณ์"),
]

THAI_UNITS = [
    ("ปี", 31536000), ("เดือน", 2592000), ("วัน", 86400),
    ("ชั่วโมง", 3600), ("นาที", 60),
]


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def rel_time(iso_str, now=None):
    """Coarse Thai relative-time string. The page is static, so this
    freezes at render time -- acceptable since the whole page is only
    ever as fresh as the last render anyway."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return ""
    now = now or datetime.now(timezone.utc)
    diff = (now - dt).total_seconds()
    future = diff < 0
    diff = abs(diff)
    for label, secs in THAI_UNITS:
        if diff >= secs:
            n = int(diff // secs)
            return f"อีก {n} {label}" if future else f"{n} {label}ที่แล้ว"
    return "เมื่อสักครู่"


def fmt_clock(dt):
    return dt.strftime("%d %b %Y, %H:%M น.")


def load_json(source):
    """source is a local path or an http(s) URL. Returns (data, error)
    -- error is None on success, or a short string describing what
    went wrong (never raises)."""
    try:
        if source.startswith("http://") or source.startswith("https://"):
            with urlopen(source, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8")), None
        else:
            path = Path(source)
            if not path.exists():
                return None, "missing"
            return json.loads(path.read_text(encoding="utf-8")), None
    except HTTPError as exc:
        # A 404 from raw.githubusercontent.com means the file has
        # simply never been published yet (e.g. before the first
        # push/workflow run) -- a normal, expected state, not a
        # fetch failure worth alarming the viewer about.
        if exc.code == 404:
            return None, "missing"
        return None, f"HTTP {exc.code}"
    except URLError as exc:
        return None, str(exc.reason)
    except Exception as exc:  # noqa: BLE001 -- deliberately broad, see docstring
        return None, str(exc)


def render_tiles(tiles):
    t = tiles or {}
    return f'''
      <div class="tile"><div class="num">{esc(t.get("total", 0))}</div><div class="label">Workflow ทั้งหมด</div></div>
      <div class="tile ok"><div class="num">{esc(t.get("ok", 0))}</div><div class="label">ทำงานปกติ</div></div>
      <div class="tile warn"><div class="num">{esc(t.get("attn", 0))}</div><div class="label">ต้องดู</div></div>
      <div class="tile accent"><div class="num">{esc(t.get("running", 0))}</div><div class="label">กำลังรัน</div></div>
    '''


def render_groups(groups):
    if not groups:
        return '<div class="note">ไม่พบ workflow run ในช่วงที่ดึงมา</div>'

    dot_svg = '<svg viewBox="0 0 8 8"><circle cx="4" cy="4" r="4" fill="currentColor"/></svg>'
    parts = []
    for g in groups:
        cards = []
        for item in g.get("items", []):
            cls = item.get("status_class", "unknown")
            label = item.get("status_label", "ไม่ทราบสถานะ")
            dot = "" if cls == "running" else dot_svg
            href = item.get("html_url") or "https://github.com/pongsatornm1991-droid/AION/actions"
            cards.append(f'''
            <a class="card" href="{esc(href)}" target="_blank" rel="noopener">
              <div class="card-top">
                <div class="card-name">{esc(item.get("name"))}</div>
                <span class="pill {esc(cls)}">{dot}{esc(label)}</span>
              </div>
              <div class="card-path">{esc(item.get("file"))}</div>
              <div class="card-time">{esc(rel_time(item.get("created_at")))}</div>
            </a>''')
        parts.append(f'''
          <div class="group">
            <div class="group-head"><h2>{esc(g.get("label"))}</h2><span class="count">{len(g.get("items", []))}</span></div>
            <div class="cards">{"".join(cards)}</div>
          </div>''')
    return "".join(parts)


def render_moods(summary):
    states = ((summary or {}).get("state_council") or {}).get("states") or []
    if not states:
        return '<div class="empty-note">ยังไม่มีสัญญาณมู้ดให้แสดง</div>'
    parts = []
    for s in states:
        value = max(0, min(100, s.get("value", 0)))
        parts.append(f'''
      <div class="mood">
        <div class="mood-top">
          <span class="mood-label">{esc(s.get("label"))}</span>
          <span class="mood-value">{esc(s.get("value"))}</span>
        </div>
        <div class="mood-bar"><div class="mood-bar-fill" style="width:{value}%; background:{esc(s.get("color") or "var(--accent)")};"></div></div>
        <div class="mood-evidence">{esc(s.get("evidence"))}</div>
      </div>''')
    return "".join(parts)


def render_mood_disclaimer(summary):
    disclaimer = ((summary or {}).get("state_council") or {}).get("disclaimer")
    if not disclaimer:
        return ""
    return f'<div class="mood-disclaimer">{esc(disclaimer)}</div>'


def render_mindstrip(summary):
    mind = (summary or {}).get("mind") or {}
    parts = []
    for key, label in MIND_LABELS:
        parts.append(f'''
      <div class="mindstat">
        <div class="num">{esc(mind.get(key, 0))}</div>
        <div class="label">{esc(label)}</div>
      </div>''')
    return "".join(parts)


def render_thoughts(summary):
    thoughts = (summary or {}).get("thoughts") or []
    if not thoughts:
        return '<div class="empty-note">ยังไม่มีความคิดที่บันทึกไว้ในรอบนี้</div>'
    parts = []
    for t in thoughts:
        parts.append(f'''
          <div class="feed-item">
            <div class="feed-item-top">
              <span class="feed-tag">{esc(t.get("category"))}</span>
              <span class="feed-time">{esc(rel_time(t.get("timestamp")))}</span>
            </div>
            <div class="feed-content">{esc(t.get("content"))}</div>
          </div>''')
    return "".join(parts)


def render_posts(summary):
    posts = (summary or {}).get("recent_posts") or []
    if not posts:
        return '<div class="empty-note">ยังไม่มีโพสต์ที่เผยแพร่ในรอบนี้</div>'
    parts = []
    for p in posts:
        platforms = "".join(
            f'<span class="pill unknown">{name}</span>'
            for flag, name in ((p.get("instagram"), "Instagram"), (p.get("facebook"), "Facebook"), (p.get("youtube"), "YouTube"))
            if flag
        )
        parts.append(f'''
          <div class="feed-item">
            <div class="feed-item-top">
              <span class="feed-tag">โพสต์</span>
              <span class="feed-time">{esc(rel_time(p.get("timestamp")))}</span>
            </div>
            <div class="feed-content">{esc(p.get("caption") or "(ไม่มีแคปชัน)")}</div>
            <div class="feed-platforms">{platforms}</div>
          </div>''')
    return "".join(parts)


def render(workflow_status_source, brain_summary_source, template_path):
    now = datetime.now(timezone.utc)

    status, status_err = load_json(workflow_status_source)
    brain, brain_err = load_json(brain_summary_source)

    if status_err == "missing":
        gh_error_html = (
            '<div class="missing-box">ยังไม่มีข้อมูลสถานะ workflow ให้แสดง — รอ push ขึ้น GitHub '
            'และรอบแรกของ workflow publish-public-summary (รันทุกชั่วโมง)</div>'
        )
        tiles_html = render_tiles(None)
        groups_html = ""
        checked_at = "ยังไม่มีข้อมูล"
    elif status_err:
        gh_error_html = (
            f'<div class="error-box">ดึงสถานะ workflow ไม่สำเร็จตอนสร้างหน้านี้ '
            f'({esc(status_err)}) — หน้านี้จะลองใหม่อัตโนมัติในรอบถัดไป</div>'
        )
        tiles_html = render_tiles(None)
        groups_html = ""
        checked_at = "อัปเดตล่าสุด: ล้มเหลว"
    else:
        gh_error_html = ""
        tiles_html = render_tiles(status.get("tiles"))
        groups_html = render_groups(status.get("groups"))
        gen = status.get("generated_at")
        checked_at = "อัปเดตล่าสุด: " + (rel_time(gen, now) or fmt_clock(now))

    if brain_err == "missing":
        brain_error_html = (
            '<div class="missing-box">ยังไม่มีข้อมูลสมองให้แสดง — รอ push ขึ้น GitHub '
            'และรอบแรกของ workflow publish-public-summary (รันทุกชั่วโมง)</div>'
        )
        brain_updated_at = "ยังไม่มีข้อมูล"
        brain = None
    elif brain_err:
        brain_error_html = (
            f'<div class="error-box">ดึงข้อมูลสมองไม่สำเร็จตอนสร้างหน้านี้ '
            f'({esc(brain_err)}) — หน้านี้จะลองใหม่อัตโนมัติในรอบถัดไป</div>'
        )
        brain_updated_at = "อัปเดตล่าสุด: ล้มเหลว"
        brain = None
    else:
        brain_error_html = ""
        gen = brain.get("generated_at")
        brain_updated_at = "ข้อมูลล่าสุด: " + (rel_time(gen, now) or fmt_clock(now))

    template = Path(template_path).read_text(encoding="utf-8")
    replacements = {
        "%%CHECKED_AT%%": checked_at,
        "%%GH_ERROR_HTML%%": gh_error_html,
        "%%TILES_HTML%%": tiles_html,
        "%%GROUPS_HTML%%": groups_html,
        "%%BRAIN_UPDATED_AT%%": brain_updated_at,
        "%%BRAIN_ERROR_HTML%%": brain_error_html,
        "%%MOODS_HTML%%": render_moods(brain),
        "%%MOOD_DISCLAIMER_HTML%%": render_mood_disclaimer(brain),
        "%%MINDSTRIP_HTML%%": render_mindstrip(brain),
        "%%THOUGHTS_HTML%%": render_thoughts(brain),
        "%%POSTS_HTML%%": render_posts(brain),
    }
    out = template
    for token, value in replacements.items():
        out = out.replace(token, value)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--workflow-status",
        default="https://raw.githubusercontent.com/pongsatornm1991-droid/AION/main/public/aion-workflow-status.json",
    )
    parser.add_argument(
        "--brain-summary",
        default="https://raw.githubusercontent.com/pongsatornm1991-droid/AION/main/public/aion-brain-summary.json",
    )
    parser.add_argument(
        "--template",
        default=str(Path(__file__).resolve().parent / "pulse_template.html"),
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    html_out = render(args.workflow_status, args.brain_summary, args.template)
    Path(args.out).write_text(html_out, encoding="utf-8")
    print(f"Wrote {args.out} ({len(html_out)} bytes)")


if __name__ == "__main__":
    main()
