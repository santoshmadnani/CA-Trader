# CA Trader

FastAPI + Upstox trading terminal, served at catrader.site in Docker behind Caddy.

## Files

| File | What it is |
| --- | --- |
| `app.py` | The app: API, auth, Upstox, paper trading |
| `mcp_server.py` | Read-only connector for Claude (`/mcp/<secret>`), the shared terminal routes (`/terminal`, `/classic`, `/api/term/call`) and `/api/model/*` |
| `ca_model.py`, `ca_model_params.json` | Backtested daily model and its parameters (also holds the intraday trade-call rule) |
| `ca_terminal.html` | The terminal page. The same page runs as the Claude artifact (data from the connector) and at `/terminal` (data from `/api/term/call`) |
| `terminal.html` | The previous terminal, still at `/classic` |
| `terminal_selector.html`, `CA_Trader_Login.html`, `fitness.html` | Selector, login and fitness pages |
| `deploy.py` | Sync, deploy and server clean-up |
| `docs/` | Audit, handover and research reports |

## Deploying

From your PC, in this folder:

```
python deploy.py status         # what is where
python deploy.py sync           # bring app.py etc. from your working folder (CA_Trader\7) into the repo and push
python deploy.py deploy         # upload and run deploy.sh on the server, then health-check
python deploy.py clean-server   # old zips, old backups, unused images; asks before deleting
```

`deploy.py` picks the server that catrader.site points to and finds its SSH key in the usual folders; override with `--host` and `--key`.
Run `sync` before the first `deploy`: the server runs releases newer than the `app.py` that was in GitHub before this change.
