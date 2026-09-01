#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""schedules/live.json（暗号化されたライブ日程データ）から公開用ページ schedules/index.html を生成。

- 復号は crypt.sh 経由（鍵はリポ外 ../shirase-lab.github.io.passwd）。
  既に平文があるなら第1引数で渡せる:  python schedules/_gen_schedules.py <plain.json>
- 公開するのは「予定（今週/開催中/近日/発表）」の“公開情報だけ”＝グループ / 公演名 / 会場（都道府県）/
  日付 / 開場開演 / genre（色分け用）。内部のマーケ項目（uchiwa_demand・sns_priority・
  fan_service_culture・notes・verified 等）は一切出力しない。
- 表示は **1つの切替式カレンダー**（FullCalendar・前月/次月/今日ナビ）。公演日にジャンル色バー
  （連続公演日は連結）、混雑日は「+N more」。ジャンル色はアプリ（lib/ui/calendar_screen.dart の
  _genreColors）を踏襲。カレンダーの下に月別の詳細一覧（会場・日時）＝JS 無効/クローラ向けにも全件を
  静的 HTML で残す（SEO 維持）。
- live.json を更新したら（週次）このスクリプトを再実行して schedules/index.html を再生成する。
"""
import datetime
import html
import json
import subprocess
import sys
from datetime import date, timedelta
from itertools import groupby
from pathlib import Path

HERE = Path(__file__).resolve().parent          # <repo>/schedules
ROOT = HERE.parent                              # <repo>
SITE = "https://oshimite.jp"
FC_VER = "6.1.15"                                # FullCalendar (CDN)

# 予定として公開する status（過去＝last_week 等は出さない）。表示ラベルも定義。
SHOW = {"this_week": "今週", "ongoing": "開催中", "upcoming": "近日", "announced_onsale": "発表"}
WD = ["月", "火", "水", "木", "金", "土", "日"]           # 日付表記（月曜始まり＝weekday()）

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


def date_runs(dates):
    """公演日を連続する run にまとめる。[(start_date, end_date), ...]（両端含む）。"""
    ds = sorted({date.fromisoformat(x) for x in (dates or []) if _is_iso(x)})
    runs = []
    for d in ds:
        if runs and (d - runs[-1][1]).days == 1:
            runs[-1][1] = d
        else:
            runs.append([d, d])
    return runs


def _is_iso(x):
    try:
        date.fromisoformat(x)
        return True
    except (ValueError, TypeError):
        return False


def fc_events(events):
    """FullCalendar 用イベント配列。連続公演日は1本（end は排他＝翌日）。全日イベント。"""
    out = []
    lo = hi = None
    for e in events:
        color = genre_color(e.get("genre"))
        title = bar_label(e)
        venue = e.get("venue", "")
        pref = e.get("prefecture", "")
        opn = e.get("open_start", "")
        detail = venue + (f"（{pref}）" if pref else "") + (f" {opn}" if opn else "")
        for start, end in date_runs(e.get("dates")):
            lo = start if lo is None or start < lo else lo
            hi = end if hi is None or end > hi else hi
            out.append({
                "title": title,
                "start": start.isoformat(),
                "end": (end + timedelta(days=1)).isoformat(),   # FC の end は排他
                "allDay": True,
                "color": color,
                "extendedProps": {"detail": detail, "status": e.get("status", ""),
                                  "genre": e.get("genre", "")},
            })
    return out, (lo.isoformat() if lo else ""), (hi.isoformat() if hi else "")


CSS = """
:root{--pink:#FF5C8A;--pink-deep:#FF2E6E;--bg:#FFF0F6;--bg2:#FFE3EF;--ink:#4A2E3D;--ink-soft:#9A7886;
--display:'Mochiy Pop One',system-ui,sans-serif;--body:'M PLUS Rounded 1c',system-ui,sans-serif;}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--body);color:var(--ink);line-height:1.7;min-height:100vh;
background:radial-gradient(1200px 600px at 80% -10%,#FFD6E8 0%,transparent 55%),
radial-gradient(900px 500px at -10% 20%,#E6DBFF 0%,transparent 50%),var(--bg);-webkit-font-smoothing:antialiased}
a{color:var(--pink-deep);text-decoration:none}a:hover{text-decoration:underline}
header{text-align:center;padding:38px 20px 6px}
header .home{display:inline-block;color:var(--ink-soft);font-size:.9rem;margin-bottom:12px}
h1{font-family:var(--display);font-size:clamp(1.5rem,5vw,2.3rem);color:var(--pink-deep)}
header p{color:var(--ink-soft);margin-top:8px;font-size:.9rem}
main{max-width:820px;margin:0 auto;padding:16px 16px 64px}
/* ジャンル絞り込みチップ（トグル式） */
.legend{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:10px auto 4px;max-width:820px;padding:0 16px}
.fchip{display:inline-flex;align-items:center;gap:6px;font-family:var(--body);font-size:.76rem;font-weight:700;
color:var(--ink-soft);background:#fff;border:1.6px solid #ffd9e6;border-radius:999px;padding:5px 12px;cursor:pointer;
line-height:1.2;transition:background .15s,color .15s,border-color .15s}
.fchip i{width:11px;height:11px;border-radius:3px;display:inline-block;flex:0 0 auto}
.fchip:hover{border-color:var(--pink)}
.fchip.on{background:var(--pink);border-color:var(--pink);color:#fff}
.fchip.all.on{background:var(--pink-deep);border-color:var(--pink-deep)}
/* FullCalendar 外枠（アプリ風のピンク基調） */
#cal{background:#fff;border:2px solid #ffe1ec;border-radius:16px;padding:12px;margin:14px 0 6px}
#cal .fc .fc-toolbar-title{font-family:var(--display);color:var(--pink-deep);font-size:1.1rem}
#cal .fc .fc-button-primary{background:var(--pink);border-color:var(--pink);font-weight:700;
box-shadow:none;text-transform:none}
#cal .fc .fc-button-primary:hover{background:var(--pink-deep);border-color:var(--pink-deep)}
#cal .fc .fc-button-primary:disabled{background:#ffc2d6;border-color:#ffc2d6}
#cal .fc .fc-button-primary:not(:disabled):active,
#cal .fc .fc-button-primary:not(:disabled).fc-button-active{background:var(--pink-deep);border-color:var(--pink-deep)}
#cal .fc .fc-daygrid-day.fc-day-today{background:#fff2f7}
#cal .fc .fc-col-header-cell-cushion{color:var(--ink-soft);font-weight:700}
#cal .fc .fc-day-sun .fc-col-header-cell-cushion{color:#e5484d}
#cal .fc .fc-day-sat .fc-col-header-cell-cushion{color:#3a7bd5}
#cal .fc .fc-daygrid-day-number{color:var(--ink);font-weight:600}
#cal .fc .fc-event{border:none;font-weight:700;font-size:.72rem}
#cal .fc .fc-more-link{color:var(--pink-deep);font-weight:700}
.calnote{max-width:820px;margin:2px auto 0;padding:0 18px;font-size:.76rem;color:var(--ink-soft);text-align:center}
/* 月別の詳細一覧（JS 無効/クローラ向けにも全件） */
.mon{margin-top:22px}
.mon>h2{font-family:var(--display);font-size:1.05rem;color:var(--pink-deep);padding:0 4px 6px;border-bottom:2px solid #ffd9e6}
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
.listhead{text-align:center;margin-top:30px;color:var(--ink-soft);font-size:.86rem}
.note{max-width:820px;margin:24px auto 0;padding:0 18px;font-size:.8rem;color:var(--ink-soft);text-align:center}
footer{text-align:center;padding:24px 16px 48px;color:var(--ink-soft);font-size:.82rem}
"""

JS = """
document.addEventListener('DOMContentLoaded', function () {
  var el = document.getElementById('cal');
  if (!el || typeof FullCalendar === 'undefined') return;
  var first = %FIRST%, last = %LAST%;
  var today = new Date().toISOString().slice(0, 10);
  var initial = (first && today < first) ? first : ((last && today > last) ? last : today);
  var ALL = window.__LIVE_EVENTS__ || [];
  var active = {};                       // 選択中ジャンル（空＝すべて）
  function activeCount(){ return Object.keys(active).length; }
  function filtered(){
    var n = activeCount();
    return n ? ALL.filter(function(e){ return active[(e.extendedProps || {}).genre]; }) : ALL;
  }
  var cal = new FullCalendar.Calendar(el, {
    initialView: 'dayGridMonth',
    initialDate: initial,
    locale: 'ja',
    firstDay: 0,
    height: 'auto',
    displayEventTime: false,
    dayMaxEvents: 4,
    headerToolbar: { left: 'prev,next today', center: 'title', right: '' },
    events: ALL,
    eventDidMount: function (info) {
      var d = info.event.extendedProps.detail;
      if (d) info.el.setAttribute('title', info.event.title + ' — ' + d);
    }
  });
  cal.render();

  var chips = Array.prototype.slice.call(document.querySelectorAll('.fchip'));
  function apply(){
    var n = activeCount();
    // カレンダー: 現ソースを外して絞り込み済みを再投入
    cal.getEventSources().forEach(function(s){ s.remove(); });
    cal.addEventSource(filtered());
    // 一覧の行
    Array.prototype.forEach.call(document.querySelectorAll('.ev'), function(li){
      var g = li.getAttribute('data-genre');
      li.style.display = (!n || active[g]) ? '' : 'none';
    });
    // 中身が0の月セクションは隠す
    Array.prototype.forEach.call(document.querySelectorAll('.mon'), function(sec){
      var vis = Array.prototype.some.call(sec.querySelectorAll('.ev'), function(li){ return li.style.display !== 'none'; });
      sec.style.display = vis ? '' : 'none';
    });
    // チップの選択状態
    chips.forEach(function(c){
      var g = c.getAttribute('data-genre');
      if (c.classList.contains('all')) c.classList.toggle('on', n === 0);
      else c.classList.toggle('on', !!active[g]);
    });
  }
  chips.forEach(function(c){
    c.addEventListener('click', function(){
      var g = c.getAttribute('data-genre');
      if (c.classList.contains('all')) active = {};
      else if (active[g]) delete active[g];
      else active[g] = true;
      apply();
    });
  });
});
"""


def main():
    data = load_events()
    events = [e for e in data.get("events", []) if e.get("status") in SHOW]
    events.sort(key=lambda e: (sorted(e.get("dates") or ["9999-99-99"])[0], e.get("group", "")))

    # ジャンル絞り込みチップ（実在するジャンルのみ・GENRE の並び順→未知は末尾）。
    # トグル式（複数OR・「すべて」で解除）。JS 無効でも全件表示のまま（チップは無効化されるだけ）。
    present = {e.get("genre") for e in events if e.get("genre")}
    ordered = [g for g in GENRE if g in present] + [g for g in present if g not in GENRE]
    chips = ['<button type="button" class="fchip all on" data-genre="">すべて</button>']
    chips += [
        f'<button type="button" class="fchip" data-genre="{esc(g)}">'
        f'<i style="background:{genre_color(g)}"></i>{esc(genre_label(g))}</button>'
        for g in ordered
    ]
    legend = "".join(chips)

    fcev, first, last = fc_events(events)
    events_json = json.dumps(fcev, ensure_ascii=False).replace("</", "<\\/")

    # 月別の詳細一覧（静的・全件）
    sections = []
    for mk, grp in groupby(events, key=month_key):
        grp = list(grp)
        if mk == "9999-99":
            label = "日程調整中・その他"
        else:
            y, m = (int(x) for x in mk.split("-"))
            label = f"{y}年{m}月"
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
                f'<li class="ev" data-genre="{esc(e.get("genre",""))}">'
                f'<span class="gc" style="background:{gc}"></span>'
                f'<span class="d">{esc(fmt_dates(e.get("dates")))}</span>'
                f'<span class="body"><span class="grp">{esc(e.get("group",""))}</span>{badge}'
                f'<span class="name">{esc(e.get("event_name",""))}</span>'
                f'<span class="loc">{loc}{opn}</span></span></li>'
            )
        sections.append(f'<section class="mon"><h2>{esc(label)}</h2><ul>{"".join(rows)}</ul></section>')

    meta = data.get("meta") or {}
    updated = esc(meta.get("generated_at") or meta.get("report_week") or "")
    sub = f"最終更新 {updated}・{len(events)}公演" if updated else f"{len(events)}公演"

    js = (JS.replace("%FIRST%", json.dumps(first))
            .replace("%LAST%", json.dumps(last)))

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
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@{FC_VER}/index.global.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@fullcalendar/core@{FC_VER}/locales/ja.global.min.js"></script>
<style>{CSS}</style></head><body>
<header><a class="home" href="/">← 推しミテ！トップ</a><h1>ライブ日程カレンダー</h1>
<p>{esc(sub)}</p></header>
<div class="legend">{legend}</div>
<main>
<div id="cal"></div>
<p class="calnote">日付のバーをタップ（ホバー）で会場・開演を表示。前月／次月で移動できます。混雑日は「+N」でまとめて表示。</p>
<p class="listhead">▼ 一覧でも見る（会場・日時）</p>
{"".join(sections)}
<p class="note">※ 公演情報は各公式発表に基づく参考情報です。最新・正確な情報は各公演の公式サイトでご確認ください。<br>推しミテ！で応援うちわを作って、コンビニでA3実寸プリント。全機能無料。</p>
</main>
<footer>© 2026 ShiraseLab / 推しミテ！ ・ <a href="/">トップ</a> ・ <a href="/templates/">うちわテンプレート</a></footer>
<script>window.__LIVE_EVENTS__ = {events_json};</script>
<script>{js}</script>
</body></html>
"""

    (HERE / "index.html").write_text(page, encoding="utf-8")
    print(f"schedules/index.html generated: {len(events)} events, {len(fcev)} calendar bars, "
          f"{len(sections)} months, {len(ordered)} genres, range {first}..{last}")


if __name__ == "__main__":
    main()
