#!/usr/bin/env python3
"""配信テンプレの SEO ページ生成（index.json が唯一の入力＝ソース・オブ・トゥルース）。

生成物:
  templates/tpl.css                共通スタイル（個別/タグページが読む）
  templates/t/<id>.html            テンプレごとの個別ページ（検索面を増やす）
  templates/tag/<slug>.html        タグ（フィルター）ごとの一覧ページ
  templates/index.html             ギャラリー（CARDS を個別ページへのリンク付きで再生成＋TAGNAV）
  sitemap.xml                      root / help / templates / 全 t / 全 tag を列挙
  robots.txt                       Sitemap 行つき

使い方: リポジトリの templates/index.json を更新したら
  python templates/_gen_seo.py
を実行して commit/push（GitHub Pages 反映）。※アプリのアップロードは index.json と
index.html カードを書くが、個別/タグページと sitemap はこのスクリプトで再生成する。
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent          # .../templates
ROOT = HERE.parent                               # repo root
SITE = "https://oshimite.jp"
HELP = "help-2.4.0.html"

data = json.loads((HERE / "index.json").read_text(encoding="utf-8"))
templates = data["templates"]


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def slugify(tag: str) -> str:
    s = (tag or "").strip()
    for a, b in (("／", "-"), ("/", "-"), (" ", "-"), ("　", "-"),
                 ("!", ""), ("！", ""), ("?", ""), ("？", ""),
                 ("#", ""), ("%", ""), ("&", "and")):
        s = s.replace(a, b)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "tag"


# タグを初出順に集め、一意な slug を割り当てる
all_tags: list[str] = []
for t in templates:
    for tag in t.get("tags", []):
        if tag not in all_tags:
            all_tags.append(tag)

tag_slug: dict[str, str] = {}
seen: dict[str, str] = {}
for tag in all_tags:
    base = slugify(tag)
    slug, i = base, 2
    while slug in seen and seen[slug] != tag:
        slug, i = f"{base}-{i}", i + 1
    seen[slug] = tag
    tag_slug[tag] = slug


def tpls_for_tag(tag: str):
    return [t for t in templates if tag in t.get("tags", [])]


CSS = """:root{
  --pink:#FF5C8A;--pink-deep:#FF2E6E;--lav:#B9A3FF;
  --bg:#FFF0F6;--bg2:#FFE3EF;--ink:#4A2E3D;--ink-soft:#9A7886;--gold:#FFD84D;--white:#fff;
  --display:'Mochiy Pop One',system-ui,sans-serif;--body:'M PLUS Rounded 1c',system-ui,sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
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
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:22px;margin-top:20px}
.card{background:var(--white);border-radius:20px;overflow:hidden;
  box-shadow:0 8px 24px rgba(255,92,138,.14);border:2px solid #ffd9e6;display:flex;flex-direction:column;
  transition:transform .16s ease,box-shadow .16s ease}
a.card:hover{transform:translateY(-4px);box-shadow:0 14px 30px rgba(255,92,138,.22)}
.card .thumb{background:#111;aspect-ratio:1/1;display:flex;align-items:center;justify-content:center}
.card .thumb img{width:100%;height:100%;object-fit:contain}
.card .body{padding:14px 16px 18px}
.card h2{font-family:var(--display);font-size:1.05rem;color:var(--ink);line-height:1.4}
.detail{max-width:720px;margin:0 auto}
.detail .frame{max-width:420px;margin:0 auto;background:#111;border-radius:20px;overflow:hidden;
  border:2px solid #ffd9e6;box-shadow:0 10px 28px rgba(255,92,138,.18);aspect-ratio:1/1;
  display:flex;align-items:center;justify-content:center}
.detail .frame img{width:100%;height:100%;object-fit:contain}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:20px auto 0;max-width:640px}
.chip{display:inline-block;background:#fff;border:2px solid #FFC9DD;color:var(--pink-deep);
  font-weight:700;font-size:.82rem;padding:5px 13px;border-radius:999px}
.chip:hover{background:var(--bg2)}
.cta{display:inline-block;margin:22px auto 0;padding:12px 26px;border-radius:999px;
  background:var(--pink-deep);color:#fff;font-weight:700;box-shadow:0 6px 16px rgba(255,46,110,.35)}
.cta:hover{background:var(--pink)}
.center{text-align:center}
.tagnav{max-width:960px;margin:6px auto 0;padding:0 16px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.note{max-width:960px;margin:26px auto 0;padding:0 18px;font-size:.85rem;color:var(--ink-soft);text-align:center}
footer{text-align:center;padding:24px 16px 48px;color:var(--ink-soft);font-size:.82rem}
footer a{color:var(--pink-deep)}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+One&family=M+PLUS+Rounded+1c:wght@400;500;700;800&display=swap" rel="stylesheet">')

GTAG = ('<!-- Google tag (gtag.js) -->\n'
        '<script async src="https://www.googletagmanager.com/gtag/js?id=G-N5SNNFWXR4"></script>\n'
        '<script>\n  window.dataLayer = window.dataLayer || [];\n'
        '  function gtag(){dataLayer.push(arguments);}\n'
        "  gtag('js', new Date());\n  gtag('config', 'G-N5SNNFWXR4');\n</script>")


def page_head(title, desc, canonical, image, css_href):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
{GTAG}
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{image}">
<link rel="icon" href="/oshimite-icon.png">
{FONTS}
<link rel="stylesheet" href="{css_href}">
</head>
<body>"""


FOOT = ('<footer>\n  <p>© 白瀬ラボ / 推しミテ！ ・ '
        '<a href="/">トップ</a> ・ <a href="/templates/">テンプレート集</a> ・ '
        f'<a href="/{HELP}">使い方</a></p>\n</footer>\n</body>\n</html>\n')


def card_html(t, base_prefix):
    """base_prefix: t/ ページから見た相対の接頭。ここでは常にルート相対 URL を使う。"""
    tid = t["id"]
    title = t["title"]
    thumb = f"/templates/{t['thumbUrl']}"
    return (f'    <a class="card" href="/templates/t/{tid}.html">\n'
            f'      <div class="thumb"><img src="{thumb}" alt="「{esc(title)}」うちわテンプレート" width="640" height="640" loading="lazy"></div>\n'
            f'      <div class="body">\n        <h2>{esc(title)}</h2>\n      </div>\n'
            f'    </a>')


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---- tpl.css ----
write(HERE / "tpl.css", CSS)

# ---- 個別テンプレページ ----
for t in templates:
    tid = t["id"]
    title = t["title"]
    tags = t.get("tags", [])
    thumb = f"/templates/{t['thumbUrl']}"
    canonical = f"{SITE}/templates/t/{tid}.html"
    img = f"{SITE}/templates/{t['thumbUrl']}"
    desc = (f"「{title}」の応援うちわテンプレート。推しミテ！アプリで文字やメンバーカラーを"
            f"編集して、コンビニでA3実寸プリント。全機能無料。"
            + ("タグ: " + " / ".join(tags) if tags else ""))
    chips = "\n".join(
        f'      <a class="chip" href="/templates/tag/{tag_slug[tag]}.html">#{esc(tag)}</a>'
        for tag in tags)
    ld = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title,
        "headline": title,
        "image": img,
        "url": canonical,
        "isPartOf": {"@type": "CollectionPage", "name": "うちわテンプレート集",
                     "url": f"{SITE}/templates/"},
        "keywords": ", ".join(tags),
        "author": {"@type": "Organization", "name": "白瀬ラボ / ShiraseLab"},
        "inLanguage": "ja",
    }
    ld_json = json.dumps(ld, ensure_ascii=False)
    body = f"""{page_head(f"{title} - うちわテンプレート | 推しミテ！", desc, canonical, img, "/templates/tpl.css")}
<script type="application/ld+json">{ld_json}</script>
<header>
  <a class="home" href="/templates/">← うちわテンプレート集</a>
  <h1>{esc(title)}</h1>
</header>
<nav class="crumb"><a href="/">推しミテ！</a> › <a href="/templates/">テンプレート集</a> › {esc(title)}</nav>
<main class="detail">
  <div class="frame"><img src="{thumb}" alt="「{esc(title)}」うちわテンプレートのプレビュー" width="640" height="640"></div>
{f'  <div class="chips">{chr(10)}{chips}{chr(10)}  </div>' if chips else ''}
  <p class="center"><a class="cta" href="/">アプリで開いて編集する</a></p>
  <p class="note">※ このテンプレートは推しミテ！アプリ内の「テンプレート → もっと見る（配信テンプレ）」からダウンロードして編集する下書きです。文字・メンバーカラー・装飾を自由に変えて、コンビニでA3実寸プリントできます。</p>
</main>
{FOOT}"""
    write(HERE / "t" / f"{tid}.html", body)

# ---- タグ（フィルター）ページ ----
for tag in all_tags:
    slug = tag_slug[tag]
    matches = tpls_for_tag(tag)
    canonical = f"{SITE}/templates/tag/{slug}.html"
    img = f"{SITE}/templates/{matches[0]['thumbUrl']}" if matches else f"{SITE}/oshimite-icon.png"
    desc = (f"「{tag}」の応援うちわテンプレート一覧（{len(matches)}件）。推しミテ！アプリで"
            f"編集してコンビニでA3実寸プリント。全機能無料。")
    cards = "\n".join(card_html(t, "") for t in matches)
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"「{tag}」のうちわテンプレート",
        "url": canonical,
        "inLanguage": "ja",
    }
    body = f"""{page_head(f"「{tag}」のうちわテンプレート集 - 推しミテ！", desc, canonical, img, "/templates/tpl.css")}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<header>
  <a class="home" href="/templates/">← うちわテンプレート集</a>
  <h1>「{esc(tag)}」のうちわテンプレート</h1>
  <p>「{esc(tag)}」でつかえる応援うちわテンプレート {len(matches)} 件。アプリで編集してコンビニで実寸プリント。</p>
</header>
<nav class="crumb"><a href="/">推しミテ！</a> › <a href="/templates/">テンプレート集</a> › {esc(tag)}</nav>
<main>
  <section class="grid" aria-label="「{esc(tag)}」のテンプレート一覧">
{cards}
  </section>
  <p class="note">※ ダウンロードは <a href="/">推しミテ！</a> アプリの「テンプレート → もっと見る」から。</p>
</main>
{FOOT}"""
    write(HERE / "tag" / f"{slug}.html", body)

# ---- ギャラリー index.html を再生成（CARDS＝リンク付きカード / TAGNAV＝タグ導線）----
gallery = (HERE / "index.html").read_text(encoding="utf-8")

cards_block = "\n".join(card_html(t, "") for t in templates)
start = "<!-- CARDS:START"
end = "<!-- CARDS:END -->"
i0 = gallery.index(start)
i0 = gallery.index("-->", i0) + 3
i1 = gallery.index(end)
gallery = (gallery[:i0] + "\n" + cards_block + "\n    " + gallery[i1:])

# TAGNAV（grid の前に、独自マーカーで管理＝アプリの CARDS 再生成では消えない）
from collections import Counter as _Counter, defaultdict as _defaultdict
_GENERIC = {"かわいい", "キラキラ", "デコ", "定番"}   # 絞り込みにならない汎用タグは導線から外す
_filters = data.get("filters", [])
_cnt = {tag: len(tpls_for_tag(tag)) for tag in all_tags}
def _tchip(tg):
    return f'<a class="chip" href="/templates/tag/{tag_slug[tg]}.html">#{esc(tg)}（{_cnt[tg]}）</a>'
_group_axis = next((a for a in _filters if a.get("key") in ("kind", "group")), None)
_region_axis = next((a for a in _filters if a.get("key") == "region"), None)
_region_tags = set()
if _region_axis:
    for v in _region_axis.get("values", []):
        _region_tags.update(v.get("tags", []))
_kinds = [(v["name"], set(v.get("tags", []))) for v in _group_axis.get("values", [])] if _group_axis else []
def _item_kind(it):
    s = set(it.get("tags", []))
    for nm, mk in _kinds:
        if s & mk:
            return nm
    return None
_groups = _defaultdict(list)
for tg in all_tags:
    if tg in _GENERIC or tg in _region_tags:
        continue
    _ks = [_item_kind(x) for x in templates if tg in x.get("tags", [])]
    kc = _Counter(k for k in _ks if k is not None)
    _best, _bn = kc.most_common(1)[0] if kc else (None, 0)
    # そのタグの過半数がそのカテゴリの時だけ配属。横断的なテーマ語は「その他」へ。
    _groups[_best if _bn > len(_ks) / 2 else "その他"].append(tg)
_PER = 12
_sections = []
for nm, _mk in _kinds:
    ts = sorted((t for t in _groups.get(nm, []) if t != nm), key=lambda t: -_cnt[t])
    if ts:
        _sections.append((nm, ts[:_PER], True))
if _region_tags:
    rts = sorted((t for t in all_tags if t in _region_tags and t not in _GENERIC), key=lambda t: -_cnt[t])
    if rts:
        _sections.append((_region_axis.get("label", "地域"), rts[:_PER], True))
_other = sorted(_groups.get("その他", []), key=lambda t: -_cnt[t])
if _other:
    _sections.append(("その他", _other[:_PER], bool(_kinds or _region_tags)))
_parts = []
for _lbl, _ts, _show in _sections:
    _hd = f'<span class="tglabel">{esc(_lbl)}</span>' if _show else ""
    _parts.append(f'<div class="taggroup">{_hd}{"".join(_tchip(t) for t in _ts)}</div>')
tagnav = ('  <!-- TAGNAV:START （_gen_seo.py が index.json から再生成。手で編集しない） -->\n'
          f'  <section class="taggroups" aria-label="タグで絞り込む">{"".join(_parts)}</section>\n'
          '  <!-- TAGNAV:END -->\n')
if "<!-- TAGNAV:START" in gallery:
    a = gallery.index("  <!-- TAGNAV:START")
    b = gallery.index("<!-- TAGNAV:END -->")
    b = gallery.index("\n", b) + 1
    gallery = gallery[:a] + tagnav + gallery[b:]
else:
    anchor = '<main>\n'
    gallery = gallery.replace(anchor, anchor + tagnav, 1)
write(HERE / "index.html", gallery)

# ---- sitemap.xml ----
lastmod = data.get("updatedAt", "2026-08-05")
urls = [(f"{SITE}/", "1.0", "weekly"),
        (f"{SITE}/{HELP}", "0.8", "monthly"),
        (f"{SITE}/templates/", "0.8", "weekly")]
for t in templates:
    urls.append((f"{SITE}/templates/t/{t['id']}.html", "0.6", "monthly"))
for tag in all_tags:
    urls.append((f"{SITE}/templates/tag/{tag_slug[tag]}.html", "0.5", "weekly"))
# 配信スタンプ／ステッカーのギャラリーも sitemap に温存する（実体の生成は ../_gen_galleries.py。
# ここで URL を足さないと、このスクリプトを回すたびに sitemap から stamps/stickers が消える）。
for gdir, gkey in (("stamps", "stamps"), ("stickers", "stickers")):
    gp = ROOT / gdir / "index.json"
    if not gp.exists():
        continue
    gitems = json.loads(gp.read_text(encoding="utf-8"))[gkey]
    gtags, gseen, gslug = [], {}, {}
    for it in gitems:
        for tg in it.get("tags", []):
            if tg not in gtags:
                gtags.append(tg)
    for tg in gtags:
        base, s2, j = slugify(tg), slugify(tg), 2
        while s2 in gseen and gseen[s2] != tg:
            s2, j = f"{base}-{j}", j + 1
        gseen[s2] = tg; gslug[tg] = s2
    urls.append((f"{SITE}/{gdir}/", "0.8", "weekly"))
    for it in gitems:
        urls.append((f"{SITE}/{gdir}/t/{it['id']}.html", "0.6", "monthly"))
    for tg in gtags:
        urls.append((f"{SITE}/{gdir}/tag/{gslug[tg]}.html", "0.5", "weekly"))
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc, pri, cf in urls:
    sm.append(f"  <url>\n    <loc>{quote(loc, safe=':/')}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
              f"    <changefreq>{cf}</changefreq>\n    <priority>{pri}</priority>\n  </url>")
sm.append("</urlset>\n")
write(ROOT / "sitemap.xml", "\n".join(sm))

# ---- robots.txt ----
write(ROOT / "robots.txt",
      "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)

print(f"templates={len(templates)} tags={len(all_tags)} "
      f"pages: t={len(templates)} tag={len(all_tags)} + sitemap({len(urls)}) + robots + index.html + tpl.css")
