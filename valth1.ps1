function CreateAndRunTask($taskName, $execute, $argument, $workingDir) {
    LogMessage "Creating scheduled task: $taskName"
    LogMessage "Execute: $execute"
    LogMessage "Argument: $argument"
    LogMessage "Working directory: $workingDir"
    LogMessage "User name: $env:USERNAME"

    try {
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(1)
        $action = New-ScheduledTaskAction -Execute $execute -Argument $argument -WorkingDirectory $workingDir
        
        if ($debug_mode -eq 1) {
            Write-Host "[DEBUG] Execute: $execute" -ForegroundColor Cyan
            Write-Host "[DEBUG] Argument: $argument" -ForegroundColor Cyan
            Write-Host "[DEBUG] Working directory: $workingDir" -ForegroundColor Cyan
        }

        Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -User "$env:COMPUTERNAME\$env:USERNAME" -RunLevel Highest -Force -ErrorAction Stop | Out-Null
        Start-ScheduledTask -TaskName $taskName
        LogMessage "Started scheduled task: $taskName"
        Start-Sleep -Seconds 2  # Give the task a moment to start
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    } catch {
        LogMessage "ERROR: Failed to create or run scheduled task: $taskName - $_"
        Write-Host "  ERROR: Could not create or run scheduled task: $taskName" -ForegroundColor Red
        Write-Host "  Error details: $_" -ForegroundColor Red
    }
}