# ComputAI installer for Windows (PowerShell).
#
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# Installs computai.py and a computai.cmd wrapper into %LOCALAPPDATA%\computai\bin and
# adds that folder to your user PATH. Run from a checkout to install that copy; otherwise
# the script is downloaded from $env:COMPUTAI_URL.
$ErrorActionPreference = "Stop"
$Bin = Join-Path $env:LOCALAPPDATA "computai\bin"
$Ref = if ($env:COMPUTAI_REF) { $env:COMPUTAI_REF } else { "v0.1.0-beta.2" }
$Url = if ($env:COMPUTAI_URL) { $env:COMPUTAI_URL } else { "https://raw.githubusercontent.com/Sean-Hawks/computai/$Ref/computai" }

$Py = $null
foreach ($cand in @(@("py", "-3"), @("python"), @("python3"))) {
    try {
        $exe = $cand[0]; $rest = @($cand | Select-Object -Skip 1)
        & $exe @rest -c "import sys; sys.exit(sys.version_info < (3, 8))" 2>$null
        if ($LASTEXITCODE -eq 0) { $Py = $cand; break }
    } catch { }
}
if (-not $Py) { Write-Error "computai needs Python 3.8 or newer (install it from python.org)"; exit 1 }

New-Item -ItemType Directory -Force -Path $Bin | Out-Null
$Target = Join-Path $Bin "computai.py"
$Local = Join-Path $PSScriptRoot "computai"
if (Test-Path $Local) { Copy-Item $Local $Target -Force }
else { Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Target }

$cmd = '@echo off' + "`r`n" + ($Py -join ' ') + ' "%~dp0computai.py" %*' + "`r`n"
Set-Content -Path (Join-Path $Bin "computai.cmd") -Value $cmd -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not ($userPath -split ";" | Where-Object { $_ -eq $Bin })) {
    [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(";") + ";" + $Bin), "User")
    Write-Host "added $Bin to your PATH (open a new terminal to use it)"
}
Write-Host "installed $Target"
& $Py[0] @($Py | Select-Object -Skip 1) $Target --version
