<#
.SYNOPSIS
  推しミテ！ライブ日程 週次更新ランナー（Windows タスクスケジューラ → Claude headless）。

.DESCRIPTION
  1) daily_update.md をジョブ仕様として Claude Agent SDK（schedules/run_live_agent.py）に渡し、
     schedules/live.json（暗号文）を更新させる（調査→検査→暗号化まで）。
     API キー（このジョブ専用の環境変数 OSHIMITE_ANTHROPIC_API_KEY）で動かすので、Max に付く月次 API クレジットから引かれる。
     キーが未設定のときだけ、以前の `claude -p`（Max の利用枠）で動かす（警告をログに残す）。
  2) schedules/ に差分が出たら、この PowerShell 側で git add/commit/push（決定的処理を分離）。

  週2回（月・木）の実行を想定。設計/規約は D:/ShiraseLab/ShiraseLab/DailyPipeline に倣う。

  headless は権限プロンプトに答えられないため、常に権限をバイパスして実行する
  （Bash=crypt.sh・Web調査・Edit が要るため）。自分のPC上の限定ジョブなので許容。

.PARAMETER DryRun
  Claude によるデータ更新（live.json 再生成）までは行うが、git commit/push はしない。
  注: live.json は毎回の調査結果で上書きされる。試験で戻したいときは
      git checkout -- schedules/live.json。

.PARAMETER Model
  使うモデル（既定: 未指定＝既定のモデル）。

.PARAMETER MaxBudgetUsd
  1 回の実行の上限金額（USD・既定 5）。Agent SDK で動かすときだけ有効。

.EXAMPLE
  # 動作確認（push しない）。pwsh が無ければ powershell でも可。
  powershell -ExecutionPolicy Bypass -File schedules/Run-LiveSchedule.ps1 -DryRun
#>
[CmdletBinding()]
param(
  [datetime]$Now,
  [switch]$DryRun,
  [string]$Model,
  [double]$MaxBudgetUsd = 5
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
# Agent SDK はリポジトリ外の venv（D:/ShiraseLab/.venv-agent-sdk）に入れてある。
$sdkPython = 'D:\ShiraseLab\.venv-agent-sdk\Scripts\python.exe'
$useSdk = [bool]$env:OSHIMITE_ANTHROPIC_API_KEY -and (Test-Path $sdkPython)
$claude = (Get-Command claude -ErrorAction SilentlyContinue)
if (-not $useSdk -and -not $claude) { Log 'ERROR: Agent SDK も claude CLI も使えません。中止。'; exit 2 }
$passwd = Join-Path (Split-Path -Parent $repo) 'shirase-lab.github.io.passwd'
if (-not (Test-Path $passwd) -or (Get-Item $passwd).Length -eq 0) {
  Log "ERROR: パスフレーズ未設定: $passwd"; exit 3
}

Log ("=== Run-LiveSchedule start (repo=$repo, DryRun=$DryRun) ===")

# --- Claude headless 実行 ---
Push-Location $repo
try {
  if ($useSdk) {
    # Agent SDK（API キー＝月次 API クレジット）。ジョブ仕様は run_live_agent.py が daily_update.md から読む。
    $sdkArgs = @((Join-Path $here 'run_live_agent.py'), '--max-budget-usd', "$MaxBudgetUsd")
    if ($Model) { $sdkArgs += @('--model', $Model) }
    Log ("agent-sdk {0}" -f ($sdkArgs -join ' '))
    # Python の stderr を PowerShell がエラー扱いして止めないよう、この呼び出しだけ Continue にする。
    $prevEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & $sdkPython @sdkArgs 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
    $claudeExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    Log ("agent-sdk exit=$claudeExit")
  } else {
    Log 'WARN: OSHIMITE_ANTHROPIC_API_KEY が未設定（または SDK 未導入）のため claude -p（Max の利用枠）で実行します。'
    $spec = Get-Content (Join-Path $here 'daily_update.md') -Raw -Encoding UTF8
    $claudeArgs = @('-p', '--output-format', 'text', '--add-dir', $repo, '--dangerously-skip-permissions')
    if ($Model) { $claudeArgs += @('--model', $Model) }
    Log ("claude {0}" -f ($claudeArgs -join ' '))
    # ジョブ仕様は stdin から渡す（引数長制限を回避）
    $spec | & $claude.Source @claudeArgs 2>&1 | Tee-Object -FilePath $log -Append
    $claudeExit = $LASTEXITCODE
    Log ("claude exit=$claudeExit")
  }

  # --- ツアー欠落チェック（決定的バックストップ）---
  # headless Claude が daily_update.md §6.5 の gate を飛ばしても、ここで live.json を
  # 復号して check_tour_gaps.py にかけ、「レグ取りこぼし」を機械検出してログに残す。
  # （2026-08-03 実例: なにわ男子 ND⁵ の当週横浜レグ未登録＝当週なにわ0件。二度と見逃さない。）
  # 誤検知（本当に千秋楽済みのツアー）で週次 push 全体を止めたくないので、push は続行し警告のみ。
  try {
    if (Test-Path (Join-Path $repo 'schedules/live.json')) {
      $tmpPlain = Join-Path ([System.IO.Path]::GetTempPath()) ("live.audit.{0}.json" -f ([guid]::NewGuid().ToString('N')))
      & bash 'schedules/crypt.sh' dec 'schedules/live.json' $tmpPlain 2>&1 | Tee-Object -FilePath $log -Append
      if (Test-Path $tmpPlain) {
        $gate = (& python 'schedules/check_tour_gaps.py' $tmpPlain 2>&1)
        $gateExit = $LASTEXITCODE
        $gate | Tee-Object -FilePath $log -Append
        if ($gateExit -ne 0) {
          Log '⚠⚠ TOUR-GAP GATE: 継続レグ未登録の疑いあり。上の一覧の公式日程を確認しレグを補完のこと（push は続行）。'
        } else {
          Log 'tour-gap gate: OK（レグ取りこぼしの疑いなし）。'
        }
        Remove-Item -Force $tmpPlain -ErrorAction SilentlyContinue
      } else {
        Log 'tour-gap gate: 復号できず（スキップ）。'
      }
    }
  } catch { Log ("tour-gap gate 実行エラー（無視して継続）: {0}" -f $_.Exception.Message) }

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
