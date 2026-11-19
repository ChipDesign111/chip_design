param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Push-Location $Repo
try {
    if (-not (Test-Path -LiteralPath '.venv-demo\Scripts\python.exe')) {
        & $Python -m venv .venv-demo
        if ($LASTEXITCODE -ne 0) { throw 'Python venv creation failed' }
    }
    & .\.venv-demo\Scripts\python.exe -m pip install -r fpga/demo/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    & .\.venv-demo\Scripts\python.exe -m fpga.demo.assets
    if ($LASTEXITCODE -ne 0) { throw 'Pose model download failed' }
    & .\.venv-demo\Scripts\python.exe -m fpga.demo.doctor
    if ($LASTEXITCODE -ne 0) { throw 'Environment check failed' }
} finally { Pop-Location }
