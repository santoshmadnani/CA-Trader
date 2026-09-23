# CA Trader: Laptop Server & Zero-Cost Hosting Guide

This guide explains how to use your Windows laptop as the primary server and database storage for **CA Trader**, eliminating AWS cloud hosting fees while keeping your data 100% private and portable.

---

## 1. Quick Start (Running on Your Laptop)

### Starting the Server
1. Open the folder: `CA_Trader\app\server_host\`
2. Double-click: **`start_laptop_server.bat`**
3. The server will:
   - Create an automatic timestamped database backup in `server_host/backups/`.
   - Inhibit Windows sleep (CPU stays awake while plugged in).
   - Start the backend on `http://127.0.0.1:8000`.
   - Launch an encrypted Cloudflare Tunnel and display a public `https://xxxx.trycloudflare.com` URL.

### Accessing the Terminal
- **On your laptop**: Open [http://127.0.0.1:8000/terminal](http://127.0.0.1:8000/terminal)
- **On your phone, tablet, or external device**: Open the live `https://xxxx.trycloudflare.com/terminal` link displayed in the launcher console window.

### Stopping the Server
Press `Ctrl + C` in the console window. The server shuts down cleanly, terminates the tunnel, and releases the sleep lock.

---

## 2. Keeping the Laptop Awake (Power Configuration)

To ensure the server runs continuously during market hours even when the laptop lid is closed:

1. Open **Windows Control Panel** (or press `Win + R`, type `powercfg.cpl`, and press Enter).
2. On the left side, click **"Choose what closing the lid does"**.
3. Under **"When plugged in"**, set:
   - **"When I close the lid"** -> **"Do nothing"**
4. Click **"Save changes"**.
5. Keep your laptop plugged into its power adapter during trading hours.

> [!NOTE]
> `start_laptop_server.py` automatically invokes Windows API `SetThreadExecutionState` (`ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED`), keeping the CPU and network alive even if screen timeout occurs.

---

## 3. Database Synchronization (AWS -> Laptop)

Your live AWS server currently stores user accounts and trading recommendations in `/home/ubuntu/ca-trader-data/ca_trader.sqlite3`.

To refresh your local database with the latest records from AWS at any time:
```cmd
cd CA_Trader\app
python tools\sync_db_from_aws.py
```
This tool:
1. Creates a safety backup of your existing local database.
2. Streams the live database directly from AWS EC2 (`ca-trader-key.pem`).
3. Runs SQLite integrity check verification automatically.

---

## 4. Current State: Dual-Running (AWS + Laptop)

Right now, **both systems work in parallel without interference**:
- **AWS Server**: Serves your primary domain **`https://catrader.site`** on EC2 IP `15.252.81.122`.
- **Laptop Server**: Serves your local instance on `http://127.0.0.1:8000` and via the test Cloudflare Tunnel.

---

## 5. Cutover Plan: Pointing `catrader.site` to Laptop When AWS Expires

When your AWS membership is ready to expire, switch `catrader.site` to your laptop permanently with ₹0 ongoing cost:

### Option A: Cloudflare Named Tunnel (Recommended - 100% Free Forever)
1. Sign up for a free Cloudflare account at [dash.cloudflare.com](https://dash.cloudflare.com).
2. Go to **Zero Trust** -> **Networks** -> **Tunnels** -> Click **"Create a tunnel"**.
3. Choose **Cloudflared**, name it `catrader-laptop`.
4. Copy the tunnel token into `server_host/host_config.json`.
5. Under **Public Hostname**, enter:
   - Domain: `catrader.site`
   - Service Type: `HTTP`
   - URL: `localhost:8000`
6. In `server_host/host_config.json`, change `"mode": "quick"` to `"mode": "named"`.
7. Double-click `start_laptop_server.bat` -> `https://catrader.site` is now live from your laptop!

### Option B: Namecheap DNS Subdomain (Zero Account Needed)
If you prefer not to change nameservers, you can point a CNAME in Namecheap (e.g. `app.catrader.site` or `laptop.catrader.site`) directly to your Cloudflare Tunnel hostname.

---

## 6. How to Migrate to a NEW Laptop in the Future

The entire hosting environment is self-contained. To switch to a new laptop at any point:

1. **Copy or Git Clone**:
   Copy the `CA_Trader` folder to the new laptop, or run:
   ```cmd
   git clone -b CA-Trader-Bifurcated https://github.com/santoshmadnani/CA-Trader.git
   ```
2. **Install Prerequisites (One-Click)**:
   Double-click `server_host\install_host_prerequisites.bat`
   *(Installs python libraries and downloads the standalone `cloudflared.exe` in ~60 seconds)*.
3. **Run the Server**:
   Double-click `server_host\start_laptop_server.bat`
   *(Your new laptop is now the active CA Trader server!)*.

---

## 7. Configuration Reference (`server_host/host_config.json`)

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `server.port` | `8000` | Local port for CA Trader web server |
| `server.host` | `127.0.0.1` | Set to `0.0.0.0` to also allow direct access from local home Wi-Fi devices |
| `database.auto_backup_on_start` | `true` | Creates a timestamped `.sqlite3` copy before every launch |
| `database.max_backups_to_retain` | `15` | Automatically purges older backup snapshots |
| `tunnel.mode` | `"quick"` | `"quick"` gives instant URL; change to `"named"` for custom domain `catrader.site` |
| `power_management.prevent_system_sleep`| `true` | Prevents Windows sleep while the server process is alive |

