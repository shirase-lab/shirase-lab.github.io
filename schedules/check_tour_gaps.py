#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""schedules/check_tour_gaps.py — 多都市ツアーの「レグ取りこぼし」検出リンタ。

週次ジョブ(daily_update.md)が、ツアーの一部レグだけ拾って次のレグを取りこぼす
事故を機械的に検出する gate。

実例(2026-08-03): なにわ男子 ND⁵ の大阪レグ(7/28-29)を last_week に降格した回で、
次の横浜アリーナ(8/5-7=当週)レグを登録し忘れ、当週のなにわが 0 件になった。
「全9都市45公演」の発表済みツアーなのに、live 側はレグを後追いで1つずつ拾う作りで、
1レグが last_week に落ちた瞬間ツアーが今週から消えた。

外部の公式日程はこのスクリプトは持てないので、構造から次の“事故シグネチャ”を検出する:
  「同一ツアーが最近(既定21日以内)まで開催されていたのに、
   this_week / ongoing / upcoming / announced_onsale の“先のレグ”が1つも無い」
= 継続レグ未登録の疑い。→ 公式日程で確認し、欠けているレグを found.json に足して再マージ。

使い方:
  python schedules/check_tour_gaps.py <live_plain_or_merged.json> [--today YYYY-MM-DD] [--window-days N]

終了コード: 0=警告なし / 1=要確認ツアーあり(標準出力に一覧)。
※これは“確定エラー”ではなく“公式で確認して埋めろ”の gate。ツアーが本当に千秋楽まで
  終わっている場合は誤検知しうる(window-days=21 を過ぎれば自然に消える)。誤検知でも
  「確認した上で足すものが無い」と判断できれば無視してよい。
"""
import argparse
import datetime
import json
import re
import sys

# 「これから/開催中」を意味する status（これが1つでもあれば“先のレグあり”とみなす）
FORWARD = {"this_week", "ongoing", "upcoming", "announced_onsale"}


def tour_key(ev):
    """(group, ツアー名) を返す。ツアー名は event_name の「…」内、無ければ末尾の
    「<地名>公演」を落とした基幹名。単独公演どうしを同一ツアーに束ねるためのキー。"""
    name = ev.get("event_name", "") or ""
    m = re.search(r"「(.+?)」", name)
    if m:
        title = m.group(1)
    else:
        # 例: "真夏の全国ツアー2026 大阪公演" -> "真夏の全国ツアー2026"
        title = re.sub(r"[\s　]*\S+公演$", "", name).strip() or name
    return (ev.get("group", ""), title)


def max_date(ev):
    ds = [d for d in ev.get("dates", []) if d]
    return max(ds) if ds else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="live 平文 or merged {meta,events}")
    ap.add_argument("--today", help="YYYY-MM-DD（既定: meta.generated_at → 実行日）")
    ap.add_argument("--window-days", type=int, default=21,
                    help="直近この日数以内に最終レグが終わっていれば“継続の疑い”とする（既定21）")
    a = ap.parse_args()

    with open(a.src, encoding="utf-8") as f:
        doc = json.load(f)
    if isinstance(doc, list):
        events = doc
    elif isinstance(doc, dict):
        events = doc.get("events", [])
    else:
        events = []

    if a.today:
        today = datetime.date.fromisoformat(a.today)
    else:
        gen = (doc.get("meta", {}) or {}).get("generated_at") if isinstance(doc, dict) else None
        today = datetime.date.fromisoformat(gen) if gen else datetime.date.today()

    # ツアー単位に束ねる
    tours = {}
    for ev in events:
        tours.setdefault(tour_key(ev), []).append(ev)

    flagged = []
    for (group, title), legs in tours.items():
        if len(legs) < 2:
            continue  # 単独の一発イベントはツアー扱いしない（誤検知抑制）
        has_forward = any(
            (ev.get("status") in FORWARD) or ((max_date(ev) or "") >= today.isoformat())
            for ev in legs
        )
        if has_forward:
            continue  # 先のレグ or 開催中レグがある = 健全
        last = max((max_date(ev) or "" for ev in legs), default="")
        if not last:
            continue
        last_d = datetime.date.fromisoformat(last)
        if today - datetime.timedelta(days=a.window_days) <= last_d < today:
            flagged.append((group, title, last, legs))

    if not flagged:
        print("check_tour_gaps: OK — 継続レグ未登録の疑いは無し (today=%s)" % today.isoformat())
        return 0

    print("check_tour_gaps: ⚠ 継続レグ未登録の疑い %d 件 (today=%s)" % (len(flagged), today.isoformat()))
    print("  → 各ツアーの公式日程(公式サイト/会場公式)を確認し、欠けている this_week/upcoming レグを")
    print("    found.json に足して再マージすること。本当に千秋楽済みなら無視可。")
    for group, title, last, legs in flagged:
        print("  - %s「%s」: 最終レグ=%s、this_week/upcoming/ongoing レグ無し（登録レグ %d 本）" % (
            group, title, last, len(legs)))
        for ev in sorted(legs, key=lambda e: max_date(e) or ""):
            print("      · %s〜%s %s [%s]" % (
                (ev.get("dates") or ["?"])[0], (ev.get("dates") or ["?"])[-1],
                ev.get("venue", "?"), ev.get("status", "?")))
    return 1


if __name__ == "__main__":
    sys.exit(main())
