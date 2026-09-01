#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""schedules/live.json（暗号化されたライブ日程データ）から公開用ページ schedules/index.html を生成。

- 復号は crypt.sh 経由（鍵はリポ外 ../shirase-lab.github.io.passwd）。
  既に平文があるなら第1引数で渡せる:  python schedules/_gen_schedules.py <plain.json>
- 公開するのは「予定（今週/開催中/近日/発表）」の“公開情報だけ”＝グループ / 公演名 / 会場（都道府県）/
  日付 / 開場開演 / genre（色分け用）。内部のマーケ項目（uchiwa_demand・sns_priority・
  fan_service_culture・notes・verified 等）は一切出力しない。
- 表示は**アプリのカレンダー画面に寄せる**: 日曜始まりの月グリッド＋公演日にジャンル色の
  連結バー（Google カレンダー風）＋その下に月別の詳細一覧。ジャンル色はアプリ
  （lib/ui/calendar_screen.dart の _genreColors）を踏襲。
- live.json を更新したら（週次）このスクリプトを再実行して schedules/index.html を再生成する。
"""
import calendar as pycal
import datetime
import html
import json
import subprocess
import sys
from datetime import date
from itertools import groupby
from pathlib import Path

HERE = Path(__file__).resolve().parent          # <repo>/schedules
ROOT = HERE.parent                              # <repo>
SITE = "https://oshimite.jp"

# 予定として公開する status（過去＝last_week 等は出さない）。表示ラベルも定義。
SHOW = {"this_week": "今週", "ongoing": "開催中", "upcoming": "近日", "announced_onsale": "発表"}
WD = ["月", "火", "水", "木", "金", "土", "日"]           # 日付表記（月曜始まり＝weekday()）
WD_SUN = ["日", "月", "火", "水", "木", "金", "土"]        # カレンダー見出し（日曜始まり）

# ジャンル → (表示名, 色)。アプリ lib/ui/calendar_screen.dart の _genreColors を踏襲。
# アプリで色未定義（tertiary フォールバック）の tobe/utaite/ebidan/kayo_idol にも web 用の色を割当。
GENRE = {
    "sakamichi":        ("坂道系",        "#8E24AA"),
    "starto_jr":        ("STARTO",        "#3949AB"),
    "tobe":             ("TOBE",          "#546E7A"),
    "kpop":             ("K-POP",         "#D81B60"),
    "hello_project":    ("ハロプロ",       "#E53935"),
    "underground_idol": ("地下アイドル",   "#00897B"),
    "idol_group_other": ("その他アイドル", "#F9A825"),
    "voice_actor_2_5d": ("声優/2.5次元",  "#00ACC1"),
    "battle_fes":       ("対バン/フェス",  "#F4511E"),
    "utaite":           ("歌い手",        "#8D6E63"),
    "ebidan":           ("EBiDAN",        "#43A047"),
    "kayo_idol":        ("歌謡アイドル",   "#C0CA33"),
}
DEFAULT_COLOR = "#FF5C8A"
MAX_LANES = 4   # 1週に積むバーの最大本数（アプリ _kMaxLanes と同じ。超過は非表示＝日セルに +N、詳細は一覧に全件）


def esc(s):
    return html.escape(str(s or ""), quote=True)


def genre_color(g):
    return GENRE.get(g, ("", DEFAULT_COLOR))[1]


def genre_label(g):
    return GENRE.get(g, (g or "", DEFAULT_COLOR))[0]


def bar_label(e):
    if e.get("performer_type") == "festival" and e.get("event_name"):
        return e["event_name"]
    return e.get("group") or e.get("event_name") or ""


def load_events():
    if len(sys.argv) > 1:                        # 平文パスが渡された場合
        return json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = subprocess.run(["bash", str(HERE / "crypt.sh"), "dec", str(HERE / "live.json"), "-"],
                         capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    if out.returncode != 0:
        raise SystemExit(f"crypt.sh dec failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def fmt_dates(dates):
    ds = sorted(dates or [])
    if not ds:
        return ""
    def part(iso):
        y, m, d = (int(x) for x in iso.split("-"))
        return m, d, WD[datetime.date(y, m, d).weekday()]
    (m0, d0, w0) = part(ds[0])
    (m1, d1, w1) = part(ds[-1])
    if ds[0] == ds[-1]:
        return f"{m0}/{d0}（{w0}）"
    if m0 == m1:
        return f"{m0}/{d0}（{w0}）–{d1}（{w1}）"
    return f"{m0}/{d0}（{w0}）–{m1}/{d1}（{w1}）"


def month_key(e):
    ds = sorted(e.get("dates") or [])
    return ds[0][:7] if ds else "9999-99"        # YYYY-MM（日付なしは末尾）


def date_set(e):
    out = set()
    for iso in e.get("dates") or []:
        try:
            out.add(date.fromisoformat(iso))
        except ValueError:
            pass
    return out


def build_calendar(y, m, evs):
    """月 (y, m) のカレンダー HTML。evs = その月に公演日を持つイベント列。
    日曜始まり・週ごとにイベントの連続公演日を1本の連結バー（ジャンル色）にして、
    重なりはレーンを縦に積む（アプリ _buildWeekSegments と同じ考え方）。"""
    dsets = [(e, date_set(e)) for e in evs]
    head = "".join(
        f'<div class="cw {"sun" if i == 0 else "sat" if i == 6 else ""}">{w}</div>'
        for i, w in enumerate(WD_SUN)
    )
    weeks = pycal.Calendar(firstweekday=6).monthdatescalendar(y, m)  # 日曜始まり・実日付
    week_html = []
    for week in weeks:
        # この週での各イベントの列 run（連続公演日）を集める
        runs = []  # (colStart, colEnd, color, label)
        for e, ds in dsets:
            cols = [i for i, dt in enumerate(week) if dt.month == m and dt in ds]
            if not cols:
                continue
            color = genre_color(e.get("genre"))
            label = bar_label(e)
            # 連続 col を run にまとめる
            s = cols[0]
            prev = cols[0]
            for c in cols[1:]:
                if c == prev + 1:
                    prev = c
                    continue
                runs.append((s, prev, color, label))
                s = prev = c
            runs.append((s, prev, color, label))
        # レーン割り当て（貪欲・列が被らない最下段へ）。MAX_LANES を超えたバーは非表示にし、
        # その run が覆う日にちに「+N」を出す（詳細は下の一覧に全件あり）。
        runs.sort(key=lambda r: (r[0], r[1]))
        lane_end = []           # レーンごとの最後の colEnd
        placed = []             # (lane, cs, ce, color, label)  ※ lane < MAX_LANES のみ
        overflow = [0] * 7      # 列（曜日）ごとの非表示バー数
        for cs_, ce_, color, label in runs:
            lane = None
            for li, end in enumerate(lane_end):
                if end < cs_:
                    lane = li
                    lane_end[li] = ce_
                    break
            if lane is None:
                lane = len(lane_end)
                lane_end.append(ce_)
            if lane < MAX_LANES:
                placed.append((lane, cs_, ce_, color, label))
            else:
                for c in range(cs_, ce_ + 1):
                    overflow[c] += 1
        nlanes = min(len(lane_end), MAX_LANES)
        # 日セル（超過があれば +N）
        cells = "".join(
            f'<div class="cd{" oth" if dt.month != m else ""}"><span class="cn">{dt.day}</span>'
            + (f'<span class="more">+{overflow[i]}</span>' if dt.month == m and overflow[i] else "")
            + "</div>"
            for i, dt in enumerate(week)
        )
        # バー
        bars = "".join(
            f'<div class="cbar" title="{esc(label)}" '
            f'style="left:calc({cs_}*100%/7 + 2px);width:calc({ce_ - cs_ + 1}*100%/7 - 4px);'
            f'top:calc(var(--numh) + {lane}*(var(--barh) + var(--barg)));background:{color}">'
            f'<span>{esc(label)}</span></div>'
            for (lane, cs_, ce_, color, label) in placed
        )
        h = f"calc(var(--numh) + {nlanes}*(var(--barh) + var(--barg)) + 8px)"
        week_html.append(f'<div class="cweek" style="height:{h}">{cells}{bars}</div>')
    return f'<div class="cal"><div class="cal-head">{head}</div>{"".join(week_html)}</div>'


CSS = """
:root{--pink:#FF5C8A;--pink-deep:#FF2E6E;--bg:#FFF0F6;--bg2:#FFE3EF;--ink:#4A2E3D;--ink-soft:#9A7886;
--display:'Mochiy Pop One',system-ui,sans-serif;--body:'M PLUS Rounded 1c',system-ui,sans-serif;
--numh:24px;--barh:16px;--barg:3px;}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--body);color:var(--ink);line-height:1.7;min-height:100vh;
background:radial-gradient(1200px 600px at 80% -10%,#FFD6E8 0%,transparent 55%),
radial-gradient(900px 500px at -10% 20%,#E6DBFF 0%,transparent 50%),var(--bg);-webkit-font-smoothing:antialiased}
a{color:var(--pink-deep);text-decoration:none}a:hover{text-decoration:underline}
header{text-align:center;padding:38px 20px 6px}
header .home{display:inline-block;color:var(--ink-soft);font-size:.9rem;margin-bottom:12px}
h1{font-family:var(--display);font-size:clamp(1.5rem,5vw,2.3rem);color:var(--pink-deep)}
header p{color:var(--ink-soft);margin-top:8px;font-size:.9rem}
main{max-width:760px;margin:0 auto;padding:16px 16px 64px}
/* ジャンル凡例 */
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;justify-content:center;margin:8px auto 4px;max-width:760px;padding:0 16px}
.legend .lg{display:inline-flex;align-items:center;gap:5px;font-size:.75rem;color:var(--ink-soft)}
.legend .lg i{width:12px;height:12px;border-radius:3px;display:inline-block;flex:0 0 auto}
/* 月ブロック */
.mon{margin-top:22px}
.mon>h2{font-family:var(--display);font-size:1.05rem;color:var(--pink-deep);padding:0 4px 6px;border-bottom:2px solid #ffd9e6}
/* カレンダー（アプリ風） */
.cal{background:#fff;border:2px solid #ffe1ec;border-radius:16px;padding:10px 10px 6px;margin:12px 0 6px}
.cal-head{display:flex}
.cal-head .cw{flex:1 1 0;text-align:center;font-size:.72rem;font-weight:700;color:var(--ink-soft);padding:2px 0}
.cal-head .cw.sun{color:#e5484d}.cal-head .cw.sat{color:#3a7bd5}
.cweek{position:relative;display:flex}
.cd{flex:1 1 0;min-width:0;text-align:center;position:relative}
.cd .cn{display:inline-block;font-size:.78rem;color:var(--ink);height:var(--numh);line-height:var(--numh)}
.cd.oth .cn{color:var(--ink-soft);opacity:.4}
.cd .more{position:absolute;right:3px;bottom:2px;font-size:.55rem;font-weight:700;color:var(--pink-deep);opacity:.85}
.cbar{position:absolute;height:var(--barh);border-radius:calc(var(--barh)/2);overflow:hidden;
display:flex;align-items:center;box-shadow:0 1px 2px rgba(0,0,0,.08)}
.cbar>span{font-size:.6rem;font-weight:700;color:#fff;white-space:nowrap;overflow:hidden;
text-overflow:ellipsis;padding:0 5px;line-height:var(--barh)}
/* 月の詳細一覧 */
.mon ul{list-style:none;margin-top:10px}
.ev{display:flex;gap:12px;background:#fff;border:2px solid #ffe1ec;border-radius:14px;padding:10px 14px;margin-top:8px}
.ev .gc{flex:0 0 6px;border-radius:3px;align-self:stretch}
.ev .d{flex:0 0 5.5em;font-weight:700;color:var(--pink-deep);font-size:.9rem}
.ev .body{display:flex;flex-direction:column;gap:2px;min-width:0}
.ev .grp{font-weight:800;font-size:.98rem}
.ev .name{font-size:.9rem}
.ev .loc{font-size:.82rem;color:var(--ink-soft)}
.ev .loc .pref{opacity:.75}
.ev .loc .opn{margin-left:8px}
.ev .st{display:inline-block;font-size:.66rem;font-weight:700;color:#fff;background:var(--pink);
border-radius:999px;padding:1px 8px;margin-left:8px;vertical-align:middle}
.ev .st-this_week,.ev .st-ongoing{background:var(--pink-deep)}
.note{max-width:760px;margin:24px auto 0;padding:0 18px;font-size:.8rem;color:var(--ink-soft);text-align:center}
footer{text-align:center;padding:24px 16px 48px;color:var(--ink-soft);font-size:.82rem}
@media (max-width:560px){
  .cd .cn{font-size:.72rem}
  .cbar>span{font-size:.55rem;padding:0 3px}
}
"""


def main():
    data = load_events()
    events = [e for e in data.get("events", []) if e.get("status") in SHOW]
    events.sort(key=lambda e: (sorted(e.get("dates") or ["9999-99-99"])[0], e.get("group", "")))

    # 凡例（実在するジャンルのみ・GENRE の並び順→未知は末尾）
    present = {e.get("genre") for e in events if e.get("genre")}
    ordered = [g for g in GENRE if g in present] + [g for g in present if g not in GENRE]
    legend = "".join(
        f'<span class="lg"><i style="background:{genre_color(g)}"></i>{esc(genre_label(g))}</span>'
        for g in ordered
    )

    sections = []
    for mk, grp in groupby(events, key=month_key):
        grp = list(grp)
        if mk == "9999-99":
            label = "日程調整中・その他"
            cal = ""
        else:
            y, m = (int(x) for x in mk.split("-"))
            label = f"{y}年{m}月"
            cal = build_calendar(y, m, grp)
        rows = []
        for e in grp:
            st = SHOW.get(e.get("status"), "")
            badge = f'<span class="st st-{esc(e.get("status"))}">{esc(st)}</span>' if st else ""
            venue = esc(e.get("venue", ""))
            pref = e.get("prefecture", "")
            loc = f'{venue}<span class="pref">（{esc(pref)}）</span>' if pref else venue
            opn = f'<span class="opn">{esc(e.get("open_start"))}</span>' if e.get("open_start") else ""
            gc = genre_color(e.get("genre"))
            rows.append(
                f'<li class="ev"><span class="gc" style="background:{gc}"></span>'
                f'<span class="d">{esc(fmt_dates(e.get("dates")))}</span>'
                f'<span class="body"><span class="grp">{esc(e.get("group",""))}</span>{badge}'
                f'<span class="name">{esc(e.get("event_name",""))}</span>'
                f'<span class="loc">{loc}{opn}</span></span></li>'
            )
        sections.append(
            f'<section class="mon"><h2>{esc(label)}</h2>{cal}<ul>{"".join(rows)}</ul></section>'
        )

    meta = data.get("meta") or {}
    updated = esc(meta.get("generated_at") or meta.get("report_week") or "")
    sub = f"最終更新 {updated}・{len(events)}公演" if updated else f"{len(events)}公演"

    page = f"""<!DOCTYPE html><html lang="ja"><head>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-N5SNNFWXR4"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-N5SNNFWXR4');</script>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ライブ日程カレンダー - 推しミテ！ 応援うちわ文字作成アプリ</title>
<meta name="description" content="アイドル・K-POP などのライブ／コンサート日程をカレンダーでまとめて確認。会場・日付をチェックして、推しミテ！で応援うちわを作ろう。">
<link rel="canonical" href="{SITE}/schedules/">
<meta property="og:title" content="ライブ日程カレンダー - 推しミテ！"><meta property="og:description" content="ライブ／コンサート日程をカレンダーでまとめて確認。応援うちわ作成アプリ 推しミテ！。">
<meta property="og:type" content="website"><meta property="og:url" content="{SITE}/schedules/">
<meta property="og:image" content="{SITE}/oshimite-fan.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/oshimite-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+One&family=M+PLUS+Rounded+1c:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><a class="home" href="/">← 推しミテ！トップ</a><h1>ライブ日程カレンダー</h1>
<p>{esc(sub)}</p></header>
<div class="legend">{legend}</div>
<main>
{"".join(sections)}
<p class="note">※ 公演情報は各公式発表に基づく参考情報です。最新・正確な情報は各公演の公式サイトでご確認ください。<br>推しミテ！で応援うちわを作って、コンビニでA3実寸プリント。全機能無料。</p>
</main>
<footer>© 2026 ShiraseLab / 推しミテ！ ・ <a href="/">トップ</a> ・ <a href="/templates/">うちわテンプレート</a></footer>
</body></html>
"""

    (HERE / "index.html").write_text(page, encoding="utf-8")
    print(f"schedules/index.html generated: {len(events)} events, "
          f"{len(sections)} months, {len(ordered)} genres")


if __name__ == "__main__":
    main()
