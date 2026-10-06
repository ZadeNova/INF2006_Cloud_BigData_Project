# ADR-017: Matched settings between the variants, the reduced Fargate jobs, and the script front door

**Status:** drafted by the writing session for review (6 October 2026).

## Decision

**1. Matched settings.** Both stacks use the same module for the entry layer (ADR-014), the same image digest, the same RDS, the same Gunicorn settings, 2 vCPU / 4 GB of compute, and the same scaling signal: `ALBRequestCountPerTarget` with target **300** (`scale_target_requests`), minimum 1, maximum 2. Where the platforms differ, the pairing is recorded here and measured, not hidden:

| Setting | A: EC2 + Auto Scaling | B: ECS on Fargate | Note |
|---|---|---|---|
| Boot allowance | `estimated_instance_warmup` 240 s, grace 300 s | grace 120 s | Reflects the measured or expected time to healthy; both are revised from the first runs |
| Scale-out spacing | warm-up above | `scale_out_cooldown` 300 s | With a maximum of 2 there is one scale-out step, so this barely matters |
| Scale-in | service default | `scale_in_cooldown` 300 s | Both also wait for the policy's built-in sustained-low-load window |
| Capacity pinning | `min_capacity`, `max_capacity`, `desired_capacity` | the same variable names | An apply resets the count on both (ADR-013) |

**2. `jobs.sh fargate` offers four jobs:** `check`, `migrate`, `refresh` and `bootstrap`, each a one-off task started with `aws ecs run-task` (command override and `AWS_SECRET_ID` override), then waits for it to stop, prints its logs and fails on a non-zero exit code. `trainer-sql`, `import` and `operator` need `psql`, the AWS CLI or a data folder that the frozen image lacks, so they are **not offered on Fargate** and the script says to run them on variant A. `restart` has no Fargate meaning.

**3. Script front door** (written in the next step): `status.sh`, `up.sh base|ec2|fargate|loadgen`, `down.sh ec2|fargate|loadgen`, `smoke.sh`; `tf.sh`, `secrets.sh`, `jobs.sh` and `push-image.sh` stay internal helpers. `migrate-state.sh` and the stale probe script are deleted. State stays local, one folder per stack.

## Options considered

| Option | Why not |
|---|---|
| All jobs on Fargate | Needs a second image with extra tools or code in the frozen image; most of the cost is for one-time setup of a shared database that variant A already does |
| Different scaling targets, tuned per platform | Then a difference in scale-out time could come from the target, not the platform |
| One generic `scripts/aws.sh` with many sub-commands | Harder to read than one verb per intention |
| Remote state (S3) | Each person's lab is a separate account, so each laptop owns its account's state; a shared backend only adds a bootstrap problem |
| **Matched settings, four jobs, small front door (chosen)** | Fair comparison, honest scope, easy for a newcomer |

## Driver

The comparison is only meaningful if the platform is the only change; the one-time database setup is not part of what is compared; and the project's reproducibility marks depend on a short, obvious path from nothing to a running stack.

## Consequences

- A brand-new database is seeded through variant A once; reproduction order is `base`, then `ec2`, then `fargate`. The report states this limit.
- Cooldown and grace values are starting points that the load runs may change; every change is recorded with the run it applies to.
- Fargate's ability to scale to 2 tasks depends on a vCPU quota the lab does not show; the first scale-out is the real test.

## Evidence that will back it

The two stacks' plans (module portions equal), `jobs.sh fargate check` and `migrate` passing as a one-off task, the run-time numbers in the load runs, and a newcomer following only the README quick start.

## Revisit when

A run shows a scaling setting favouring one platform, or a teammate cannot follow the quick start without help.
