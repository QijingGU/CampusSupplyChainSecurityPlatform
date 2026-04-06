$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend'
$backendDbPath = Join-Path $backendDir 'supply_chain.db'
$backendEnvPath = Join-Path $backendDir '.env'
$processStatePath = Join-Path $repoRoot '.ids-dev-processes.json'

$providerDefaults = @{
    deepseek = @{
        base_url = 'https://api.deepseek.com'
        model = 'deepseek-chat'
    }
    kimi = @{
        base_url = 'https://api.moonshot.cn/v1'
        model = 'moonshot-v1-8k'
    }
}

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found in PATH: $Name"
    }
}

function Test-HttpOk {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Test-PortAvailable {
    param([int]$Port)

    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Get-AvailablePort {
    param([int[]]$Candidates)

    foreach ($port in $Candidates) {
        if (Test-PortAvailable -Port $port) {
            return $port
        }
    }

    return $null
}

function Start-PowerShellWindow {
    param(
        [string]$WorkingDirectory,
        [string]$Title,
        [string[]]$Commands
    )

    $joinedCommands = @(
        '$ErrorActionPreference = ''Stop'''
        '$OutputEncoding = [System.Text.Encoding]::UTF8'
        '[Console]::InputEncoding = [System.Text.Encoding]::UTF8'
        '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8'
        ('$Host.UI.RawUI.WindowTitle = ''{0}''' -f $Title.Replace("'", "''"))
        ('Set-Location ''{0}''' -f $WorkingDirectory.Replace("'", "''"))
        $Commands
    ) -join "`r`n"

    return Start-Process powershell -WorkingDirectory $WorkingDirectory -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy',
        'Bypass',
        '-Command',
        $joinedCommands
    ) -PassThru
}

function Get-LiveProcessEntriesFromState {
    $entries = New-Object System.Collections.Generic.List[object]

    if (-not (Test-Path $processStatePath)) {
        return $entries
    }

    try {
        $state = Get-Content -Path $processStatePath -Raw | ConvertFrom-Json
        foreach ($proc in @($state.processes)) {
            $pid = 0
            if (-not ([int]::TryParse([string]$proc.pid, [ref]$pid) -and $pid -gt 0)) {
                continue
            }

            if (-not (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
                continue
            }

            $entries.Add([pscustomobject]@{
                name = [string]$proc.name
                pid = $pid
                port = if ($null -ne $proc.port) { [int]$proc.port } else { 0 }
                working_directory = [string]$proc.working_directory
                kind = [string]$proc.kind
            })
        }
    } catch {
        Write-Host ("[launcher] Failed to read existing process state file {0}: {1}" -f $processStatePath, $_.Exception.Message) -ForegroundColor Yellow
    }

    return $entries
}

function Save-ProcessState {
    param(
        [System.Collections.IEnumerable]$Processes,
        [int]$BackendPort,
        [int]$FrontendPort,
        [bool]$BackendReused
    )

    $state = [pscustomobject]@{
        updated_at = (Get-Date).ToString('s')
        backend_port = $BackendPort
        frontend_port = $FrontendPort
        backend_reused = $BackendReused
        processes = @($Processes)
    }

    $state |
        ConvertTo-Json -Depth 6 |
        Set-Content -Path $processStatePath -Encoding UTF8
}

function Read-EnvFile {
    param([string]$Path)

    $values = @{}
    if (-not (Test-Path $Path)) {
        return $values
    }

    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $line.Contains('=')) {
            continue
        }
        $parts = $line -split '=', 2
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($key) {
            $values[$key] = $value
        }
    }
    return $values
}

function Update-EnvFile {
    param(
        [string]$Path,
        [hashtable]$Updates
    )

    $lines = @()
    if (Test-Path $Path) {
        $lines = Get-Content $Path
    }

    $seen = New-Object 'System.Collections.Generic.HashSet[string]'
    $newLines = New-Object System.Collections.Generic.List[string]

    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $line.Contains('=')) {
            $newLines.Add($line)
            continue
        }

        $parts = $line -split '=', 2
        $key = $parts[0].Trim()
        if ($Updates.ContainsKey($key)) {
            $newLines.Add(('{0}={1}' -f $key, $Updates[$key]))
            [void]$seen.Add($key)
        } else {
            $newLines.Add($line)
        }
    }

    foreach ($entry in $Updates.GetEnumerator()) {
        if (-not $seen.Contains([string]$entry.Key)) {
            $newLines.Add(('{0}={1}' -f $entry.Key, $entry.Value))
        }
    }

    Set-Content -Path $Path -Value $newLines -Encoding UTF8
}

function Read-SecretPlainText {
    param([string]$Prompt)

    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally {
        if ($ptr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        }
    }
}

function Get-LaunchAiSelection {
    param([string]$EnvPath)

    $envValues = Read-EnvFile -Path $EnvPath
    $currentProvider = ''
    if ($envValues.ContainsKey('LLM_PROVIDER')) {
        $currentProvider = [string]$envValues['LLM_PROVIDER']
    }
    $defaultProvider = if ($providerDefaults.ContainsKey($currentProvider)) { $currentProvider } else { 'deepseek' }

    Write-Host ''
    Write-Host 'AI launch selection' -ForegroundColor Cyan
    if ($envValues.ContainsKey('LLM_API_KEY') -and [string]::IsNullOrWhiteSpace([string]$envValues['LLM_API_KEY']) -eq $false) {
        $currentModel = if ($envValues.ContainsKey('LLM_MODEL')) { [string]$envValues['LLM_MODEL'] } else { '' }
        Write-Host ("- Existing backend/.env AI config detected: provider={0} model={1}" -f $defaultProvider, ($currentModel -or '<default>')) -ForegroundColor DarkCyan
    }

    $enableAi = (Read-Host 'Enable AI audit for this launch? [y/N]').Trim().ToLower()
    if ($enableAi -notin @('y', 'yes')) {
        return @{
            skip_prompt = '1'
            force_static = '1'
            summary = 'static audit mode'
            provider = ''
            model = ''
            base_url = ''
        }
    }

    $providerInput = (Read-Host ("Choose provider [{0}] (deepseek/kimi)" -f $defaultProvider)).Trim().ToLower()
    if (-not $providerInput) {
        $providerInput = $defaultProvider
    }
    if (-not $providerDefaults.ContainsKey($providerInput)) {
        Write-Host ("[launcher] Unknown provider '{0}', falling back to {1}." -f $providerInput, $defaultProvider) -ForegroundColor Yellow
        $providerInput = $defaultProvider
    }

    $apiKey = (Read-SecretPlainText -Prompt ("Enter {0} API Key" -f $providerInput)).Trim()
    if (-not $apiKey) {
        Write-Host '[launcher] Empty API key entered. This launch will use static audit mode.' -ForegroundColor Yellow
        return @{
            skip_prompt = '1'
            force_static = '1'
            summary = 'static audit mode'
            provider = ''
            model = ''
            base_url = ''
        }
    }

    $providerConfig = $providerDefaults[$providerInput]
    Update-EnvFile -Path $EnvPath -Updates @{
        LLM_PROVIDER = $providerInput
        LLM_API_KEY = $apiKey
        LLM_BASE_URL = [string]$providerConfig.base_url
        LLM_MODEL = [string]$providerConfig.model
    }

    return @{
        skip_prompt = '1'
        force_static = '0'
        summary = ('AI audit using {0}' -f $providerInput)
        provider = $providerInput
        model = [string]$providerConfig.model
        base_url = [string]$providerConfig.base_url
    }
}

Assert-Command -Name 'python'
Assert-Command -Name 'npm'

$backendPort = $null
$backendAlreadyRunning = $false
foreach ($candidate in 8166, 8167) {
    if (Test-HttpOk -Url "http://127.0.0.1:$candidate/api/health") {
        $backendPort = $candidate
        $backendAlreadyRunning = $true
        break
    }
}

if (-not $backendPort) {
    $backendPort = Get-AvailablePort -Candidates @(8166, 8167)
}

if (-not $backendPort) {
    throw 'No backend port is available in the candidate set: 8166, 8167.'
}

$frontendPort = Get-AvailablePort -Candidates @(5173, 5174)
if (-not $frontendPort) {
    throw 'No frontend port is available in the candidate set: 5173, 5174.'
}

$launchAiSelection = $null
$processEntries = Get-LiveProcessEntriesFromState

if (-not $backendAlreadyRunning) {
    $launchAiSelection = Get-LaunchAiSelection -EnvPath $backendEnvPath
}

if (-not $backendAlreadyRunning) {
    $backendCommands = @(
        ('$env:IDS_SKIP_LLM_STARTUP_PROMPT = ''{0}''' -f $launchAiSelection.skip_prompt),
        ('$env:IDS_FORCE_STATIC_MODE = ''{0}''' -f $launchAiSelection.force_static),
        ('if (-not (Test-Path ''{0}'')) {{' -f $backendDbPath.Replace("'", "''")),
        '    Write-Host "[backend] supply_chain.db not found. Running init_db.py..." -ForegroundColor Yellow',
        '    python init_db.py',
        '    if ($LASTEXITCODE -ne 0) { throw "init_db.py failed." }',
        '}',
        ('Write-Host "[backend] Starting FastAPI at http://127.0.0.1:{0}" -ForegroundColor Green' -f $backendPort),
        ('Write-Host "[backend] Launch mode: {0}" -ForegroundColor Cyan' -f $launchAiSelection.summary)
    )

    if ($launchAiSelection.force_static -eq '1') {
        $backendCommands += 'Write-Host "[backend] This launch is pinned to static audit mode, even if backend/.env already contains an API key." -ForegroundColor Cyan'
    } else {
        $backendCommands += ('Write-Host "[backend] Provider={0}, model={1}, base={2}" -ForegroundColor Cyan' -f $launchAiSelection.provider, $launchAiSelection.model, $launchAiSelection.base_url)
    }

    $backendCommands += ('python -m uvicorn app.main:app --reload --host 127.0.0.1 --port {0}' -f $backendPort)

    $backendWindow = Start-PowerShellWindow -WorkingDirectory $backendDir -Title 'IDS Backend' -Commands $backendCommands
    $processEntries.Add([pscustomobject]@{
        name = 'backend'
        pid = [int]$backendWindow.Id
        port = $backendPort
        working_directory = $backendDir
        kind = 'powershell_window'
    })
    Save-ProcessState -Processes $processEntries -BackendPort $backendPort -FrontendPort $frontendPort -BackendReused $backendAlreadyRunning
}

$frontendCommands = @(
    'if (-not (Test-Path ''node_modules'')) {',
    '    Write-Host "[frontend] node_modules not found. Running npm install..." -ForegroundColor Yellow',
    '    npm install',
    '    if ($LASTEXITCODE -ne 0) { throw "npm install failed." }',
    '}',
    ('Write-Host "[frontend] Starting Vite at http://127.0.0.1:{0}" -ForegroundColor Green' -f $frontendPort),
    ('npm run dev -- --host 127.0.0.1 --port {0}' -f $frontendPort)
)

$frontendWindow = Start-PowerShellWindow -WorkingDirectory $frontendDir -Title 'IDS Frontend' -Commands $frontendCommands
$processEntries.Add([pscustomobject]@{
    name = 'frontend'
    pid = [int]$frontendWindow.Id
    port = $frontendPort
    working_directory = $frontendDir
    kind = 'powershell_window'
})
Save-ProcessState -Processes $processEntries -BackendPort $backendPort -FrontendPort $frontendPort -BackendReused $backendAlreadyRunning

Write-Host ''
Write-Host 'IDS quick start launched.' -ForegroundColor Green
if ($backendAlreadyRunning) {
    Write-Host ("- Backend reused: http://127.0.0.1:{0}" -f $backendPort)
    Write-Host '- Existing backend process was already running, so no new AI-mode prompt was shown.'
} else {
    Write-Host ("- Backend window started: http://127.0.0.1:{0}" -f $backendPort)
    Write-Host ("- Backend launch mode: {0}" -f $launchAiSelection.summary)
}
Write-Host ("- Frontend window started: http://127.0.0.1:{0}" -f $frontendPort)
Write-Host ("- API docs: http://127.0.0.1:{0}/docs" -f $backendPort)
Write-Host ("- Stop command: powershell -ExecutionPolicy Bypass -File ""{0}""" -f (Join-Path $repoRoot 'stop-ids-dev.ps1'))
Write-Host ("- Process state file: {0}" -f $processStatePath)
Write-Host ''
Write-Host 'Demo accounts: system_admin / logistics_admin / warehouse_procurement / campus_supplier / counselor_teacher'
Write-Host 'Password: 123456'
