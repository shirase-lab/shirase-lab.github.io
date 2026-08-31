# schedules/

推しミテ！（うちわつくーる）SNSマーケティング用のライブ日程データ。
週2回（月・木）更新。**今週だけでなく、判明している先のツアー全日程まで累積**（`status` で時系列を区別）。

## ファイル

| ファイル | 内容 | 追跡 |
| --- | --- | --- |
| `live.internal.json` | **内部フル**（全項目＝uchiwa_demand/sns_priority/fan_service_culture/verified/notes/lineup_note 込み）。SNS施策用の本体・次回マージの base。AES暗号化版 | コミットする |
| `live.json` | **公開版**（アプリ／公開Web が取得）。`make_public.py` で内部項目を除去した公開情報のみ。AES暗号化版 | コミットする |
| `seed_list.json` | **定点巡回リスト**（監視対象アクト/事務所）の AES暗号化版 | コミットする |
| `crypt.sh` | 暗号化／復号ヘルパ（openssl AES-256-CBC / PBKDF2） | コミットする |
| `make_public.py` | 内部フル平文 → 公開平文（内部項目を除去）。`live.json` 生成に使う | コミットする |
| `_gen_schedules.py` | 公開 `live.json` → 公開Web `schedules/index.html`（ライブ日程ページ） | コミットする |
| `index.html` | 公開の「ライブ日程」ページ（`/schedules/`）。`_gen_schedules.py` が生成 | コミットする |
| `*.plain.json` 等の平文 | 元データ（平文） | **コミットしない**（`.gitignore` 済み） |

- `seed_list.json`（何を監視するか）→ 週2回（月・木）これを巡回して新規/更新公演を拾い、
  `live.json`（累積データ）へ **`id` で upsert**（被ったら更新・新規は追加・過去分は残す）する2段構成。
  マージと日付更新は決定的な `merge_live.py` が担う。両方とも暗号文で公開し、
  復号はパスフレーズを持つ手元だけで行う。

平文・パスフレーズはリポジトリに入れない。`live.json` は**暗号文のみ**を公開する。

## パスフレーズ

リポジトリ**外**のサイブリング `../oshimite.jp.passwd`
（= `D:/ShiraseLab/UchiwaTukool/oshimite.jp.passwd`）に平文で1行保存。
GitHub Pages（公開）には出ない。初回は自動生成した64桁の base64 乱数。差し替え可。

## 復号（手元で中身を見る）

```bash
# 標準出力へ
bash schedules/crypt.sh dec

# ファイルへ
bash schedules/crypt.sh dec schedules/live.json /tmp/live.plain.json
```

openssl 直叩きでも同じ:

```bash
openssl enc -d -aes-256-cbc -md sha256 -pbkdf2 -iter 200000 -salt -base64 \
  -in schedules/live.json \
  -pass file:../oshimite.jp.passwd
```

## 暗号化（平文 → live.json）

```bash
bash schedules/crypt.sh enc /path/to/live.plain.json
# => schedules/live.json を上書き
```

暗号／復号は**同じパラメータ**（`-aes-256-cbc -md sha256 -pbkdf2 -iter 200000 -salt -base64`）で行うこと。

## 更新フロー（週2回 月・木・Windows タスクスケジューラ → Claude headless）

1. `crypt.sh dec seed_list.json` / `crypt.sh dec live.json` で seed と前回データを復号。
2. `monitor_priority=high` から巡回し、新規ツアー/チケット発売/初日・千秋楽・卒業/大型フェスを検知。
   収集期間に上限なし（先のツアーも全日程を拾う）。**多都市ツアーはレグ後追い禁止＝発表済みの
   全都市・全レグを最初に全部登録する**（1レグ＝1レコード）。
3. 今回**追加/更新するイベントだけ**を `found.json` に完全な形で出す（再検査で `verified` true/false、
   当日休演・欠席は `absent`）。
4. `merge_live.py --base <前回> --incoming found.json --out <merged>` で **`id` upsert**＋
   `meta.generated_at`/`report_week` を更新（被りは丸ごと差し替え・新規は追加・過去分は残す）。
5. **`check_tour_gaps.py <merged>`（gate・必須）** でツアーのレグ取りこぼしを機械チェック。
   `⚠`（終了コード1）が出たら公式日程で欠けたレグを補って 3→4 をやり直す（`OK`＝0 になるまで）。
6. **2ファイル出力**: `crypt.sh enc <merged> schedules/live.internal.json`（内部フル）＋
   `make_public.py <merged>` で内部項目を除いた公開平文を作り `crypt.sh enc …public… schedules/live.json`（公開版）。
   さらに `_gen_schedules.py` で公開Web `schedules/index.html` を再生成 → commit → push（ランナーが実行）。

実体は `Run-LiveSchedule.ps1`（runner）＋ `daily_update.md`（ジョブ仕様）＋ `merge_live.py`（マージ）。
登録は `Register-LiveScheduleTask.ps1`。詳細は「## 自動化」参照。

> 発信前チェック: `absent`（当日休演・欠席）や在籍メンバー・活動状況は変動が速い。
> SNS 発信直前に各グループ公式（`seed_list.json` の `source`）で最終確認すること。

## 自動化（Windows タスクスケジューラ → Claude headless）

「取得＋検査」は Web 調査＝LLM が要るので、月・木に headless の Claude を起動して
調査→検査→**`id` upsert マージ**→暗号化まで行い、決定的な git 処理はランナー側で行う二段構え。

| ファイル | 役割 |
| --- | --- |
| `daily_update.md` | headless Claude に渡すジョブ仕様（seed/前回復号→調査→検査→`merge_live.py`→`check_tour_gaps.py`→`crypt.sh enc`）。 |
| `merge_live.py` | 決定的マージャ。`id` で upsert＋`meta` 日付（generated_at/report_week）更新。 |
| `check_tour_gaps.py` | **ツアー欠落リンタ（gate）**。多都市ツアーの「レグ取りこぼし」（最近まで開催中なのに this_week/upcoming レグが無い＝継続レグ未登録の疑い）を検出。暗号化前に必ず通す。**2026-08-21 強化**: 2レグ以上だけでなく、event_name が『ツアー/Tour』を含むのに live 上 1 レグしか無いツアーも検出（最初の1都市だけ登録して後続を後追いしなかった事故＝KEY TO LIT/ACEes を取りこぼしていた）。1レグのみは検知窓を広く（`--single-window-days` 既定90日）。各フラグは公式確認して埋める／千秋楽済みなら無視。 |
| `Run-LiveSchedule.ps1` | ランナー。`claude -p` 実行後、`schedules/` に差分があれば commit/push。 |
| `Register-LiveScheduleTask.ps1` | タスク `ShiraseLab-LiveSchedule` を毎週 月・木 09:00 で登録。 |
| `logs/` | 実行ログ（gitignore）。 |

### セットアップ

```powershell
# 1) まず動作確認（push しない）。pwsh が無ければ powershell でも可。
powershell -NoProfile -ExecutionPolicy Bypass -File schedules/Run-LiveSchedule.ps1 -DryRun

# 2) 問題なければ毎週 月・木 09:00 に登録（ログオン中のみ・管理者不要）
powershell -NoProfile -ExecutionPolicy Bypass -File schedules/Register-LiveScheduleTask.ps1
#    ログオフ中も走らせるなら管理者 PowerShell で:
#    powershell -NoProfile -ExecutionPolicy Bypass -File schedules/Register-LiveScheduleTask.ps1 -RunWhenLoggedOff

# 手動テスト実行 / 解除
Start-ScheduledTask       -TaskName 'ShiraseLab-LiveSchedule'
Unregister-ScheduledTask  -TaskName 'ShiraseLab-LiveSchedule' -Confirm:$false
```

### 前提

- `claude` CLI がログイン済み（headless で動く認証状態）。
- `git push` の資格情報が保存済み（Windows 資格情報マネージャ / `gh auth`）。HTTPS remote。
- ランナーは常に `--dangerously-skip-permissions` で headless 実行（Bash=crypt.sh・Web・Edit が要るため）。
  権限を絞るなら `Run-LiveSchedule.ps1` の `$claudeArgs` を `--allowedTools` 方式へ差し替え可。
- 曜日/時刻は `Register-LiveScheduleTask.ps1 -DaysOfWeek Monday,Thursday -Time '09:00'` で変更。
