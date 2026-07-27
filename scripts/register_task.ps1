$pythonPath = (Get-Command python).Source
$scriptPath = Join-Path $PSScriptRoot "..\main.py" | Resolve-Path
$workingDir = Split-Path $scriptPath -Parent

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory $workingDir
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName "JobWatcher" -Action $action -Trigger $trigger -Settings $settings -Description "Daily job posting collection for job_watcher"
