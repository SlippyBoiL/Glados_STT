# Start a local Honcho stack for GLaDOS (API :8000, Postgres, Redis, deriver).
# Requires Docker Desktop. Writes honcho/.env from local Hermes llama.cpp (never printed).
# Windows PowerShell 5.1: do not put [*] or [!] inside double-quoted strings.

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$HonchoDir = Join-Path $RepoRoot "honcho"
$GladosEnv = Join-Path $RepoRoot ".env"
$HonchoEnv = Join-Path $HonchoDir ".env"

function Read-DotEnvKey([string]$path, [string]$name) {
    if (-not (Test-Path $path)) { return "" }
    foreach ($line in Get-Content $path) {
        $trim = $line.Trim()
        if (-not $trim -or $trim.StartsWith("#") -or $trim -notmatch "=") { continue }
        $k, $v = $trim.Split("=", 2)
        if ($k.Trim() -eq $name) { return $v.Trim().Trim('"').Trim("'") }
    }
    return ""
}

function Get-DockerBinDir {
    $cmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return Split-Path -Parent $cmd.Source
    }
    $candidates = @(
        "${env:ProgramFiles}\Docker\Docker\resources\bin",
        "${env:ProgramFiles}\Docker\Docker\resources\bin\docker.exe",
        "${env:LOCALAPPDATA}\Programs\Docker\Docker\resources\bin"
    )
    foreach ($c in $candidates) {
        $dir = $c
        if ($c -like '*.exe') { $dir = Split-Path -Parent $c }
        $exe = Join-Path $dir "docker.exe"
        if (Test-Path $exe) { return $dir }
    }
    return $null
}

function Get-DockerDesktopExe {
    foreach ($p in @(
        "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles}\Docker\Docker\resources\Docker desktop.exe"
    )) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

function Wait-DockerEngine {
    param([string]$DockerExe, [int]$Seconds = 180)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            & $DockerExe info --format '{{.ServerVersion}}' 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return $true }
        } catch { }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Read-HermesServerJson {
    $state = Join-Path $env:LOCALAPPDATA "hermes\runtimes\llamacpp\server.json"
    if (-not (Test-Path $state)) { return $null }
    try {
        return Get-Content $state -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

$hermes = Read-HermesServerJson
$key = Read-DotEnvKey $GladosEnv "HERMES_API_KEY"
if (-not $key -and $hermes) { $key = [string]$hermes.api_key }
$model = Read-DotEnvKey $GladosEnv "HERMES_MODEL"
if (-not $model) { $model = "Qwen3.6-35B-A3B-UD-Q4_K_M" }
$base = Read-DotEnvKey $GladosEnv "HERMES_BASE_URL"
if (-not $base -and $hermes -and $hermes.base_url) { $base = [string]$hermes.base_url }
if (-not $base) { $base = "http://127.0.0.1:18434/v1" }

if (-not $key) {
    Write-Host '[!] No Hermes API key. Leave Hermes Agent running, then re-run this script.'
    Write-Host '    GLaDOS reads %LOCALAPPDATA%\hermes\runtimes\llamacpp\server.json'
    Write-Host '    Honcho deriver can wait; GLaDOS still boots without it.'
    exit 1
}

$envBody = @"
AUTH_USE_AUTH=false
LOG_LEVEL=INFO
VECTOR_STORE_TYPE=pgvector
EMBED_MESSAGES=false
LLM_OPENAI_API_KEY=$key
DERIVER_MODEL_CONFIG__TRANSPORT=openai
DERIVER_MODEL_CONFIG__MODEL=$model
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=$base
DERIVER_FLUSH_ENABLED=true
DIALECTIC_LEVELS__low__MODEL_CONFIG__TRANSPORT=openai
DIALECTIC_LEVELS__low__MODEL_CONFIG__MODEL=$model
DIALECTIC_LEVELS__low__MODEL_CONFIG__OVERRIDES__BASE_URL=$base
SUMMARY_MODEL_CONFIG__TRANSPORT=openai
SUMMARY_MODEL_CONFIG__MODEL=$model
SUMMARY_MODEL_CONFIG__OVERRIDES__BASE_URL=$base
"@
Set-Content -Path $HonchoEnv -Value $envBody -Encoding utf8
Write-Host ('[*] Wrote {0} (Hermes key present, not printed)' -f $HonchoEnv)

$dockerBin = Get-DockerBinDir
if (-not $dockerBin) {
    Write-Host '[!] Docker Desktop files were not found. Install, then start Docker Desktop once:'
    Write-Host '    winget install -e --id Docker.DockerDesktop'
    Write-Host '    GLaDOS can still launch without Honcho; memory just will not persist.'
    exit 1
}

$env:Path = "$dockerBin;$env:Path"
$dockerExe = Join-Path $dockerBin "docker.exe"
Write-Host ('[*] Using {0}' -f $dockerExe)

$desktopExe = Get-DockerDesktopExe
$engineUp = $false
try {
    & $dockerExe info --format '{{.ServerVersion}}' 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $engineUp = $true }
} catch { }

if (-not $engineUp) {
    if ($desktopExe) {
        Write-Host '[*] Starting Docker Desktop (first launch may ask for WSL2 / a reboot)...'
        if (Get-Service com.docker.service -ErrorAction SilentlyContinue) {
            try { Start-Service com.docker.service -ErrorAction SilentlyContinue } catch { }
        }
        Start-Process -FilePath $desktopExe | Out-Null
    } else {
        Write-Host '[!] Found docker.exe but Docker Desktop is not running. Open Docker Desktop from the Start menu.'
        exit 1
    }
    Write-Host '[*] Waiting for the Docker engine...'
    if (-not (Wait-DockerEngine -DockerExe $dockerExe -Seconds 180)) {
        Write-Host '[!] Docker engine did not become ready. Finish first-run setup in the Docker Desktop window, wait until it says Running, then re-run this script.'
        Write-Host '    GLaDOS can still launch without Honcho; memory just will not persist.'
        exit 1
    }
}

Write-Host '[*] Starting Honcho stack (ghcr.io/plastic-labs/honcho:latest)...'
& $dockerExe compose -f (Join-Path $HonchoDir "docker-compose.yml") --project-directory $HonchoDir up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host '[!] docker compose up failed.'
    exit 1
}

Write-Host '[*] Waiting for http://127.0.0.1:8000/health ...'
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if ($ok) {
    Write-Host '[*] Honcho is up. GLaDOS will use HONCHO_URL=http://127.0.0.1:8000'
} else {
    Write-Host '[!] Honcho did not become healthy in time. Check: docker compose -f honcho/docker-compose.yml logs'
    exit 1
}
