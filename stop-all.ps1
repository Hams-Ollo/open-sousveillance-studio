# PowerShell Stop Script for Open Sousveillance Studio
# Reads PIDs from .pids/ directory and gracefully stops all services.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pidsDir = Join-Path $projectRoot ".pids"

if (-not (Test-Path $pidsDir)) {
    Write-Host "No .pids directory found. Nothing to stop." -ForegroundColor Yellow
    exit 0
}

$pidFiles = Get-ChildItem -Path $pidsDir -Filter "*.pid" -ErrorAction SilentlyContinue

if ($pidFiles.Count -eq 0) {
    Write-Host "No PID files found. Nothing to stop." -ForegroundColor Yellow
    exit 0
}

$stopped = 0
$notFound = 0

foreach ($pidFile in $pidFiles) {
    $serviceName = $pidFile.BaseName
    $savedPid = (Get-Content $pidFile.FullName).Trim()

    if (-not $savedPid) {
        Write-Host "  [$serviceName] Empty PID file, removing." -ForegroundColor Gray
        Remove-Item $pidFile.FullName -Force
        continue
    }

    try {
        $proc = Get-Process -Id $savedPid -ErrorAction Stop

        # Stop the process tree (terminal + child processes)
        Write-Host "  [$serviceName] Stopping PID $savedPid ($($proc.ProcessName))..." -ForegroundColor Cyan
        Stop-Process -Id $savedPid -Force -ErrorAction Stop

        # Also try to stop child processes
        try {
            Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $savedPid } | ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
        } catch {
            # Child process cleanup is best-effort
        }

        $stopped++
        Write-Host "  [$serviceName] Stopped." -ForegroundColor Green
    } catch [Microsoft.PowerShell.Commands.ProcessCommandException] {
        Write-Host "  [$serviceName] Process $savedPid not found (already stopped)." -ForegroundColor Gray
        $notFound++
    } catch {
        Write-Host "  [$serviceName] Error stopping PID $savedPid : $_" -ForegroundColor Red
    }

    # Clean up PID file
    Remove-Item $pidFile.FullName -Force
}

Write-Host ""
Write-Host "Summary: $stopped stopped, $notFound already gone." -ForegroundColor Green
