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
New-WebAppPool -Name "UberStrikeAppPool"

# Create website
New-Website -Name "UberStrikeWebService" -Port 80 -PhysicalPath $webservicePath -ApplicationPool "UberStrikeAppPool"

Start-Website -Name $webserviceName

