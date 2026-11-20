# Execution

Example command
```
poetry run python .\deploy.py --path C:\code\uber-server-4-3-8\Artifacts portal --webservice-hostname ws-dev.uberforever.eu
```
`path` must be a path to Artifacts.

Callback channel only (deploys `Cmune.Channels.Callback` only and hosts it at the site root):
```
poetry run python .\deploy.py --path C:\code\uber-server-4-3-8\Artifacts callback --webservice-hostname payments.uberstrike.com
```
The callback channel gets its own `UberStrikeChannelCallback` IIS site bound to
`payments.uberstrike.com`, so the Stripe webhook URL is
`http://payments.uberstrike.com/StripeHandler.aspx`.

## HTTPS with a Cloudflare Origin Certificate

Create an Origin Certificate for `payments.uberstrike.com` in the Cloudflare
dashboard, save the certificate and key, then convert them to a PFX:
```
openssl pkcs12 -export -out payments.pfx -inkey origin.key -in origin.crt
```
Deploy with HTTPS binding (SNI on port 443):
```
poetry run python .\deploy.py --path C:\code\uber-server-4-3-8\Artifacts callback --webservice-hostname payments.uberstrike.com --cert-pfx C:\certs\payments.pfx --cert-password <pfx-password>
```
The PFX password can also be set as `CERT_PASSWORD` in `.env`. If the certificate
is already imported into `LocalMachine\My`, use `--cert-thumbprint <thumbprint>`
instead of `--cert-pfx`. Keep Cloudflare SSL/TLS mode on Full (strict).

