#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
07にくまるフォントを「LP の見出しで実際に使う字種」だけにサブセットして WOFF2 化する。

素の OTF は 2.93MB あり、そのまま Web フォントとして読ませるとモバイル回線で
表示が数秒遅れる。見出しは字種が限られるので、必要な字だけ切り出して 60KB 前後に落とす。

使い方:
    pip install fonttools brotli
    python tools/subset_nikumaru.py

入力 : NikumaruFont/07にくまるフォント.otf
出力 : assets/nikumaru-subset.woff2

見出しを書き換えたら必ず再実行すること。サブセットに無い字は
フォールバック（Zen Maru Gothic）で表示され、そこだけ書体が変わって見える。

ライセンス:
    M+ FONTS License
    Copyright (C) 2002-2014 M+ FONTS PROJECT
    Copyright (C) 2014 Fontna.com
    Copyright (C) 2014 Kato Masashi
    改変・再配布・商用利用いずれも許諾されている（無保証）。
    詳細は NikumaruFont/mplus-TESTFLIGHT-058/LICENSE_J を参照。
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "NikumaruFont" / "07にくまるフォント.otf"
OUT = ROOT / "assets" / "nikumaru-subset.woff2"

# --- 1. index.html の見出しで実際に使っている文字 -------------------------
# var(--display) を適用している要素のテキスト。日本語版（正本）のみが対象。
# 中国語・韓国語の見出しは Zen Maru Gothic にフォールバックさせる
# （にくまるフォントに簡体字とハングルは収録されていない）。
HEADINGS = """
推しミテ！
by 白瀬ラボ
ファンサうちわ文字作成アプリ
スタンプ・ステッカー・テンプレートで、うちわをデコる
Android版、配信開始！
動画で見る、推しミテ！
つくれるのは、自分だけの一枚
かんたん、4ステップ
サブスクのお金を、推しに！
「ちゃんと実寸で刷れる」にこだわりました
ご利用上の注意
アプリのバージョン確認方法
配信スタンプ
配信ステッカー
うちわテンプレート集
"""


def build_charset() -> str:
    chars = set(HEADINGS) - {"\n"}

    # --- 2. 保険 ---------------------------------------------------------
    # 見出しの文言を少し直すたびにサブセットが壊れると運用が回らないので、
    # かな・ASCII・約物は全域を入れておく。追加しても数KB しか増えない。
    for cp in range(0x3041, 0x309F + 1):      # ひらがな
        chars.add(chr(cp))
    for cp in range(0x30A0, 0x30FF + 1):      # カタカナ
        chars.add(chr(cp))
    for cp in range(0x0020, 0x007E + 1):      # ASCII
        chars.add(chr(cp))
    for cp in range(0xFF10, 0xFF19 + 1):      # 全角数字
        chars.add(chr(cp))
    chars |= set("　、。，．・：；？！ー〜～「」『』（）［］｛｝〈〉《》【】…‥"
                 "“”‘’＋－＝／＼％＆＃＊♡★☆←→↑↓")
    return "".join(sorted(chars))


def main() -> int:
    if not SRC.exists():
        print(f"[NG] 元フォントが見つからない: {SRC}", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    charset = build_charset()
    txt = ROOT / "tools" / "_nikumaru_charset.txt"
    txt.write_text(charset, encoding="utf-8")

    cmd = [
        sys.executable, "-m", "fontTools.subset", str(SRC),
        f"--text-file={txt}",
        f"--output-file={OUT}",
        "--flavor=woff2",
        "--layout-features=kern,palt,vert,vrt2,liga,ccmp",
        "--no-hinting",
        "--desubroutinize",
        "--name-IDs=*", "--name-legacy", "--name-languages=*",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode

    kb = OUT.stat().st_size / 1024
    print(f"[OK] {OUT.relative_to(ROOT)}  {len(charset)} 字 / {kb:.1f} KB")

    # --- 3. 取りこぼし検査 ------------------------------------------------
    # サブセットに入らなかった見出し文字があれば、そこだけ別書体で表示されて
    # 見た目が崩れる。黙って通さず必ず報告する。
    try:
        from fontTools.ttLib import TTFont
        cmap = TTFont(OUT).getBestCmap()
        missing = sorted({c for c in set(HEADINGS) - {"\n"} if ord(c) not in cmap})
        if missing:
            print(f"[警告] 元フォントに無い字: {''.join(missing)}", file=sys.stderr)
    except Exception as exc:  # 検査の失敗で生成物を捨てる必要はない
        print(f"[警告] 検査をスキップ: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
