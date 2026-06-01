# Brain Dashboard

Custom web UI for observing Glados's live thought pipeline, memory, skills, and monitoring.

## Quick start

```powershell
# 1. Python API (from repo root)
pip install fastapi "uvicorn[standard]" watchdog
python -m brain_server.main

# 2. Build frontend (one time, or after UI changes)
cd brain_web
npm install
npm run build

# 3. Open http://localhost:8080/hud/ for the JARVIS-style Command Center (F11 fullscreen)
#    Or http://localhost:8080/ for the observatory dashboard
```

Or use the system tray: `python tray_launcher.py` — starts kernel + brain server, menu **Open Brain Dashboard**.

## LAN access (phone / tablet)

1. Set your PC LAN IP in `configs/glados.yaml`:
   ```yaml
   brain_dashboard_url: "http://192.168.1.50:8080"
   ```
2. Allow Windows Firewall (Private network only):
   ```powershell
   netsh advfirewall firewall add rule name="Glados Brain Dashboard" dir=in action=allow protocol=TCP localport=8080 profile=private
   ```
3. On another device on the same WiFi, open `brain_dashboard_url`.

## Development

Run API and Next.js dev server separately:

```powershell
python -m brain_server.main
cd brain_web && npm run dev
```

Next.js dev: http://localhost:3000 (proxies API via `NEXT_PUBLIC_API_URL`).

## Optional auth

Set `brain_dashboard_token` in config or `BRAIN_DASHBOARD_TOKEN` env var. Store token in browser:
`localStorage.setItem('glados_brain_token', 'your-token')`.
