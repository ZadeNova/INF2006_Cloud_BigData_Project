# Running the load test

Short version. Full reference: [tests/load/README.md](../tests/load/README.md). The recorded runs and how they were judged: [evidence/test-performance.md](../evidence/test-performance.md) and [evidence/load-summary.md](../evidence/load-summary.md).

## Without AWS (anyone, free, a few minutes)

```bash
cd tests/load
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python selftest.py                                           # the harness's own checks (16 of 16)
python analyze.py --raw ../../evidence/raw --out /tmp/summary.md   # rebuilds the tables from our recorded runs
```

A smoke run against the local Docker shop (from the repository root first: `docker compose up -d`, then import the dataset as in [src/README.md](../src/README.md)):

```bash
cd tests/load && cp .env.example .env     # set LOADTEST_PASSWORD to any strong value
set -a; . ./.env; set +a
python accounts.py create --base-url http://127.0.0.1:8000 --count 4
python run.py smoke --base-url http://127.0.0.1:8000 --yes
```

This exercises login, browsing, cart and checkout for 75 seconds. It proves the harness works; it says nothing about AWS capacity.

## Against your own stack B (needs REPRODUCE_CLOUD.md level 2)

The harness refuses any host that is not ours or localhost, so for your own domain set `LOAD_DOMAIN` in `tests/load/.env`. The generator must run **in us-east-1 on its own instance**, never on the app and never on a laptop, or the numbers measure your network.

1. **Laptop, once.** `cd tests/load`, create the venv as above, `cp .env.example .env`, set `LOADTEST_PASSWORD`, `LOAD_BASE_URL=https://shop-fargate.<your domain>` and `LOAD_DOMAIN=<your domain>`.
2. **Bundle the code for the generator** (code and history, never `.env`), from the repository root: `git bundle create ~/repo.bundle HEAD`.
3. **Start the generator.** `src/infrastructure/scripts/up.sh loadgen`; note the instance id it prints. Then upload the bundle: `B=$(terraform -chdir=src/infrastructure/base output -raw s3_bucket_name); aws s3 cp ~/repo.bundle s3://$B/exports/tools/repo.bundle`.
4. **Open a shell on it** inside `tmux` (a dropped connection then does not stop the run): `aws ssm start-session --target <id>`, then `ls /var/lib/loadgen-ready && tmux new -s load`. If the file is missing, wait a minute.
5. **Set it up** (on the generator): `B=<bucket>; aws s3 cp s3://$B/exports/tools/repo.bundle . && git clone repo.bundle inf2006 && cd inf2006/tests/load && python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`, then `read -rs LOADTEST_PASSWORD && export LOADTEST_PASSWORD` (type the same password as on the laptop; nothing is echoed) and `export LOAD_BASE_URL=https://shop-fargate.<your domain>`.
6. **Create the test accounts once** (about 10 minutes): `python accounts.py create --base-url $LOAD_BASE_URL`.
7. **Run.** Saturation (1 to 512 users, about 20 minutes): `python run.py saturation --variant fargate --base-url $LOAD_BASE_URL --repeat 1 --location us-east-1`. It prints the run id, the duration and the cost, and asks `Start? [y/N]`. Scale-out and replacement runs also need `aws_capture.py watch` (and `kill`) running on the laptop; see the README.
8. **Export before you tear anything down.** On the generator: `aws s3 cp --recursive out/<RUN-ID> s3://$B/exports/load/<RUN-ID>/`. On the laptop: `aws s3 cp --recursive s3://$B/exports/load/<RUN-ID> out/<RUN-ID>`, then `python aws_capture.py export --variant fargate --run-id <RUN-ID> --run-dir out/<RUN-ID>`, then `python analyze.py --out ../../evidence/load-summary.md`. CloudWatch keeps one-minute data for only about 15 days.
9. **Clean up.** `python reset_state.py --target fargate --apply` removes the orders the run created (dry run first, without `--apply`). Then `down.sh loadgen` and `down.sh fargate`.

## Mistakes we made, so you do not

- Never paste lab credentials into a chat or a screenshot; they rotate on Start Lab.
- The password prompt (`read -rs`) shows nothing as you type, and arrow keys are swallowed. Type it plainly and press Enter.
- Run the harness on the generator, not the laptop. The laptop only runs `aws_capture.py`, which needs lab credentials.
- Do the WAF count-mode check: with the rate rule in block mode the load test's logins are rejected.
- Results are indicative: one repeat each, the 3D models are not fetched, and the load shape is a closed model (users wait between actions).
