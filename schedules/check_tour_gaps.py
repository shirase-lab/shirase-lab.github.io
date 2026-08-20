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

【単レグ多都市ツアーの穴（2026-08-21 追加）】以前は「同一ツアーで2レグ以上登録」だけを
  ツアー扱いにしていた（`len(legs) < 2` は単発扱いで除外）。しかし多都市ツアーの
  “最初の1都市だけ登録して後続レグを後追いしなかった”ケースは、live 上は 1 レグ=単発に
  見えてチェックから漏れる（実例: KEY TO LIT『NEO CLASSICS』/ ACEes『V』を有明/神戸 1 レグ
  だけ登録し、次の有明8/20-23・大阪8/29-30 を取りこぼした=2026-08-21 発覚）。対策:
  event_name が “ツアー / Tour” を含む（=ツアー名を持つ）イベントは、登録が 1 レグでも
  ツアー扱いにして検査する。1 レグしか無い場合は最終レグが古くても拾えるよう検知窓を
  広く取る（--single-window-days、既定90日。21日窓だと 39 日前終了の ACEes 有明が漏れた）。

使い方:
  python schedules/check_tour_gaps.py <live_plain_or_merged.json> \
      [--today YYYY-MM-DD] [--window-days N] [--single-window-days N]

終了コード: 0=警告なし / 1=要確認ツアーあり(標準出力に一覧)。
※これは“確定エラー”ではなく“公式で確認して埋めろ”の gate。ツアーが本当に千秋楽まで
  終わっている場合は誤検知しうる(window を過ぎれば自然に消える)。誤検知でも
  「確認した上で足すものが無い」と判断できれば無視してよい。
"""
import argparse
import datetime
import json
import re
import sys

# 「これから/開催中」を意味する status（これが1つでもあれば“先のレグあり”とみなす）
FORWARD = {"this_week", "ongoing", "upcoming", "announced_onsale"}

# event_name が「ツアー名」を持つ = 単発でなく多都市ツアーの1レグとみなすシグナル
TOUR_NAME_RE = re.compile(r"ツアー|tour", re.IGNORECASE)


def is_tourlike(ev):
    """event_name が『ツアー / Tour / TOUR』を含めば、登録が1レグでもツアー扱いにする。
    多都市ツアーの最初の1都市だけ登録して後続を取りこぼす事故を、単発誤検知抑制の
    `len(legs) < 2` 除外で見逃さないため。"""
    return bool(TOUR_NAME_RE.search(ev.get("event_name", "") or ""))


# 都道府県＋レグ名に単独で現れがちな主要都市。末尾に素で付く「地名」を落として束ねる。
PREF_CITY = set(
    "北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 "
    "新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 "
    "和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 長崎 熊本 大分 "
    "宮崎 鹿児島 沖縄 横浜 神戸 名古屋 仙台 札幌 博多 幕張 さいたま".split()
)
# 末尾に付くレグ修飾語（都市名の前後に付く）。ツアー基幹名には含めない。
_LEG_QUAL = re.compile(
    r"[\s　]*(?:千秋楽|ファイナル|FINAL|Final|開幕|初日|追加公演|アンコール|ENCORE|Encore)$"
)
_KOEN = re.compile(r"[\s　]*[^\s　]*公演$")            # 「大阪公演」「公演」
_PAREN = re.compile(r"[\s　]*[（(][^）)]*[）)]$")        # 末尾の（…）/(…)


def tour_key(ev):
    """(group, ツアー基幹名) を返す。レグ名の表記ゆれ（「横浜公演」／素の「大阪」／
    「新潟 千秋楽」／「…（ファイナル）」等）を末尾から反復除去して同一ツアーに束ねる。

    ※以前は末尾「<地名>公演」しか落とさず、素の地名（"…大阪"）や "公演" の後ろの括弧、
      "千秋楽" 語で束ね損ねて同一ツアーが分裂し、実在する先レグを見落として大量に誤検知した
      （2026-08-21 に Kis-My-Ft2/NEWS 等で発覚）。基幹名まで正規化して束ねる。"""
    name = ev.get("event_name", "") or ""
    m = re.search(r"「(.+?)」", name)
    if m:
        return (ev.get("group", ""), m.group(1))
    title = name
    for _ in range(8):  # 末尾修飾を安定するまで剥ぐ（多重修飾: "…大阪公演（ファイナル）"）
        prev = title
        title = _PAREN.sub("", title).rstrip()          # 末尾（…）
        title = _LEG_QUAL.sub("", title).rstrip()       # 千秋楽/ファイナル/アンコール等
        title = _KOEN.sub("", title).rstrip()           # <地名>公演/公演
        mm = re.search(r"[\s　]([^\s　]+)$", title)      # 素の末尾地名（都道府県/主要都市）
        if mm and mm.group(1) in PREF_CITY:
            title = title[: mm.start()].rstrip()
        if title == prev:
            break
    return (ev.get("group", ""), title.strip() or name)


def max_date(ev):
    ds = [d for d in ev.get("dates", []) if d]
    return max(ds) if ds else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="live 平文 or merged {meta,events}")
    ap.add_argument("--today", help="YYYY-MM-DD（既定: meta.generated_at → 実行日）")
    ap.add_argument("--window-days", type=int, default=21,
                    help="複数レグ登録済みツアー: 直近この日数以内に最終レグが終わっていれば“継続の疑い”（既定21）")
    ap.add_argument("--single-window-days", type=int, default=90,
                    help="ツアー名を持つが1レグしか登録が無い場合の広い窓（既定90。後追い漏れは古くなりがち）")
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
        # ツアー扱いの条件: 2レグ以上登録済み、または（1レグでも）event_name がツアー名を持つ。
        # 後者が「多都市ツアーの1都市だけ登録して後続を取りこぼした」穴を塞ぐ。
        multi = len(legs) >= 2
        if not multi and not any(is_tourlike(ev) for ev in legs):
            continue  # ツアー名も持たない真の単発イベントは対象外（誤検知抑制）
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
        # 1レグしか無いツアーは後追い漏れが古くなりがちなので広い窓で拾う
        window = a.window_days if multi else a.single_window_days
        if today - datetime.timedelta(days=window) <= last_d < today:
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
