#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配信スタンプ／ステッカーの公開ギャラリー＋SEOページを index.json から生成する。
templates/_gen_seo.py と同じ作法（個別ページ t/・タグページ tag/・ギャラリー index.html）。
sitemap.xml は root/help/templates(+t/tag)/stamps(+t/tag)/stickers(+t/tag) を全部列挙して
上書き（＝完全版。テンプレ側の背景処理は index.html しか触らないので消えない）。

使い方: stamps/index.json や stickers/index.json を更新したら
  python _gen_galleries.py
を実行して commit/push（GitHub Pages 反映）。
"""
import html, json, re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
SITE = "https://oshimite.jp"
HELP = "help-2.4.0.html"


def esc(s):
    return html.escape(s or "", quote=True)


def slugify(tag):
    s = (tag or "").strip()
    for a, b in (("／", "-"), ("/", "-"), (" ", "-"), ("　", "-"),
                 ("!", ""), ("！", ""), ("?", ""), ("？", ""),
                 ("#", ""), ("%", ""), ("&", "and"), ("①", "1"), ("②", "2"), ("③", "3")):
        s = s.replace(a, b)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "tag"


def tag_slugs(items):
    all_tags = []
    for it in items:
        for tg in it.get("tags", []):
            if tg not in all_tags:
                all_tags.append(tg)
    slug, seen = {}, {}
    for tg in all_tags:
        base, s, i = slugify(tg), slugify(tg), 2
        while s in seen and seen[s] != tg:
            s, i = f"{base}-{i}", i + 1
        seen[s] = tg
        slug[tg] = s
    return all_tags, slug


CSS = """:root{--pink:#FF5C8A;--pink-deep:#FF2E6E;--lav:#B9A3FF;--bg:#FFF0F6;--bg2:#FFE3EF;
  --ink:#4A2E3D;--ink-soft:#9A7886;--gold:#FFD84D;--white:#fff;
  --display:'Mochiy Pop One',system-ui,sans-serif;--body:'M PLUS Rounded 1c',system-ui,sans-serif;}
*{margin:0;padding:0;box-sizing:border-box}html{scroll-behavior:smooth}
body{font-family:var(--body);color:var(--ink);
  background:radial-gradient(1200px 600px at 80% -10%,#FFD6E8 0%,transparent 55%),
    radial-gradient(900px 500px at -10% 20%,#E6DBFF 0%,transparent 50%),var(--bg);
  line-height:1.75;-webkit-font-smoothing:antialiased;min-height:100vh}
a{color:inherit;text-decoration:none}
header{text-align:center;padding:34px 20px 6px}
header .home{display:inline-block;color:var(--ink-soft);font-size:.9rem;margin-bottom:12px}
header .home:hover{color:var(--pink-deep)}
h1{font-family:var(--display);font-size:clamp(1.4rem,4.6vw,2.2rem);color:var(--pink-deep);line-height:1.3}
header p{max-width:640px;margin:12px auto 0;color:var(--ink-soft)}
main{max-width:960px;margin:0 auto;padding:22px 16px 64px}
.crumb{max-width:960px;margin:12px auto 0;padding:0 16px;font-size:.82rem;color:var(--ink-soft)}
.crumb a:hover{color:var(--pink-deep);text-decoration:underline}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:18px;margin-top:20px}
.card{background:var(--white);border-radius:18px;overflow:hidden;
  box-shadow:0 8px 24px rgba(255,92,138,.14);border:2px solid #ffd9e6;display:flex;flex-direction:column;
  transition:transform .16s ease,box-shadow .16s ease}
a.card:hover{transform:translateY(-4px);box-shadow:0 14px 30px rgba(255,92,138,.22)}
.card .thumb{background:#f6eef2;aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;padding:10px}
/* max-width/height で内側にフィット（flex中央寄せ）。width/height:100% は Safari で
   aspect-ratio 親に対し overflow して .card の overflow:hidden で切れるため使わない。 */
.card .thumb img{max-width:100%;max-height:100%;width:auto;height:auto}
.card .body{padding:10px 12px 14px}
.card h2{font-family:var(--display);font-size:.92rem;color:var(--ink);line-height:1.4}
.detail{max-width:720px;margin:0 auto}
.detail .frame{max-width:380px;margin:0 auto;background:#f6eef2;border-radius:20px;overflow:hidden;
  border:2px solid #ffd9e6;box-shadow:0 10px 28px rgba(255,92,138,.18);aspect-ratio:1/1;
  display:flex;align-items:center;justify-content:center;padding:26px}
.detail .frame img{max-width:100%;max-height:100%;width:auto;height:auto}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:20px auto 0;max-width:640px}
.chip{display:inline-block;background:#fff;border:2px solid #FFC9DD;color:var(--pink-deep);
  font-weight:700;font-size:.82rem;padding:5px 13px;border-radius:999px}
.chip:hover{background:var(--bg2)}
.cta{display:inline-block;margin:22px auto 0;padding:12px 26px;border-radius:999px;
  background:var(--pink-deep);color:#fff;font-weight:700;box-shadow:0 6px 16px rgba(255,46,110,.35)}
.cta:hover{background:var(--pink)}.center{text-align:center}
.tagnav{max-width:960px;margin:6px auto 0;padding:0 16px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.tagnav-more{max-width:960px;margin:10px auto 0;text-align:center}
.tagnav-more>summary{display:inline-block;list-style:none;cursor:pointer;background:var(--bg2);border:2px solid #FFC9DD;color:var(--pink-deep);font-weight:700;font-size:.82rem;padding:6px 16px;border-radius:999px}
.tagnav-more>summary::-webkit-details-marker{display:none}
.tagnav-more[open]>summary{margin-bottom:12px}
.note{max-width:960px;margin:26px auto 0;padding:0 18px;font-size:.85rem;color:var(--ink-soft);text-align:center}
footer{text-align:center;padding:24px 16px 48px;color:var(--ink-soft);font-size:.82rem}
footer a{color:var(--pink-deep)}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+One&family=M+PLUS+Rounded+1c:wght@400;500;700;800&display=swap" rel="stylesheet">')

GTAG = ('<!-- Google tag (gtag.js) -->'
        '<script async src="https://www.googletagmanager.com/gtag/js?id=G-N5SNNFWXR4"></script>'
        '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}'
        "gtag('js',new Date());gtag('config','G-N5SNNFWXR4');</script>")


def head(title, desc, canonical, image):
    return f"""<!DOCTYPE html><html lang="ja"><head>{GTAG}
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}"><meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{image}"><link rel="icon" href="/oshimite-icon.png">
{FONTS}<link rel="stylesheet" href="/gallery.css"></head><body>"""


def foot():
    return ('<footer><p>© 白瀬ラボ / 推しミテ！ ・ <a href="/">トップ</a> ・ '
            '<a href="/stamps/">スタンプ</a> ・ <a href="/stickers/">ステッカー</a> ・ '
            '<a href="/templates/">テンプレート集</a> ・ '
            f'<a href="/{HELP}">使い方</a></p></footer></body></html>\n')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# gallery ごとの設定
GALLERIES = [
    dict(dir="stamps", key="stamps", noun="スタンプ", gtitle="配信スタンプ一覧",
         ghero="推しミテ！の配信スタンプ（色変更できるSVG）一覧。アプリで色を推しのメンバーカラーに変えて、うちわに貼れます。全機能無料。",
         idesc=lambda t: f"「{t}」の推し活うちわ用スタンプ（色変更できるSVG）。推しミテ！アプリで色を変えてうちわに貼れる。コンビニでA3実寸プリントも。全機能無料。"),
    dict(dir="stickers", key="stickers", noun="ステッカー", gtitle="配信ステッカー一覧",
         ghero="推しミテ！の配信ステッカー（透過PNG）一覧。応援うちわに貼ってデコれます。全機能無料。",
         idesc=lambda t: f"「{t}」の推し活うちわ用ステッカー（透過PNG）。推しミテ！アプリでうちわに貼ってデコれる。コンビニでA3実寸プリントも。全機能無料。"),
]


def card(dir_, it):
    tid, title = it["id"], it["title"]
    thumb = f"/{dir_}/{it['thumbUrl']}"
    return (f'<a class="card" href="/{dir_}/t/{tid}.html">'
            f'<div class="thumb"><img src="{thumb}" alt="「{esc(title)}」うちわ用{"" }" width="512" height="512" loading="lazy"></div>'
            f'<div class="body"><h2>{esc(title)}</h2></div></a>')


def gen_gallery(cfg):
    dir_, key, noun = cfg["dir"], cfg["key"], cfg["noun"]
    D = ROOT / dir_
    data = json.loads((D / "index.json").read_text(encoding="utf-8"))
    items = data[key]
    all_tags, slug = tag_slugs(items)

    # 個別ページ
    for it in items:
        tid, title = it["id"], it["title"]
        tags = it.get("tags", [])
        thumb = f"/{dir_}/{it['thumbUrl']}"
        canonical = f"{SITE}/{dir_}/t/{tid}.html"
        img = f"{SITE}/{dir_}/{it['thumbUrl']}"
        desc = cfg["idesc"](title)
        chips = "".join(f'<a class="chip" href="/{dir_}/tag/{slug[t]}.html">#{esc(t)}</a>' for t in tags)
        ld = {"@context": "https://schema.org", "@type": "ImageObject", "name": title,
              "contentUrl": img, "thumbnailUrl": img, "url": canonical,
              "keywords": ", ".join(tags), "isPartOf": {"@type": "CollectionPage",
              "name": cfg["gtitle"], "url": f"{SITE}/{dir_}/"},
              "author": {"@type": "Organization", "name": "白瀬ラボ / ShiraseLab"}, "inLanguage": "ja"}
        body = f"""{head(f"{title} - 推し活うちわ{noun} | 推しミテ！", desc, canonical, img)}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<header><a class="home" href="/{dir_}/">← 配信{noun}一覧</a><h1>{esc(title)}</h1></header>
<nav class="crumb"><a href="/">推しミテ！</a> › <a href="/{dir_}/">{noun}</a> › {esc(title)}</nav>
<main class="detail"><div class="frame"><img src="{thumb}" alt="「{esc(title)}」うちわ用{noun}のプレビュー" width="512" height="512"></div>
{f'<div class="chips">{chips}</div>' if chips else ''}
<p class="center"><a class="cta" href="/">アプリで使う</a></p>
<p class="note">※ この{noun}は推しミテ！アプリ内の「{noun}」ギャラリーから貼れます。{'色を推しのメンバーカラーに変えられます。' if dir_=='stamps' else ''}うちわはコンビニでA3実寸プリントできます。全機能無料。</p></main>
{foot()}"""
        write(D / "t" / f"{tid}.html", body)

    # タグページ
    for tg in all_tags:
        matches = [it for it in items if tg in it.get("tags", [])]
        canonical = f"{SITE}/{dir_}/tag/{slug[tg]}.html"
        img = f"{SITE}/{dir_}/{matches[0]['thumbUrl']}" if matches else f"{SITE}/oshimite-icon.png"
        desc = f"「{tg}」の推し活うちわ用{noun}一覧（{len(matches)}件）。推しミテ！アプリでうちわに貼れる。全機能無料。"
        cards = "".join(card(dir_, it) for it in matches)
        ld = {"@context": "https://schema.org", "@type": "CollectionPage",
              "name": f"「{tg}」の{noun}", "url": canonical, "inLanguage": "ja"}
        body = f"""{head(f"「{tg}」の推し活うちわ{noun} - 推しミテ！", desc, canonical, img)}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<header><a class="home" href="/{dir_}/">← 配信{noun}一覧</a><h1>「{esc(tg)}」の{noun}</h1>
<p>「{esc(tg)}」でつかえる推し活うちわ用{noun} {len(matches)} 件。</p></header>
<nav class="crumb"><a href="/">推しミテ！</a> › <a href="/{dir_}/">{noun}</a> › {esc(tg)}</nav>
<main><section class="grid" aria-label="「{esc(tg)}」の{noun}一覧">{cards}</section></main>
{foot()}"""
        write(D / "tag" / f"{slug[tg]}.html", body)

    # ギャラリー index.html
    canonical = f"{SITE}/{dir_}/"
    img = f"{SITE}/{dir_}/{items[0]['thumbUrl']}" if items else f"{SITE}/oshimite-icon.png"
    _tcount = {t: sum(1 for x in items if t in x.get("tags", [])) for t in all_tags}
    _tordered = sorted(all_tags, key=lambda t: (-_tcount[t], t))
    def _chip(t):
        return f'<a class="chip" href="/{dir_}/tag/{slug[t]}.html">#{esc(t)}（{_tcount[t]}）</a>'
    _TOPN = 20
    tagnav = "".join(_chip(t) for t in _tordered[:_TOPN])
    _rest = _tordered[_TOPN:]
    tagmore = (f'<details class="tagnav-more"><summary>＋ その他のタグ（{len(_rest)}）</summary>'
               f'<div class="tagnav">{"".join(_chip(t) for t in _rest)}</div></details>') if _rest else ""
    cards = "".join(card(dir_, it) for it in items)
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": cfg["gtitle"],
          "url": canonical, "inLanguage": "ja", "numberOfItems": len(items)}
    body = f"""{head(f"{cfg['gtitle']}（{len(items)}種）- 推しミテ！ 応援うちわ", cfg['ghero'], canonical, img)}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<header><a class="home" href="/">← 推しミテ！トップ</a><h1>{esc(cfg['gtitle'])}（{len(items)}種）</h1>
<p>{esc(cfg['ghero'])}</p></header>
<nav class="tagnav" aria-label="タグで絞り込む">{tagnav}</nav>{tagmore}
<nav class="crumb"><a href="/">推しミテ！</a> › {noun}</nav>
<main><section class="grid" aria-label="{esc(cfg['gtitle'])}">{cards}</section>
<p class="note">※ 推しミテ！は無料の応援うちわ作成アプリ。{noun}をうちわに貼って、コンビニでA3実寸プリントできます。</p></main>
{foot()}"""
    write(D / "index.html", body)
    return items, all_tags, slug


def main():
    write(ROOT / "gallery.css", CSS)
    per = {}
    for cfg in GALLERIES:
        per[cfg["dir"]] = gen_gallery(cfg)

    # ---- 完全版 sitemap（templates も読んで温存） ----
    urls = [(f"{SITE}/", "1.0", "weekly"), (f"{SITE}/{HELP}", "0.8", "monthly")]
    # templates
    try:
        td = json.loads((ROOT / "templates" / "index.json").read_text(encoding="utf-8"))
        tpls = td["templates"]
        t_tags, t_slug = tag_slugs(tpls)
        urls.append((f"{SITE}/templates/", "0.8", "weekly"))
        for t in tpls:
            urls.append((f"{SITE}/templates/t/{t['id']}.html", "0.6", "monthly"))
        for tg in t_tags:
            urls.append((f"{SITE}/templates/tag/{t_slug[tg]}.html", "0.5", "weekly"))
    except FileNotFoundError:
        pass
    # stamps / stickers
    for cfg in GALLERIES:
        items, all_tags, slug = per[cfg["dir"]]
        urls.append((f"{SITE}/{cfg['dir']}/", "0.8", "weekly"))
        for it in items:
            urls.append((f"{SITE}/{cfg['dir']}/t/{it['id']}.html", "0.6", "monthly"))
        for tg in all_tags:
            urls.append((f"{SITE}/{cfg['dir']}/tag/{slug[tg]}.html", "0.5", "weekly"))

    lastmod = "2026-08-07"
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, pri, cf in urls:
        sm.append(f"  <url>\n    <loc>{quote(loc, safe=':/')}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
                  f"    <changefreq>{cf}</changefreq>\n    <priority>{pri}</priority>\n  </url>")
    sm.append("</urlset>\n")
    write(ROOT / "sitemap.xml", "\n".join(sm))
    write(ROOT / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")

    print("galleries:", {d: (len(v[0]), len(v[1])) for d, v in per.items()},
          "sitemap urls:", len(urls))


if __name__ == "__main__":
    main()
