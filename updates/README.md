# updates/ — 推しミテ！ アップデート通知データ

推しミテ！アプリは起動時にここの JSON を読み、**アップデート通知ダイアログ**を出す。
実装は本体リポジトリ `lib/application/app_update_controller.dart`、運用手順は
`docs/RELEASE_CHECKLIST.md` §3-2 / `AGENTS.md` §5.1。

## ファイル

### `current.json` — 最新版とストア URL
```json
{
  "latest": "2.3.0",
  "androidUrl": "https://play.google.com/store/apps/details?id=com.shiraselab.uchiwa_tukool",
  "iosUrl": "https://apps.apple.com/app/idNNNNNNNNN"
}
```
- `latest`: **実際に配信済みの最新版**。実行版がこれ未満のとき「アップデートがあります」を出す。未配信の番号を先に入れない。
- `androidUrl` / `iosUrl`: 「アップデート」ボタンで開くストア URL（プラットフォーム別）。`iosUrl` は App Store 数値 ID が必要。未取得なら空文字 `""` で可（その場合 iOS はボタンを出さず OK のみ）。

### `<version>.json` — その版の更新内容（例 `2.3.0.json`）
```json
{
  "version": "2.3.0",
  "date": "2026-07-18",
  "title": "アップデート内容",
  "highlights": [
    "新機能を追加しました",
    "各種不具合修正"
  ]
}
```
- `title`: 空なら アプリ側の既定見出し（「アップデートがあります」/「アップデート内容」）を使う。
- `highlights`: 箇条書き。**不具合修正系は「各種不具合修正」の 1 項目にまとめる**（細かな fix を列挙しない）。

## 2 種のダイアログ（アプリ側）
- **アップデートがあります**（実行版 < `latest`）: `<latest>.json` を表示・ボタン＝アップデート/OK。
- **アップデート内容**（アプリ更新後）: 上がった実行版 `<installed>.json` を表示・ボタン＝OK のみ。
- どちらも同一バージョンでは 1 度だけ。取得失敗は無言スキップ（起動を止めない）。

## リリース時の更新手順
1. `<version>.json` を作成（`main` と前回版の差分を要約・不具合は「各種不具合修正」に集約）。
2. `current.json` の `latest` を新版へ。
3. commit/push（GitHub Pages 再デプロイ）→ 本体の submodule pointer 更新。
