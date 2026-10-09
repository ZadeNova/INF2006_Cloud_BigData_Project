# Setup from a blank computer (Windows, macOS, Linux)

For a marker, a teammate or anyone new. It covers installing every tool, then running the project. Pick a path:

| Path | What you get | Tools | Time on a fresh machine |
|---|---|---|---|
| **A. Offline** (enough for marking) | The shop, its tests, the analytics and the load-test tables, on your computer | Git, Docker, Python 3 | about 30 to 45 minutes, most of it installing Docker; about 10 minutes once tools exist |
| **B. Cloud** (optional) | Variant B, the final architecture, deployed in your own AWS Learner Lab | Path A tools plus Terraform, AWS CLI, Session Manager plugin, jq, and on Windows WSL 2 | about 1.5 hours the first time (tool install, about 45 minutes of AWS waiting, DNS delegation) |
| **C. Load test** (optional) | A load run against your own cloud stack | Path B | about 1 hour plus the runs |

Measured times for each step are at the end ([timings](#measured-timings)).

## 1. Install the tools for path A

| Tool | Windows 10/11 | macOS | Linux (Ubuntu/Debian; Fedora in brackets) | Check it works |
|---|---|---|---|---|
| **Git** | `winget install Git.Git` or [git-scm.com](https://git-scm.com/downloads) | `xcode-select --install` (or `brew install git`) | `sudo apt install git` (`sudo dnf install git`) | `git --version` |
| **Docker** with Compose 2.20 or later | [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) (`winget install Docker.DockerDesktop`); it turns on WSL 2; restart when asked | [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) (`brew install --cask docker`), then open it once | [Docker Engine and the Compose plugin](https://docs.docker.com/engine/install/) (Fedora: `sudo dnf install docker docker-compose-plugin`), then `sudo systemctl enable --now docker` and `sudo usermod -aG docker $USER` (log out and in) | `docker compose version` (2.20+), `docker run --rm hello-world` |
| **Python 3** (any recent version for the shop; the analytics run in a Python 3.13 container, see below) | `winget install Python.Python.3.13`; tick "Add to PATH" | `brew install python@3.13` | `sudo apt install python3 python3-venv` (`sudo dnf install python3`) | `python --version` (Windows) or `python3 --version` |

Docker Desktop must be **running** (whale icon) before any `docker` command. Give it at least 4 GB of memory (Settings, Resources).

**Command names differ by system.** Where this guide writes `python3`, Windows uses `python` (or `py`). Virtual-environment programs live in `.venv/bin/` on macOS and Linux and in `.venv\Scripts\` on Windows. Commands below are written once; they work in PowerShell, Terminal (zsh) and bash unless marked.

## 2. Path A: run everything offline

```bash
git clone <repository URL> inf2006 && cd inf2006      # or unzip the submission and cd into it
python3 src/tools/init_env.py                          # once: writes src/.env with random local secrets (never printed)
docker compose up --build -d --wait                    # builds the image, starts PostgreSQL and the shop
docker compose run --rm web python manage.py check_database        # expect: database reachable, migrations applied
```

Open **http://127.0.0.1:8000/**. If port 8000 is busy, set `APP_PORT=8001` in `src/.env` and restart.

**Load the demo data** (the store starts empty):

```bash
python3 analytics/build_shoe_dataset.py               # builds data/derived/shoes from data/raw (standard library only)
docker compose run --rm web python manage.py import_dataset --source /app/data/derived/shoes --namespace synthetic/shoes/revision-a/demo/v1
docker compose run --rm web python manage.py seed_demo --no-products            # the operator login demo-operator
docker compose run --rm web python manage.py refresh_analytics --as-of 2026-01-02
```

Register a customer at `/register/` to shop. The operator dashboard is at `/analytics/`; the local operator password is described in [src/README.md](../src/README.md#demo-data).

**Run the tests:**

```bash
docker compose run --rm web pytest -q -p no:cacheprovider /app/tests          # the application suite
```

**Analytics and the ML checks.** The pinned analytics libraries (pandas 2.3.2 and friends) need **Python 3.13**; they do not install on Python 3.14. So run them in the official Python 3.13 container, the same one CI uses. One command, identical on Windows (PowerShell), macOS and Linux:

```bash
docker run --rm -v "${PWD}:/work:z" -w /work -e OMP_NUM_THREADS=1 python:3.13-slim-bookworm sh -c "pip install -q -r analytics/requirements.txt pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0 && python analytics/profile_dataset.py --source data/raw && python -m pytest -q -c /dev/null -p no:cacheprovider analytics/tests/test_segment_customers.py analytics/tests/test_evaluate_holdout.py"
```

Expect `integrity PASS` for the dataset profile (written to `data/PROFILE.md`) and `22 passed`. (`:z` is needed on SELinux systems such as Fedora and is harmless elsewhere.) If you prefer a host environment, create it with Python 3.13 exactly.

The full ML batch (training, export, import) is in [analytics/README.md](../analytics/README.md).

**Re-derive the load-test results from the recorded evidence** (no cloud):

```bash
cd tests/load
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt            # Windows: .venv\Scripts\pip
.venv/bin/python selftest.py                                                    # 16 checks
.venv/bin/python analyze.py --raw ../../evidence/raw --out summary-check.md    # same tables as evidence/load-summary.md
cd ../..
```

**Stop:** `docker compose down` (keeps the database). `docker compose down --volumes` deletes the local database.

## 3. Path B: tools for the cloud (optional)

The cloud scripts are **bash**. On Windows, use **WSL 2** for everything in this section: `wsl --install -d Ubuntu` in an administrator PowerShell, restart, open "Ubuntu", then follow the Linux column inside it (Docker Desktop is shared with WSL automatically: Settings, Resources, WSL integration). Clone the repository again inside WSL (`~/inf2006`), not under `/mnt/c`.

| Tool | macOS | Linux and WSL (Ubuntu/Debian) | Check |
|---|---|---|---|
| **Terraform 1.10 or later** (recorded with 1.16.4) | `brew tap hashicorp/tap && brew install hashicorp/tap/terraform` | the HashiCorp apt repository: [developer.hashicorp.com/terraform/install](https://developer.hashicorp.com/terraform/install) | `terraform version` |
| **AWS CLI v2** | `brew install awscli` | [the official installer](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) (`curl ... awscli-exe-linux-x86_64.zip`, `unzip`, `sudo ./aws/install`) | `aws --version` (2.x) |
| **Session Manager plugin** (path C, and debugging) | `brew install --cask session-manager-plugin` | [the .deb or .rpm](https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-debian-and-ubuntu.html) | `session-manager-plugin --version` |
| **jq, openssl, curl, dig, unzip** | `brew install jq` (the others ship with macOS) | `sudo apt install jq openssl curl dnsutils unzip` (Fedora: `jq openssl curl bind-utils unzip`) | `jq --version` |

Then you need:
- **An AWS Academy Learner Lab** (the course provides it). Region `us-east-1`.
- **A domain you control** (any registrar). HTTPS needs a certificate, and you will set the domain's name servers once.
- **Lab credentials in each terminal**: add the `labcreds` helper from [src/infrastructure/README.md](../src/infrastructure/README.md#tools-and-credentials) to `~/.bashrc` (or `~/.zshrc`), then run `labcreds` and paste the lab's "AWS CLI" block. They expire after about 4 hours.

Check everything at once: `src/infrastructure/scripts/status.sh` lists missing tools and what to do next. Then follow [REPRODUCE_CLOUD.md](REPRODUCE_CLOUD.md), level 2: `up.sh base`, set the name servers at your registrar when asked, then `up.sh fargate`. **Always finish with `down.sh fargate`**, and with the "Final teardown" in the infrastructure README when you are done for good. Cost: about USD 3.5 per day while variant B runs, plus about USD 1.2 per day for the shared base (list prices checked 9 October 2026).

## 4. Path C: the load test (optional)

[RUN_LOADTEST.md](RUN_LOADTEST.md). It needs path B running and the Session Manager plugin.

## 5. When something goes wrong

| Symptom | Fix |
|---|---|
| `docker: command not found`, or "Cannot connect to the Docker daemon" | Start Docker Desktop (Windows, macOS) or `sudo systemctl start docker` (Linux); on Linux, log out and in after `usermod -aG docker` |
| `python: command not found` (macOS, Linux) | Use `python3` |
| Port 8000 already in use | `APP_PORT=8001` in `src/.env`, then `docker compose up -d` |
| `import_dataset` reports a conflict | The database already has demo products: `docker compose down --volumes`, then start again (this deletes local data) |
| `$'\r': command not found` when running a `.sh` script | The file was checked out with Windows line endings. Clone inside WSL, or run `git config core.autocrlf input` and clone again |
| Tests run against old code | `docker compose build web`, then run them again (the image holds the code) |
| A cloud script says "no working lab credentials" | Run `labcreds` again; lab credentials expire after about 4 hours |
| SELinux denies the bind mounts (Fedora) | Already handled by the `:z` label in compose; no action needed |

## Measured timings

A clean clone at commit `4dbee24`, following path A on 9 October 2026 (Linux, Docker 29.6, base images already downloaded). Full log: [evidence/raw/REPRO-01_2026-10-09_linux_clean-clone.txt](../evidence/raw/REPRO-01_2026-10-09_linux_clean-clone.txt).

| Step | Seconds | Result |
|---|---|---|
| `git clone` (37 MB with history; from GitHub add 10 to 60 s) | 0 (local) | ok |
| `init_env.py` | 0 | `src/.env` written |
| Image build, no cache | 17 | ok |
| `docker compose up -d --wait` | 11 | web and db healthy |
| `check_database` | 3 | ok |
| Full test suite | 24 | **497 passed, 8 skipped** |
| Build the derived dataset | 4 | checksums match |
| `import_dataset` | 25 | ok |
| `seed_demo --no-products`, `refresh_analytics` | 7 | ok |
| Shop answers `/products/` | under 1 | HTTP 200 |
| Analytics in the Python 3.13 container (install, profile, ML tests) | 21 | integrity PASS, 22 passed |
| Load harness: install and `selftest.py` | 7 | 16 of 16 PASS |
| `analyze.py` over the recorded raw evidence | 1 | identical to `evidence/load-summary.md` |
| **Total machine time** | **about 2 minutes** | |

On a machine that has never pulled the images, add the downloads: PostgreSQL 17 (about 160 MB), Python 3.13 slim (about 45 MB) and the Python packages: **about 5 minutes** in all on a typical connection. Installing Docker Desktop itself takes 10 to 20 minutes and may need a restart. Found by this rehearsal and fixed in the guide: the analytics requirements do not install on Python 3.14, hence the container command above.
