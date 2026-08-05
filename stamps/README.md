# 配信スタンプ（stamps/）

うちわつくーるアプリの**配信スタンプ**（作者制作・色変更できる SVG）の置き場。

- `index.json` … マニフェスト（`{ "schema":1, "stamps":[...] }`）。各エントリ:
  - `id`（一意・URL安全）/ `title` / `thumbUrl`（相対可・PNG）/ `fileUrl`（相対可・**SVG**）
  - `updatedAt` / `minAppVersion` / `tags`（分類・任意）/ `description`（任意）
- `<id>.svg` … スタンプ実体（**正規化済み SVG**＝クラス塗りインライン化・色 hex 化。アプリの
  `prepareImportedSvg` と同じ前処理。ラスタ PNG は不可＝色変更できないため）。
- `thumb/<id>.png` … 一覧サムネ（512px 目安）。

アプリはこれを GET のみで取得（送信なし・端末内キャッシュ）。**投稿機能は無い**（作者制作のみ）。
アップロード/削除はアプリのデバッグビルド（配信スタンプ・ギャラリー画面の「＋」/長押し）から。
