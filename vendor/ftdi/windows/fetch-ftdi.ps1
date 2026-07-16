$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Downloads = Join-Path $Here "downloads"
$Bin = Join-Path $Here "bin\x64"

New-Item -ItemType Directory -Path $Downloads -Force | Out-Null
New-Item -ItemType Directory -Path $Bin -Force | Out-Null

$Files = @(
    @{
        Name = "LibFT4222-v1.4.8.zip"
        Url = "https://ftdichip.com/wp-content/uploads/2025/06/LibFT4222-v1.4.8.zip"
    },
    @{
        Name = "CDM-v2.12.36.20-WHQL-Certified.zip"
        Url = "https://ftdichip.com/wp-content/uploads/2025/03/CDM-v2.12.36.20-WHQL-Certified.zip"
    }
)

foreach ($file in $Files) {
    $target = Join-Path $Downloads $file.Name
    if (Test-Path $target) {
        Write-Host "Already exists: $target"
        continue
    }
    try {
        Invoke-WebRequest -Uri $file.Url -OutFile $target -Headers @{ "User-Agent" = "Mozilla/5.0" }
        Write-Host "Downloaded: $target"
    } catch {
        Write-Warning "Could not download $($file.Name): $($_.Exception.Message)"
        Write-Warning "Open this URL in a browser and save it to: $target"
        Write-Warning $file.Url
    }
}

Write-Host ""
Write-Host "After downloading, extract these files into:"
Write-Host "  $Bin"
Write-Host ""
Write-Host "Required final files:"
Write-Host "  $(Join-Path $Bin 'FT4222.dll')"
Write-Host "  $(Join-Path $Bin 'ftd2xx.dll')"
