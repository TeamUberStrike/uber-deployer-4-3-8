# Install IIS with typical features + HTTP Activation
Enable-WindowsOptionalFeature -Online -FeatureName @(
    "IIS-WebServerRole",
    "IIS-WebServer",
    "IIS-CommonHttpFeatures",
    "IIS-StaticContent",
    "IIS-DefaultDocument",
    "IIS-DirectoryBrowsing",
    "IIS-HttpErrors",
    "IIS-ApplicationDevelopment",
    "IIS-ASPNET45",
    "IIS-NetFxExtensibility45",
    "IIS-ISAPIExtensions"
) -All

Install-WindowsFeature `
    Net-Framework-Core, `
    NET-HTTP-Activation, `
    NET-WCF-HTTP-Activation45

