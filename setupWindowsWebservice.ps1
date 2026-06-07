param(
    [Parameter(Mandatory=$false)]
    [string]$HostName
)

$productionPath = "C:\production"

$webservicePath = Join-Path $productionPath "Artifacts\UberStrike.DataCenter.WebService"
if (-not (Test-Path $webservicePath)) {
  Write-Error "webservice directory missing: $webservicePath"
  exit 1
}

$webserviceName = "UberStrikeWebService"

if (Get-Website -Name $webserviceName -ErrorAction SilentlyContinue) {
    Write-Host "Website '$webserviceName' already exists. Exiting script."
    exit
}

if (Get-Website -Name "Default Web Site" -ErrorAction SilentlyContinue) {
    Remove-Website -Name "Default Web Site"
}

# Create app pool
if (-not (Test-Path "IIS:\AppPools\UberStrikeAppPool" -ErrorAction SilentlyContinue)) {
    New-WebAppPool -Name "UberStrikeAppPool"
}

# Create website
if ([string]::IsNullOrEmpty($HostName)) {
    New-Website -Name $webserviceName -Port 80 -PhysicalPath $webservicePath -ApplicationPool "UberStrikeAppPool"
} else {
    New-Website -Name $webserviceName -Port 80 -PhysicalPath $webservicePath -ApplicationPool "UberStrikeAppPool" -HostHeader $HostName
}

Start-Website -Name $webserviceName
