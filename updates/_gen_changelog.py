#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""updates/*.json（アプリの更新通知データ）から公開用の更新履歴ページ updates/index.html を生成する。

新バージョンの updates/<version>.json を追加/更新したら（§5.1）、
  python updates/_gen_changelog.py
を実行して commit/push する。ハイライトは日本語（各 JSON の highlights）をそのまま使う。
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = "https://oshimite.jp"


def esc(s):
    return html.escape(s or "", quote=True)


def vkey(d):
    try:
        return tuple(int(x) for x in str(d.get("version", "0")).split("."))
    except ValueError:
        return (0,)


versions = []
for p in sorted(HERE.glob("*.json")):
    if p.name == "current.json":
        continue
    try:
        versions.append(json.loads(p.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        pass
versions.sort(key=vkey, reverse=True)  # 新しい版を上に

cur = {}
cp = HERE / "current.json"
if cp.exists():
    cur = json.loads(cp.read_text(encoding="utf-8"))
latest = cur.get("latest", versions[0]["version"] if versions else "")

blocks = []
for d in versions:
    ver = esc(d.get("version", ""))
    date = esc(d.get("date", ""))
    lis = "".join(f"<li>{esc(h)}</li>" for h in d.get("highlights", []))
    badge = '<span class="latest">最新</span>' if d.get("version") == latest else ""
    blocks.append(
        f'<section class="rel"><h2>ver {ver}{badge}<span class="date">{date}</span></h2>'
        f'<ul>{lis}</ul></section>'
    )

html_out = f"""<!DOCTYPE html><html lang="ja"><head>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-N5SNNFWXR4"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-N5SNNFWXR4');</script>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>更新履歴 - 推しミテ！ 応援うちわ文字作成アプリ</title>
<meta name="description" content="応援うちわ作成アプリ「推しミテ！」の更新履歴（アップデート内容）。">
<link rel="canonical" href="{SITE}/updates/">
<meta property="og:title" content="更新履歴 - 推しミテ！"><meta property="og:description" content="推しミテ！のアップデート内容の履歴。">
<meta property="og:type" content="website"><meta property="og:url" content="{SITE}/updates/">
<meta property="og:image" content="{SITE}/oshimite-fan.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/oshimite-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+One&family=M+PLUS+Rounded+1c:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
:root{{--pink:#FF5C8A;--pink-deep:#FF2E6E;--bg:#FFF0F6;--bg2:#FFE3EF;--ink:#4A2E3D;--ink-soft:#9A7886;
--display:'Mochiy Pop One',system-ui,sans-serif;--body:'M PLUS Rounded 1c',system-ui,sans-serif;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--body);color:var(--ink);line-height:1.8;min-height:100vh;
background:radial-gradient(1200px 600px at 80% -10%,#FFD6E8 0%,transparent 55%),
radial-gradient(900px 500px at -10% 20%,#E6DBFF 0%,transparent 50%),var(--bg);-webkit-font-smoothing:antialiased}}
a{{color:var(--pink-deep);text-decoration:none}}a:hover{{text-decoration:underline}}
header{{text-align:center;padding:38px 20px 6px}}
header .home{{display:inline-block;color:var(--ink-soft);font-size:.9rem;margin-bottom:12px}}
h1{{font-family:var(--display);font-size:clamp(1.5rem,5vw,2.3rem);color:var(--pink-deep)}}
main{{max-width:720px;margin:0 auto;padding:20px 18px 64px}}
.rel{{background:#fff;border:2px solid #ffd9e6;border-radius:18px;padding:18px 20px;margin-top:18px;box-shadow:0 8px 24px rgba(255,92,138,.12)}}
.rel h2{{font-family:var(--display);font-size:1.15rem;color:var(--pink-deep);display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.rel .date{{font-family:var(--body);font-size:.82rem;color:var(--ink-soft);font-weight:500;margin-left:auto}}
.rel .latest{{background:var(--pink-deep);color:#fff;font-size:.7rem;font-weight:700;padding:3px 9px;border-radius:999px}}
.rel ul{{margin:12px 0 0;padding-left:1.2em}}
.rel li{{margin:6px 0;font-size:.92rem}}
footer{{text-align:center;padding:24px 16px 48px;color:var(--ink-soft);font-size:.82rem}}
</style></head><body>
<header><a class="home" href="/">← 推しミテ！トップ</a><h1>更新履歴</h1>
<p style="color:var(--ink-soft);margin-top:8px">応援うちわ作成アプリ「推しミテ！」のアップデート内容</p></header>
<main>
{"".join(blocks)}
</main>
<footer>© 2026 ShiraseLab / 推しミテ！ ・ <a href="/">トップ</a> ・ <a href="/help-2.6.0.html">使い方</a></footer>
</body></html>
"""

(HERE / "index.html").write_text(html_out, encoding="utf-8")
print(f"updates/index.html generated: {len(versions)} versions (latest {latest})")
