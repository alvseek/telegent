# Deploying telegent (bridge + brain) on the invintiry VPS

telegent runs as **two systemd services** alongside invintiry — no Docker, no
public ingress (the bridge long-polls Telegram outbound; the brain listens on
loopback only). Mirrors the invintiry `deploy/` convention.

## Repository layout (monorepo)
telegent is now the Option-2 monorepo:
- `application/bridge/` — the Telegram bridge (this repo's own code).
- `application/brain/` — the `universal-chat-agent` brain, a **git submodule** (clone with `--recursive`).
- `deploy/` — deploy scripts at the repo root.

> ⚠️ **Production migration pending.** The live VPS still runs the pre-restructure
> flat layout (bridge at `/home/deploy/telegent`, brain as a separate clone at
> `/home/deploy/universal-chat-agent`). The steps below describe the NEW layout;
> migrating the box is a **coordinated redeploy** (see *Migrating the live box*
> at the bottom) — not a plain `git pull`, because the bridge's WorkingDirectory
> and venv location change. Do it deliberately, not incidentally.

| Service | Repo | Runs | Port |
|---|---|---|---|
| `telegent-brain` | universal-chat-agent | `uvicorn application.main:app` | `127.0.0.1:8100` |
| `telegent-bridge` | telegent | `python -m application.main` (long-poll) | none (outbound) |

## One-time setup

Prereqs already provided by the invintiry box: `uv`, `git`, `deploy` user, swap, firewall.

**1. Clone the monorepo recursively** (as `deploy`) — pulls the brain submodule into `application/brain`:
```bash
cd ~ && git clone --recursive https://github.com/alvseek/telegent.git
```

**2. Create the `.env` files** (as `deploy`) — never commit these:
```bash
cp ~/telegent/application/brain/.env.example  ~/telegent/application/brain/.env    # fill OPENROUTER_API_KEY; set PORT=8100, HOST=127.0.0.1
cp ~/telegent/application/bridge/.env.example ~/telegent/application/bridge/.env   # fill TELEGRAM_BOT_TOKEN; set BRAIN_URL=http://127.0.0.1:8100
```

**3. Root setup — RUN AS ROOT, once** (installs the sudoers grant; mirrors invintiry's `setup.sh`):
```bash
bash /home/deploy/telegent/deploy/setup.sh
```

**4. Set up each app** (as `deploy`) — brain first:
```bash
~/telegent/application/brain/deploy/setup-app.sh   # brain — NOTE: submodule's own scripts still assume the standalone path; reconcile during migration
~/telegent/deploy/setup-app.sh                     # bridge — paths already updated for the monorepo
```

## Redeploy after code changes (as `deploy`)

```bash
# brain: cd into the submodule, pull it, run its redeploy (path reconcile pending)
~/telegent/deploy/redeploy.sh                # bridge: pulls the monorepo root + reinstalls application/bridge deps + restart
```

## Migrating the live box (one-time, coordinated — NOT a plain pull)
The VPS still runs the pre-restructure flat layout. To move it onto this monorepo:
1. As `deploy`, in `~/telegent`: `git pull` then `git submodule update --init --recursive` (files move to `application/bridge/`, brain populates `application/brain/`).
2. Recreate the bridge venv at the new location: `cd ~/telegent/application/bridge && uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt`. Move the `.env` too (`~/telegent/.env` → `~/telegent/application/bridge/.env`).
3. Reinstall the bridge unit (new `WorkingDirectory`): `sudo cp ~/telegent/deploy/telegent-bridge.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart telegent-bridge`.
4. Verify: `systemctl is-active telegent-bridge` + a real Telegram round-trip.
5. **Open**: the brain still runs from the standalone `~/universal-chat-agent` clone; reconciling it onto `application/brain` (and its own deploy scripts) is part of the `telegent-deploy` work — do it deliberately, keeping the brain reachable on `127.0.0.1:8100` throughout.

## Ops

```bash
sudo systemctl status telegent-brain telegent-bridge
sudo journalctl -u telegent-brain -f
sudo journalctl -u telegent-bridge -f
curl -s http://127.0.0.1:8100/health        # {"status":"ok"}
```

**One-instance-per-token**: don't run a second bridge on the same bot token
anywhere (Telegram returns 409). The VPS is the single poller once live.
