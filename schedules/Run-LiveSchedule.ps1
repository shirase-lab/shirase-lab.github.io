<#
.SYNOPSIS
  推しミテ！ライブ日程 週次更新ランナー（Windows タスクスケジューラ → Claude headless）。

.DESCRIPTION
  1) daily_update.md をジョブ仕様として headless Claude (`claude -p`) に渡し、
     schedules/live.json（暗号文）を更新させる（調査→検査→暗号化まで）。
  2) schedules/ に差分が出たら、この PowerShell 側で git add/commit/push（決定的処理を分離）。

  週2回（月・木）の実行を想定。設計/規約は D:/ShiraseLab/ShiraseLab/DailyPipeline に倣う。

  headless の `claude -p` は権限プロンプトに答えられないため、常に
  --dangerously-skip-permissions で実行する（Bash=crypt.sh・Web調査・Edit が要るため）。
  自分のPC上の限定ジョブなので許容。権限を絞るなら claudeArgs を --allowedTools 方式へ。

.PARAMETER DryRun
  Claude によるデータ更新（live.json 再生成）までは行うが、git commit/push はしない。
  注: live.json は毎回の調査結果で上書きされる。試験で戻したいときは
      git checkout -- schedules/live.json。

.PARAMETER Model
  claude --model に渡すモデル（既定: 未指定＝アカウント既定）。

.EXAMPLE
  # 動作確認（push しない）。pwsh が無ければ powershell でも可。
  powershell -ExecutionPolicy Bypass -File schedules/Run-LiveSchedule.ps1 -DryRun
#>
[CmdletBinding()]
param(
  [datetime]$Now,
  [switch]$DryRun,
  [string]$Model
)

$ErrorActionPreference = 'Stop'

# --- UTF-8（DailyPipeline と同じ作法）---
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding  = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding           = $utf8NoBom

if (-not $Now) { $Now = Get-Date }

$here = $PSScriptRoot
if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }
$repo   = Split-Path -Parent $here                 # <repo>
$logDir = Join-Path $here 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$label  = $Now.ToString('yyyy-MM-dd')
$log    = Join-Path $logDir ("live-{0}.log" -f $label)

function Log($msg) {
  $line = ('[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $msg)
  $line | Tee-Object -FilePath $log -Append
}

# --- 前提チェック ---
$claude = (Get-Command claude -ErrorAction SilentlyContinue)
if (-not $claude) { Log 'ERROR: claude CLI が PATH にありません。中止。'; exit 2 }
$passwd = Join-Path (Split-Path -Parent $repo) 'shirase-lab.github.io.passwd'
if (-not (Test-Path $passwd) -or (Get-Item $passwd).Length -eq 0) {
  Log "ERROR: パスフレーズ未設定: $passwd"; exit 3
}

Log ("=== Run-LiveSchedule start (repo=$repo, DryRun=$DryRun) ===")

# --- Claude headless 実行 ---
$spec = Get-Content (Join-Path $here 'daily_update.md') -Raw -Encoding UTF8

# headless は権限プロンプトに答えられないので常にバイパス（Bash/Web/Edit が要る）。
$claudeArgs = @('-p', '--output-format', 'text', '--add-dir', $repo, '--dangerously-skip-permissions')
if ($Model) { $claudeArgs += @('--model', $Model) }

Push-Location $repo
try {
  Log ("claude {0}" -f ($claudeArgs -join ' '))
  # ジョブ仕様は stdin から渡す（引数長制限を回避）
  $spec | & $claude.Source @claudeArgs 2>&1 | Tee-Object -FilePath $log -Append
  $claudeExit = $LASTEXITCODE
  Log ("claude exit=$claudeExit")

  # --- 差分があれば git で確定（決定的処理はここ）---
  $changed = (git -C $repo status --porcelain -- schedules/) 2>$null
  if (-not $changed) {
    Log 'schedules/ に差分なし（更新なし）。'
  } elseif ($DryRun) {
    Log ("DryRun: 差分あり（未コミット）:`n$changed")
  } else {
    git -C $repo add schedules/ | Out-Null
    $msg = "chore(schedules): live.json 週次更新 ($label)"
    git -C $repo commit -m $msg | Tee-Object -FilePath $log -Append
    git -C $repo push origin HEAD | Tee-Object -FilePath $log -Append
    Log 'push 完了。'
  }
}
finally { Pop-Location }

Log '=== done ==='
exit 0
