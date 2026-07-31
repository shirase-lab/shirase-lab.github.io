# templates/ — 配信テンプレ（作者制作テンプレのサーバ配信）

うちわつくーる（推しミテ！）が起動時ではなく**テンプレパネルを開いたとき**に読む配信テンプレの置き場。

- `index.json` … マニフェスト。アプリはここを GET してタップ用の一覧を作る。配信先 URL は
  Remote Config `template_manifest_url` で間接化（既定＝この `index.json` の URL 同値）。
- `*.uchiwa` … テンプレ実体（zip）。`fileUrl` から DL → 端末に `id@updatedAt` でキャッシュ。
- `thumb/*.webp` … 一覧サムネ。`thumbUrl` から `Image.network` で表示。
- `index.html` … 人間向けギャラリー（SEO・テンプレ名で検索面を増やす副産物）。
- `admin.html` … **タグ編集用の管理ページ**（`noindex`・公開ギャラリーからは非リンク）。GitHub の
  fine-grained PAT（`shirase-lab.github.io` の Contents: Read and write）をペースト→接続すると、
  各テンプレのタグをブラウザから編集して `index.json` に保存できる（GitHub Contents API を直接叩く・
  サーバ不要）。トークンは sessionStorage に一時保持（ログアウトで消去）。URL: `/templates/admin.html`。

## マニフェスト仕様（`index.json`）

各エントリ:

| キー | 必須 | 意味 |
|---|---|---|
| `id` | ○ | 一意 ID（端末キャッシュのファイル名にも使う） |
| `title` | ○ | 一覧の表題（**汎用ファンサ文言のみ**・グループ/メンバー名を入れない） |
| `thumbUrl` | ○ | サムネ URL（`index.json` からの相対可） |
| `fileUrl` | ○ | `.uchiwa` の URL（相対可） |
| `fallbackFont` | ○ | 端末に該当フォントが無いときの代替 family（**必須**・無いエントリは除外） |
| `updatedAt` | 任意 | 更新時刻（キャッシュ鮮度キー） |
| `minAppVersion` | 任意 | 対応最小アプリ版。実行版がこれ未満のエントリはアプリが**一覧から除外** |
| `description` | 任意 | 一覧の副題 |
| `tags` | 任意 | 分類タグの文字列配列（例 `["誕生日","初参戦"]`）。将来の絞り込み・SEO 用 |

## 方針（AGENTS.md / docs/TODO.md「テンプレ配信」）

- **投稿機能は作らない**（作者制作のみ）。`.uchiwa` に式評価・条件分岐など**ロジックになりうる
  ものを入れない**（宣言的データのプリセット配信＝ストア審査対象外）。
- **グループ名 / メンバー名を焼き込まない**（商標・パブリシティ権リスク）。汎用ファンサ文言
  （見て / 指さして / 指ハートして 等）に限定。※初回配信の 3 種は名前無しを選定済み。
  同梱テンプレのうち `豊`（推し名プレースホルダ）を含む 3 種は配信対象から除外している。
- **フォント実体は `.uchiwa` に埋め込まない**（再配布回避）。名前参照＋`fallbackFont`。
- **`schemaVersion` ゲート**: アプリは `.uchiwa` の `UchiwaDesign.schemaVersion` が
  対応上限を超えたら「最新版のアプリが必要です」と握りつぶす（クラッシュさせない）。
  互換を壊すフォーマット変更をしたらアプリ側 `kMaxKnownUchiwaSchemaVersion` を上げる。

## サムネの再生成手順

アプリ内一覧と同じレンダラで焼くので見た目が一致する。

本体リポジトリ直下（`D:/ShiraseLab/UchiwaTukool`）で実行:

```sh
# 1) 同梱テンプレから PNG を生成（test/rendering/out_template_dist_<id>.png へ）
flutter test test/rendering/template_dist_thumbs_dump_test.dart
# 2) webp へ変換して submodule の thumb/ へ置く（配信は webp のみ・PNG は submodule に入れない）
for n in mitekudasai uchiwa-tsukuto yubiheart; do \
  ffmpeg -y -i test/rendering/out_template_dist_$n.png \
    -c:v libwebp -q:v 82 -compression_level 6 \
    shirase-lab.github.io/templates/thumb/$n.webp; done
```

新しいテンプレを配る手順:
1. アプリで `.uchiwa` を作る（名前を焼かない）。`templates/<id>.uchiwa` に置く。
2. サムネを上記手順で生成（dump test の `targets` に id を足す）。
3. `index.json` に 1 エントリ足す（`fallbackFont` 必須・`minAppVersion` は配れる最小版）。
4. `index.html` にカードを足す（SEO）。submodule を commit/push → GitHub Pages 反映。
