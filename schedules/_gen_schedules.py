#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""schedules/live.json（暗号化されたライブ日程データ）から公開用ページ schedules/index.html を生成。

- 復号は crypt.sh 経由（鍵はリポ外 ../shirase-lab.github.io.passwd）。
  既に平文があるなら第1引数で渡せる:  python schedules/_gen_schedules.py <plain.json>
- 公開するのは「予定（今週/開催中/近日/発表）」の“公開情報だけ”＝グループ / 公演名 / 会場（都道府県）/
  日付 / 開場開演。内部のマーケ項目（uchiwa_demand・sns_priority・fan_service_culture・notes・
  verified 等）は一切出力しない。
- live.json を更新したら（週次）このスクリプトを再実行して schedules/index.html を再生成する。
"""
import html
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # <repo>/schedules
ROOT = HERE.parent                              # <repo>
SITE = "https://oshimite.jp"

# 予定として公開する status（過去＝last_week 等は出さない）。表示ラベルも定義。
SHOW = {"this_week": "今週", "ongoing": "開催中", "upcoming": "近日", "announced_onsale": "発表"}
WD = ["月", "火", "水", "木", "金", "土", "日"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


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
        import datetime
        w = WD[datetime.date(y, m, d).weekday()]
        return m, d, w
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


data = load_events()
events = [e for e in data.get("events", []) if e.get("status") in SHOW]
events.sort(key=lambda e: (sorted(e.get("dates") or ["9999-99-99"])[0], e.get("group", "")))

# 月ごとにセクション化
from itertools import groupby
sections = []
for mk, grp in groupby(events, key=month_key):
    grp = list(grp)
    if mk == "9999-99":
        label = "日程調整中・その他"
    else:
        y, m = mk.split("-")
        label = f"{y}年{int(m)}月"
    rows = []
    for e in grp:
        st = SHOW.get(e.get("status"), "")
        badge = f'<span class="st st-{esc(e.get("status"))}">{esc(st)}</span>' if st else ""
        venue = esc(e.get("venue", ""))
        pref = e.get("prefecture", "")
        loc = f'{venue}<span class="pref">（{esc(pref)}）</span>' if pref else venue
        opn = f'<span class="opn">{esc(e.get("open_start"))}</span>' if e.get("open_start") else ""
        rows.append(
            f'<li class="ev"><span class="d">{esc(fmt_dates(e.get("dates")))}</span>'
            f'<span class="body"><span class="grp">{esc(e.get("group",""))}</span>{badge}'
            f'<span class="name">{esc(e.get("event_name",""))}</span>'
            f'<span class="loc">{loc}{opn}</span></span></li>'
        )
    sections.append(f'<section class="mon"><h2>{esc(label)}</h2><ul>{"".join(rows)}</ul></section>')

updated = esc((data.get("meta") or {}).get("updated") or (data.get("meta") or {}).get("generated") or "")
sub = f"最終更新 {updated}・{len(events)}公演" if updated else f"{len(events)}公演"

page = f"""<!DOCTYPE html><html lang="ja"><head>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-N5SNNFWXR4"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-N5SNNFWXR4');</script>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ライブ日程 - 推しミテ！ 応援うちわ文字作成アプリ</title>
<meta name="description" content="アイドル・K-POP などのライブ／コンサート日程まとめ。会場・日付をチェックして、推しミテ！で応援うちわを作ろう。">
<link rel="canonical" href="{SITE}/schedules/">
<meta property="og:title" content="ライブ日程 - 推しミテ！"><meta property="og:description" content="ライブ／コンサート日程まとめ。応援うちわ作成アプリ 推しミテ！。">
<meta property="og:type" content="website"><meta property="og:url" content="{SITE}/schedules/">
<meta property="og:image" content="{SITE}/oshimite-fan.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/oshimite-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+One&family=M+PLUS+Rounded+1c:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
:root{{--pink:#FF5C8A;--pink-deep:#FF2E6E;--bg:#FFF0F6;--bg2:#FFE3EF;--ink:#4A2E3D;--ink-soft:#9A7886;
--display:'Mochiy Pop One',system-ui,sans-serif;--body:'M PLUS Rounded 1c',system-ui,sans-serif;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--body);color:var(--ink);line-height:1.7;min-height:100vh;
background:radial-gradient(1200px 600px at 80% -10%,#FFD6E8 0%,transparent 55%),
radial-gradient(900px 500px at -10% 20%,#E6DBFF 0%,transparent 50%),var(--bg);-webkit-font-smoothing:antialiased}}
a{{color:var(--pink-deep);text-decoration:none}}a:hover{{text-decoration:underline}}
header{{text-align:center;padding:38px 20px 6px}}
header .home{{display:inline-block;color:var(--ink-soft);font-size:.9rem;margin-bottom:12px}}
h1{{font-family:var(--display);font-size:clamp(1.5rem,5vw,2.3rem);color:var(--pink-deep)}}
header p{{color:var(--ink-soft);margin-top:8px;font-size:.9rem}}
main{{max-width:760px;margin:0 auto;padding:16px 16px 64px}}
.mon{{margin-top:22px}}
.mon>h2{{font-family:var(--display);font-size:1.05rem;color:var(--pink-deep);padding:0 4px 6px;border-bottom:2px solid #ffd9e6}}
.mon ul{{list-style:none;margin-top:8px}}
.ev{{display:flex;gap:12px;background:#fff;border:2px solid #ffe1ec;border-radius:14px;padding:10px 14px;margin-top:8px}}
.ev .d{{flex:0 0 5.5em;font-weight:700;color:var(--pink-deep);font-size:.9rem}}
.ev .body{{display:flex;flex-direction:column;gap:2px;min-width:0}}
.ev .grp{{font-weight:800;font-size:.98rem}}
.ev .name{{font-size:.9rem}}
.ev .loc{{font-size:.82rem;color:var(--ink-soft)}}
.ev .loc .pref{{opacity:.75}}
.ev .loc .opn{{margin-left:8px}}
.ev .st{{display:inline-block;font-size:.66rem;font-weight:700;color:#fff;background:var(--pink);border-radius:999px;padding:1px 8px;margin-left:8px;vertical-align:middle}}
.ev .st-this_week,.ev .st-ongoing{{background:var(--pink-deep)}}
.note{{max-width:760px;margin:24px auto 0;padding:0 18px;font-size:.8rem;color:var(--ink-soft);text-align:center}}
footer{{text-align:center;padding:24px 16px 48px;color:var(--ink-soft);font-size:.82rem}}
</style></head><body>
<header><a class="home" href="/">← 推しミテ！トップ</a><h1>ライブ日程</h1>
<p>{esc(sub)}</p></header>
<main>
{"".join(sections)}
<p class="note">※ 公演情報は各公式発表に基づく参考情報です。最新・正確な情報は各公演の公式サイトでご確認ください。<br>推しミテ！で応援うちわを作って、コンビニでA3実寸プリント。全機能無料。</p>
</main>
<footer>© 2026 ShiraseLab / 推しミテ！ ・ <a href="/">トップ</a> ・ <a href="/templates/">うちわテンプレート</a></footer>
</body></html>
"""

(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"schedules/index.html generated: {len(events)} upcoming events across {len(sections)} months")
