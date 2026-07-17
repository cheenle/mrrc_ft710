$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$DistRoot = Join-Path $RepoRoot "dist\windows"
$AppRoot = Join-Path $DistRoot "MRRC-FT710"
$PyInstallerRoot = Join-Path $DistRoot "_pyinstaller"

Set-Location $RepoRoot

Get-ChildItem -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
python -m unittest discover -s tests -v

$ft4222 = Join-Path $RepoRoot "vendor\ftdi\windows\bin\x64\FT4222.dll"
$d2xx = Join-Path $RepoRoot "vendor\ftdi\windows\bin\x64\ftd2xx.dll"
if (!(Test-Path $ft4222) -or !(Test-Path $d2xx)) {
    Write-Warning "FTDI DLLs are missing. The installer will build, but FT4222 true spectrum will fall back unless these files are added:"
    Write-Warning "  $ft4222"
    Write-Warning "  $d2xx"
}

pyinstaller packaging\pyinstaller\scope_pipe.spec --noconfirm --distpath "$PyInstallerRoot" --workpath "build\pyinstaller"
pyinstaller packaging\pyinstaller\ft710_server.spec --noconfirm --distpath "$PyInstallerRoot" --workpath "build\pyinstaller"
pyinstaller packaging\pyinstaller\ft710_launcher.spec --noconfirm --distpath "$PyInstallerRoot" --workpath "build\pyinstaller"

if (Test-Path $AppRoot) {
    Remove-Item $AppRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $AppRoot | Out-Null

Copy-Item (Join-Path $PyInstallerRoot "ft710-server\*") $AppRoot -Recurse -Force
Copy-Item (Join-Path $PyInstallerRoot "scope_pipe.exe") $AppRoot -Force
Copy-Item (Join-Path $PyInstallerRoot "MRRC-FT710.exe") $AppRoot -Force
Copy-Item (Join-Path $RepoRoot "windows") $AppRoot -Recurse -Force

$VendorSource = Join-Path $RepoRoot "vendor\ftdi\windows"
if (Test-Path $VendorSource) {
    $VendorDest = Join-Path $AppRoot "vendor\ftdi\windows"
    New-Item -ItemType Directory -Path (Split-Path $VendorDest) -Force | Out-Null
    Copy-Item $VendorSource $VendorDest -Recurse -Force
}

if (Get-Command iscc -ErrorAction SilentlyContinue) {
    iscc packaging\windows\MRRC-FT710.iss
} else {
    Write-Warning "Inno Setup Compiler 'iscc' was not found. Install Inno Setup and rerun this script to create the setup EXE."
}

Write-Host "Assembled app: $AppRoot"
Write-Host "Installer output: $(Join-Path $DistRoot 'MRRC-FT710-Setup.exe')"
