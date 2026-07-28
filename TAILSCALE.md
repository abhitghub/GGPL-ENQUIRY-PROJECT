# Accessing the portal over Tailscale

The prod stack (`docker-compose.prod.yml`) exposes **only port 3000** — the web
container proxies every `/api/v1/*` call to the API container internally, so
remote users need exactly one port and no CORS/API-URL configuration.

This machine is already on the tailnet as `abhinavkasam` (100.107.104.91,
account `ggplautomation@`).

## Option A — plain HTTP over the tailnet (simplest)

1. Start the portal on this machine:

   ```powershell
   docker compose -f docker-compose.prod.yml up -d --build
   ```

2. Make sure Windows Firewall lets tailnet traffic reach port 3000
   (one-time, **admin** PowerShell; scoped to Tailscale's IP range only):

   ```powershell
   New-NetFirewallRule -DisplayName "GGPL portal via Tailscale" `
     -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3000 `
     -RemoteAddress 100.64.0.0/10
   ```

3. Teammates (must be members of the same tailnet — invite them from
   https://login.tailscale.com/admin/users) open:

   - `http://abhinavkasam:3000` (MagicDNS), or
   - `http://100.107.104.91:3000`

   Login works as-is: the stack sets `SESSION_COOKIE_SECURE=false`, which is
   required for plain-HTTP access.

## Option B — HTTPS with a real certificate (`tailscale serve`)

Gives `https://abhinavkasam.<tailnet>.ts.net` with a valid cert, tailnet-only.

1. Enable **MagicDNS** and **HTTPS certificates** once in the admin console
   (DNS page → HTTPS Certificates → Enable).
2. On this machine:

   ```powershell
   tailscale serve --bg 3000
   tailscale serve status     # shows the https://... URL
   ```

   `tailscale serve` terminates TLS and proxies to localhost:3000, so no
   firewall rule is needed. Turn off with `tailscale serve --https=443 off`.

## Notes

- **Do NOT use `tailscale funnel`** unless you deliberately want the portal on
  the public internet.
- The office-LAN access (`http://<lan-ip>:3000`) keeps working unchanged;
  Tailscale is additive.
- If you run the dev servers instead of Docker, bind the web app to all
  interfaces so the Tailscale interface can reach it:
  `npm run dev -- -H 0.0.0.0` (API stays on 127.0.0.1 — the Next.js rewrite
  proxies to it).
- To restrict which tailnet users can reach this machine, use ACLs in the
  admin console (default is: every tailnet member can reach every device).
