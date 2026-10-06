# ADR-016: Start the Fargate task with a command that sets the health-probe host

**Status:** drafted by the writing session for review (6 October 2026).

## Decision

The ALB health-checks a target by its **private IP**, so the request arrives with `Host: <ip>:8000`. Django refuses unknown hosts, except the one named in `DJANGO_HEALTH_PROBE_HOST` (one private IPv4 address and port 8000, `config/settings.py`). On EC2 the user data reads the IP from the instance metadata service before it starts the container. A Fargate task's IP exists only once it runs, so the task definition replaces the container's start command with a short shell script that:

1. reads the task's IP from the container's own ECS metadata document (`ECS_CONTAINER_METADATA_URI_V4`, no path; it lists the container's network, so no list position is involved) with one line of Python (the image has Python and no `curl`);
2. exports `DJANGO_HEALTH_PROBE_HOST=<ip>:8000`;
3. `exec`s the image's own command, `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 30 --error-logfile - --no-control-socket`, so Gunicorn is the main process and receives the stop signal.

The script runs under `set -eu`: if the lookup fails the task stops and the service replaces it, instead of running unhealthy and being killed by the ALB check later.

## Options considered

| Option | Why not |
|---|---|
| Change the image or Django to accept the ALB's probe differently | The backend and image are frozen (AGENTS.md); the probe setting is the existing, reviewed mechanism |
| Allow every private IP in `ALLOWED_HOSTS` | Weakens host validation for the sake of a health check |
| Health check on a different path or port that skips host validation | Needs code the freeze does not allow |
| Network Load Balancer (probes carry no host) | Loses the HTTP health check and the WAF; a different design from variant A |
| **Command override reading the ECS metadata endpoint (chosen)** | No image change; same mechanism as EC2, with the IP from a different source |

## Driver

Keep one image and one probe mechanism for both variants. The difference that remains is where the IP comes from, which is a real, documentable operational difference between the platforms.

## Consequences

- **Duplicated command.** The gunicorn line repeats the Dockerfile's `CMD`. If the Dockerfile changes it and `fargate/ecs.tf` does not, the two variants would run different server settings without anyone deciding so. Mitigation: `scripts/tf.sh fargate plan` compares the two lines and stops if they differ, and `jobs.sh` runs other commands through their own overrides, unaffected.
- **Metadata endpoint shape.** The path (`Networks[0].IPv4Addresses[0]`) was tested only against a sample document; the first real task is the proof.
- One-off jobs on Fargate override the command with the job's own, so they do not need the probe host.

## Evidence that will back it

The first task's log lines, the target group showing the task healthy, and `smoke.sh` passing through the ALB.

## Revisit when

The Dockerfile's command changes, or the image gains an entry point that can read the IP itself.
