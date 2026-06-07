param(
    [Parameter(Mandatory=$false)]
    [string]$HostName
)

$productionPath = "C:\production"

$portalPath = Join-Path $productionPath "Artifacts\UberStrike.Channels.Portal"
$commonChannelPath = Join-Path $portalPath "CommonChannel"
if (-not (Test-Path $portalPath)) {
  Write-Error "portal directory missing: $portalPath"
  exit 1
}

$webserviceName = "UberStrikePortal"
$commonChannelName = "CommonChannel"

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
    New-Website -Name $webserviceName -Port 80 -PhysicalPath $portalPath -ApplicationPool "UberStrikeAppPool"
} else {
    New-Website -Name $webserviceName -Port 80 -PhysicalPath $portalPath -ApplicationPool "UberStrikeAppPool" -HostHeader $HostName
}

# Add application with common channel path
if (Test-Path $commonChannelPath) {
    New-WebApplication -Name $commonChannelName -Site $webserviceName -PhysicalPath $commonChannelPath -ApplicationPool "UberStrikeAppPool"
} else {
    Write-Warning "Common channel path does not exist: $commonChannelPath"
}

Start-Website -Name $webserviceName
