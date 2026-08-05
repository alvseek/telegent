# Deploying telegent (bridge + brain) on the invintiry VPS

telegent runs as **two systemd services** alongside invintiry — no Docker, no
public ingress (the bridge long-polls Telegram outbound; the brain listens on
loopback only). Mirrors the invintiry `deploy/` convention.

| Service | Repo | Runs | Port |
|---|---|---|---|
| `telegent-brain` | universal-chat-agent | `uvicorn application.main:app` | `127.0.0.1:8100` |
| `telegent-bridge` | telegent | `python -m application.main` (long-poll) | none (outbound) |

## One-time setup

Prereqs already provided by the invintiry box: `uv`, `git`, `deploy` user, swap, firewall.

**1. Clone both repos** (as `deploy`):
```bash
cd ~ && git clone https://github.com/alvseek/universal-chat-agent.git
git clone https://github.com/alvseek/telegent.git
```

**2. Create the `.env` files** (as `deploy`) — never commit these:
```bash
cp ~/universal-chat-agent/.env.example ~/universal-chat-agent/.env   # fill OPENROUTER_API_KEY; set PORT=8100, HOST=127.0.0.1
cp ~/telegent/.env.example ~/telegent/.env                           # fill TELEGRAM_BOT_TOKEN; set BRAIN_URL=http://127.0.0.1:8100
```

**3. Install the sudoers grant — RUN AS ROOT, once** (mirrors `deploy-invintiry`):
```bash
sudo cp ~/telegent/deploy/telegent.sudoers /etc/sudoers.d/deploy-telegent
sudo chmod 440 /etc/sudoers.d/deploy-telegent
sudo visudo -cf /etc/sudoers.d/deploy-telegent
```

**4. Set up each app** (as `deploy`) — brain first:
```bash
~/universal-chat-agent/deploy/setup-app.sh
~/telegent/deploy/setup-app.sh
```

## Redeploy after code changes (as `deploy`)

```bash
~/universal-chat-agent/deploy/redeploy.sh   # pull + deps + restart brain
~/telegent/deploy/redeploy.sh               # pull + deps + restart bridge
```

## Ops

```bash
sudo systemctl status telegent-brain telegent-bridge
sudo journalctl -u telegent-brain -f
sudo journalctl -u telegent-bridge -f
curl -s http://127.0.0.1:8100/health        # {"status":"ok"}
```

**One-instance-per-token**: don't run a second bridge on the same bot token
anywhere (Telegram returns 409). The VPS is the single poller once live.
