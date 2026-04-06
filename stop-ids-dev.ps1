$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend'
$processStatePath = Join-Path $repoRoot '.ids-dev-processes.json'
$targetPorts = @(8166, 8167, 5173, 5174)

function Get-TrackedProcessIdsFromState {
    $ids = New-Object 'System.Collections.Generic.HashSet[int]'

    if (-not (Test-Path $processStatePath)) {
        return @($ids)
    }

    try {
        $state = Get-Content -Path $processStatePath -Raw | ConvertFrom-Json
        foreach ($proc in @($state.processes)) {
            $procId = 0
            if ([int]::TryParse([string]$proc.pid, [ref]$procId) -and $procId -gt 0) {
                [void]$ids.Add($procId)
            }
        }
    } catch {
        Write-Host ("Failed to read process state file {0}: {1}" -f $processStatePath, $_.Exception.Message) -ForegroundColor Yellow
    }

    return @($ids)
}

function Get-TrackedProcessIdsFallback {
    $ids = New-Object 'System.Collections.Generic.HashSet[int]'

    foreach ($port in $targetPorts) {
        Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
            Where-Object { $_.State -eq 'Listen' } |
            ForEach-Object { [void]$ids.Add([int]$_.OwningProcess) }
    }

    Get-CimInstance Win32_Process |
        Where-Object {
            $cmd = $_.CommandLine
            if (-not $cmd) { return $false }

            return (
                ($cmd -like "*$backendDir*" -and $cmd -match 'uvicorn|python') -or
                ($cmd -like "*$frontendDir*" -and $cmd -match 'vite|node|npm') -or
                ($cmd -like "*$backendDir*" -and $_.Name -eq 'powershell.exe') -or
                ($cmd -like "*$frontendDir*" -and $_.Name -eq 'powershell.exe')
            )
        } |
        ForEach-Object { [void]$ids.Add([int]$_.ProcessId) }

    return @($ids)
}

function Get-DescendantIds {
    param(
        [int[]]$RootIds
    )

    $all = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name
    $childrenByParent = @{}
    foreach ($proc in $all) {
        $parent = [int]$proc.ParentProcessId
        if (-not $childrenByParent.ContainsKey($parent)) {
            $childrenByParent[$parent] = New-Object System.Collections.Generic.List[int]
        }
        $childrenByParent[$parent].Add([int]$proc.ProcessId)
    }

    $seen = New-Object 'System.Collections.Generic.HashSet[int]'
    $queue = New-Object System.Collections.Generic.Queue[int]
    foreach ($id in $RootIds) {
        if ($id -gt 0 -and $seen.Add($id)) {
            $queue.Enqueue($id)
        }
    }

    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        if ($childrenByParent.ContainsKey($current)) {
            foreach ($child in $childrenByParent[$current]) {
                if ($seen.Add([int]$child)) {
                    $queue.Enqueue([int]$child)
                }
            }
        }
    }

    return @($seen)
}

$rootIds = Get-TrackedProcessIdsFromState
$usingFallback = $false

if ($rootIds -and $rootIds.Count -gt 0) {
    Write-Host ("Using recorded IDS process state: {0}" -f $processStatePath) -ForegroundColor Cyan
} else {
    $rootIds = Get-TrackedProcessIdsFallback
    $usingFallback = $true
}

if (-not $rootIds -or $rootIds.Count -eq 0) {
    Write-Host 'No IDS dev processes were detected on ports 8166/8167/5173/5174.' -ForegroundColor Yellow
    if (Test-Path $processStatePath) {
        Remove-Item -Path $processStatePath -Force
    }
    exit 0
}

$allIds = Get-DescendantIds -RootIds $rootIds
$processes = Get-CimInstance Win32_Process |
    Where-Object { $allIds -contains [int]$_.ProcessId } |
    Sort-Object ProcessId -Descending

if ((-not $processes -or $processes.Count -eq 0) -and -not $usingFallback) {
    Write-Host 'Recorded IDS process IDs are no longer alive; switching to fallback scan mode.' -ForegroundColor Yellow
    $rootIds = Get-TrackedProcessIdsFallback
    $usingFallback = $true

    if (-not $rootIds -or $rootIds.Count -eq 0) {
        if (Test-Path $processStatePath) {
            Remove-Item -Path $processStatePath -Force
        }
        Write-Host 'No IDS dev processes were detected on ports 8166/8167/5173/5174.' -ForegroundColor Yellow
        exit 0
    }

    $allIds = Get-DescendantIds -RootIds $rootIds
    $processes = Get-CimInstance Win32_Process |
        Where-Object { $allIds -contains [int]$_.ProcessId } |
        Sort-Object ProcessId -Descending
}

foreach ($proc in $processes) {
    try {
        Stop-Process -Id ([int]$proc.ProcessId) -Force -ErrorAction Stop
        Write-Host ("Stopped {0} ({1})" -f $proc.Name, $proc.ProcessId) -ForegroundColor Green
    } catch {
        Write-Host ("Failed to stop {0} ({1}): {2}" -f $proc.Name, $proc.ProcessId, $_.Exception.Message) -ForegroundColor Yellow
    }
}

if (Test-Path $processStatePath) {
    Remove-Item -Path $processStatePath -Force
}

if ($usingFallback) {
    Write-Host 'IDS dev processes stop attempt completed (fallback scan mode).' -ForegroundColor Cyan
} else {
    Write-Host 'IDS dev processes stop attempt completed.' -ForegroundColor Cyan
}
