# Keeps Windows from idle-sleeping (and the display on) while this process runs, the same way a
# video player does. No settings are changed; the request ends when the process exits.
# Stop it by creating film/tools/.stop_awake
param([string]$StopFile = "$PSScriptRoot\.stop_awake")
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
if (Test-Path $StopFile) { Remove-Item $StopFile }
# ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
[void][Win32.Power]::SetThreadExecutionState([uint32]"0x80000003")
"stay_awake active $(Get-Date -Format HH:mm)"
while (-not (Test-Path $StopFile)) {
    Start-Sleep -Seconds 30
    [void][Win32.Power]::SetThreadExecutionState([uint32]"0x80000003")
}
[void][Win32.Power]::SetThreadExecutionState([uint32]"0x80000000")
"stay_awake released $(Get-Date -Format HH:mm)"
