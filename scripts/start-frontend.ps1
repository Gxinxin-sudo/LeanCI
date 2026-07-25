$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendPath = Join-Path $projectRoot "frontend"

Push-Location $frontendPath
try {
    npm run dev
}
finally {
    Pop-Location
}
