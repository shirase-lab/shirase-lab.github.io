# schedules/

推しミテ！（うちわつくーる）SNSマーケティング用の週次ライブ日程データ。

## ファイル

| ファイル | 内容 | 追跡 |
| --- | --- | --- |
| `live.json` | **今週のライブ日程**（events）の AES暗号化版（openssl `Salted__` base64） | コミットする |
| `seed_list.json` | **定点巡回リスト**（監視対象アクト/事務所）の AES暗号化版 | コミットする |
| `crypt.sh` | 暗号化／復号ヘルパ（openssl AES-256-CBC / PBKDF2） | コミットする |
| `*.plain.json` 等の平文 | 元データ（平文） | **コミットしない**（`.gitignore` 済み） |

- `seed_list.json`（何を監視するか）→ 週2回（月・木）これを巡回して新規/更新公演を拾い、
  `live.json`（累積データ）へ **`id` で upsert**（被ったら更新・新規は追加・過去分は残す）する2段構成。
  マージと日付更新は決定的な `merge_live.py` が担う。両方とも暗号文で公開し、
  復号はパスフレーズを持つ手元だけで行う。

平文・パスフレーズはリポジトリに入れない。`live.json` は**暗号文のみ**を公開する。

## パスフレーズ

リポジトリ**外**のサイブリング `../shirase-lab.github.io.passwd`
（= `D:/ShiraseLab/UchiwaTukool/shirase-lab.github.io.passwd`）に平文で1行保存。
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
  -pass file:../shirase-lab.github.io.passwd
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
   収集期間に上限なし（先のツアーも全日程を拾う）。
3. 今回**追加/更新するイベントだけ**を `found.json` に完全な形で出す（再検査で `verified` true/false、
   当日休演・欠席は `absent`）。
4. `merge_live.py --base <前回> --incoming found.json --out <merged>` で **`id` upsert**＋
   `meta.generated_at`/`report_week` を更新（被りは丸ごと差し替え・新規は追加・過去分は残す）。
5. `crypt.sh enc <merged> schedules/live.json` で暗号化 → commit → push（ランナーが実行）。

実体は `Run-LiveSchedule.ps1`（runner）＋ `daily_update.md`（ジョブ仕様）＋ `merge_live.py`（マージ）。
登録は `Register-LiveScheduleTask.ps1`。詳細は「## 自動化」参照。

> 発信前チェック: `absent`（当日休演・欠席）や在籍メンバー・活動状況は変動が速い。
> SNS 発信直前に各グループ公式（`seed_list.json` の `source`）で最終確認すること。

## 自動化（Windows タスクスケジューラ → Claude headless）

「取得＋検査」は Web 調査＝LLM が要るので、月・木に headless の Claude を起動して
調査→検査→**`id` upsert マージ**→暗号化まで行い、決定的な git 処理はランナー側で行う二段構え。

| ファイル | 役割 |
| --- | --- |
| `daily_update.md` | headless Claude に渡すジョブ仕様（seed/前回復号→調査→検査→`merge_live.py`→`crypt.sh enc`）。 |
| `merge_live.py` | 決定的マージャ。`id` で upsert＋`meta` 日付（generated_at/report_week）更新。 |
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
