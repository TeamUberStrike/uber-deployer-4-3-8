New-NetFirewallRule -DisplayName "UberStrike Photon UDP" -Direction Inbound -LocalPort 5055,5155 -Protocol UDP -Action Allow
New-NetFirewallRule -DisplayName "UberStrike Photon UDP" -Direction Outbound -LocalPort 5055,5155 -Protocol UDP -Action Allow

New-NetFirewallRule -DisplayName "UberStrike Photon TCP" -Direction Inbound -LocalPort 843 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "UberStrike Photon TCP" -Direction Outbound -LocalPort 843 -Protocol TCP -Action Allow

New-NetFirewallRule -DisplayName "UberStrike Webservice" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "UberStrike Webservice" -Direction Outbound -LocalPort 80 -Protocol TCP -Action Allow

