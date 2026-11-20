param(
    [Parameter(Mandatory=$false)]
    [string]$HostName,
    [Parameter(Mandatory=$false)]
    [string]$CertificateThumbprint,
    [Parameter(Mandatory=$false)]
    [string]$CertificatePath,
    [Parameter(Mandatory=$false)]
    [string]$CertificatePassword
)

$productionPath = "C:\production"

$callbackPath = Join-Path $productionPath "Artifacts\Cmune.Channels.Callback"
if (-not (Test-Path $callbackPath)) {
  Write-Error "callback directory missing: $callbackPath"
  exit 1
}

$callbackName = "UberStrikeChannelCallback"

# Create app pool
if (-not (Test-Path "IIS:\AppPools\UberStrikeAppPool" -ErrorAction SilentlyContinue)) {
    New-WebAppPool -Name "UberStrikeAppPool"
}

if (Get-Website -Name $callbackName -ErrorAction SilentlyContinue) {
    Write-Host "Website '$callbackName' already exists."
} else {
    if (Get-Website -Name "Default Web Site" -ErrorAction SilentlyContinue) {
        Remove-Website -Name "Default Web Site"
    }

    # Create website at the root so the callback handlers are reachable without a virtual path
    if ([string]::IsNullOrEmpty($HostName)) {
        New-Website -Name $callbackName -Port 80 -PhysicalPath $callbackPath -ApplicationPool "UberStrikeAppPool"
    } else {
        New-Website -Name $callbackName -Port 80 -PhysicalPath $callbackPath -ApplicationPool "UberStrikeAppPool" -HostHeader $HostName
    }
}

if (-not [string]::IsNullOrEmpty($CertificatePath)) {
    if (-not (Test-Path -LiteralPath $CertificatePath)) {
        Write-Error "certificate file missing: $CertificatePath"
        exit 1
    }

    if ([string]::IsNullOrEmpty($CertificatePassword)) {
        $securePassword = New-Object System.Security.SecureString
    } else {
        $securePassword = ConvertTo-SecureString -String $CertificatePassword -AsPlainText -Force
    }

    $importedCertificate = Import-PfxCertificate -FilePath $CertificatePath -CertStoreLocation Cert:\LocalMachine\My -Password $securePassword
    $CertificateThumbprint = $importedCertificate.Thumbprint
    Remove-Item -LiteralPath $CertificatePath -Force
}

if (-not [string]::IsNullOrEmpty($CertificateThumbprint)) {
    if ([string]::IsNullOrEmpty($HostName)) {
        Write-Warning "HTTPS binding skipped: --webservice-hostname is required."
    } else {
        $thumbprint = ($CertificateThumbprint -replace '\s', '').ToUpper()

        $httpsBinding = Get-WebBinding -Name $callbackName -Protocol https -Port 443 -HostHeader $HostName -ErrorAction SilentlyContinue
        if (-not $httpsBinding) {
            # SslFlags 1 = SNI, required to share port 443 with other sites
            New-WebBinding -Name $callbackName -Protocol https -Port 443 -HostHeader $HostName -SslFlags 1
            $httpsBinding = Get-WebBinding -Name $callbackName -Protocol https -Port 443 -HostHeader $HostName
        }

        $httpsBinding.AddSslCertificate($thumbprint, "My")
        Write-Host "HTTPS binding configured for $HostName with certificate $thumbprint"
    }
}

if ((Get-Website -Name $callbackName).State -ne "Started") {
    Start-Website -Name $callbackName
}

if ([string]::IsNullOrEmpty($HostName)) {
    Write-Host "Callback channel available at http://<server>/StripeHandler.aspx"
} else {
    Write-Host "Callback channel available at http://$HostName/StripeHandler.aspx"
    if (-not [string]::IsNullOrEmpty($CertificateThumbprint)) {
        Write-Host "Callback channel available at https://$HostName/StripeHandler.aspx"
    }
}
