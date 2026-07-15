<#
.SYNOPSIS
  週2回（既定 月・木 09:00）に Run-LiveSchedule.ps1 を回す Windows タスクスケジューラ登録。

.DESCRIPTION
  タスク名 'ShiraseLab-LiveSchedule' を作成/更新する。既定は毎週 月・木 09:00、現在のユーザーで
  ログオン中に実行（-RunLevel Limited）。ログオフ中も走らせたい場合は -RunWhenLoggedOff を
  付ける（＝資格情報の保存が必要になり、管理者 PowerShell での実行が要る）。
  pwsh(7) が無ければ Windows PowerShell(powershell.exe) で実行する。

.PARAMETER Time
  起動時刻 'HH:mm'（既定 '09:00'）。

.PARAMETER DaysOfWeek
  実行する曜日（既定 Monday,Thursday）。

.PARAMETER RunWhenLoggedOff
  ログオフ中も実行（要・管理者権限＋パスワード保存）。

.EXAMPLE
  # 通常（ログオン中のみ・管理者不要）。pwsh が無ければ powershell でも可。
  powershell -ExecutionPolicy Bypass -File schedules/Register-LiveScheduleTask.ps1

.EXAMPLE
  # 曜日/時刻変更＋ログオフ中も（管理者 PowerShell で）
  powershell -ExecutionPolicy Bypass -File schedules/Register-LiveScheduleTask.ps1 -Time '09:00' -DaysOfWeek Monday,Thursday -RunWhenLoggedOff

.NOTES
  解除: Unregister-ScheduledTask -TaskName 'ShiraseLab-LiveSchedule' -Confirm:$false
#>
[CmdletBinding()]
param(
  [string]$Time = '09:00',
  [string[]]$DaysOfWeek = @('Monday','Thursday'),
  [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = 'Stop'
$taskName = 'ShiraseLab-LiveSchedule'

$here   = $PSScriptRoot
if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }
$runner = Join-Path $here 'Run-LiveSchedule.ps1'
if (-not (Test-Path $runner)) { throw "runner が見つかりません: $runner" }

# pwsh(7) があれば優先、無ければ Windows PowerShell（5.1 互換のため ?. は使わない）
$pwshCmd = Get-Command pwsh -ErrorAction SilentlyContinue
if ($pwshCmd) { $psExe = $pwshCmd.Source } else { $psExe = (Get-Command powershell).Source }

$action = New-ScheduledTaskAction -Execute $psExe `
  -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $runner)

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DaysOfWeek `
  -At ([datetime]::ParseExact($Time,'HH:mm',$null))

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
  -DontStopOnIdleEnd -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 1)

if ($RunWhenLoggedOff) {
  # ログオフ中も実行：資格情報を保存（S4U/Password）。管理者 PowerShell 必須。
  $principal = New-ScheduledTaskPrincipal -UserId ("{0}\{1}" -f $env:USERDOMAIN,$env:USERNAME) `
    -LogonType S4U -RunLevel Limited
} else {
  $principal = New-ScheduledTaskPrincipal -UserId ("{0}\{1}" -f $env:USERDOMAIN,$env:USERNAME) `
    -LogonType Interactive -RunLevel Limited
}

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal -Force | Out-Null

Write-Host ("登録完了: '{0}' 毎週 {1} {2}（{3}）" -f $taskName, ($DaysOfWeek -join ','), $Time,
  ($(if($RunWhenLoggedOff){'ログオフ中も'}else{'ログオン中のみ'})))
Write-Host "テスト実行: Start-ScheduledTask -TaskName '$taskName'"
Write-Host "解除:       Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
