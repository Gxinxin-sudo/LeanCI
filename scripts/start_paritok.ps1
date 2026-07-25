$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $ProjectRoot ".env"
$ParitokExecutable = Join-Path $ProjectRoot "backend\.venv\Scripts\paritok.exe"
$ConfigFile = Join-Path $ProjectRoot "paritok.yaml"

if ([string]::IsNullOrWhiteSpace($env:PARITOK_API_KEY) -and (Test-Path -LiteralPath $EnvFile)) {
    foreach ($Line in Get-Content -LiteralPath $EnvFile -Encoding utf8) {
        $Trimmed = $Line.Trim()
        if ($Trimmed.Length -eq 0 -or $Trimmed.StartsWith("#")) {
            continue
        }
        $Parts = $Trimmed.Split("=", 2)
        if ($Parts.Count -ne 2 -or $Parts[0].Trim() -ne "PARITOK_API_KEY") {
            continue
        }
        $Value = $Parts[1].Trim()
        if (
            $Value.Length -ge 2 -and
            (($Value.StartsWith('"') -and $Value.EndsWith('"')) -or
             ($Value.StartsWith("'") -and $Value.EndsWith("'")))
        ) {
            $Value = $Value.Substring(1, $Value.Length - 2)
        }
        $env:PARITOK_API_KEY = $Value
        break
    }
}

if ([string]::IsNullOrWhiteSpace($env:PARITOK_API_KEY)) {
    throw "PARITOK_API_KEY is missing. Add it only to the local .env file."
}
if (-not (Test-Path -LiteralPath $ParitokExecutable -PathType Leaf)) {
    throw "Paritok is not installed in backend/.venv. Install backend requirements first."
}
if (-not (Test-Path -LiteralPath $ConfigFile -PathType Leaf)) {
    throw "paritok.yaml is missing."
}

$GpuStatusUrl = "https://www.paritok.com/api/test"
try {
    $GpuStatus = Invoke-RestMethod `
        -Uri $GpuStatusUrl `
        -Headers @{ Authorization = "Bearer $env:PARITOK_API_KEY" } `
        -TimeoutSec 10
} catch {
    throw "Paritok hosted GPU preflight failed. The local Proxy was not started."
}
if ($GpuStatus.gpu_available -ne $true) {
    throw "Paritok hosted GPU is unavailable. The local Proxy was not started."
}

& $ParitokExecutable proxy `
    --host 127.0.0.1 `
    --port 8080 `
    --config-file $ConfigFile `
    --openai-url "https://api.deepseek.com/chat/completions" `
    --log-level info

exit $LASTEXITCODE
