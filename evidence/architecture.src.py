"""Source of evidence/architecture.png (42Factors, INF2006 group 21). Final architecture = variant B (ECS on Fargate).

Render:  python3 evidence/architecture.src.py     (needs Pillow and Liberation Sans; writes evidence/architecture.png)

Every label comes from src/infrastructure/ (resource names), project_manifest.yaml (architecture.components) or the
evidence files named in evidence/architecture.md. No account IDs, IP addresses or secret values appear here.
The layout is hand-placed (fixed coordinates, orthogonal arrows) so the picture stays readable at A4 width.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 3600, 2730
OUT = Path(__file__).with_name("architecture.png")
FD = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-"


def font(style, size):
    return ImageFont.truetype(FD + style + ".ttf", size)


F_TITLE, F_SUB = font("Bold", 58), font("Regular", 30)
F_ZONE, F_ZSUB = font("Bold", 34), font("Regular", 27)
F_B, F_N, F_I = font("Bold", 33), font("Regular", 28), font("Italic", 28)
F_E, F_EB = font("Regular", 27), font("Bold", 27)

BLUE, GREEN, ORANGE, PURPLE, DARK, GREY = "#1f5fbf", "#1a8a3a", "#d9730d", "#7b3fa0", "#222222", "#777777"
Z1, Z2, Z3, Z4 = "#c0392b", "#d69e2e", "#2f855a", "#2b6cb0"

img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


# ------------------------------------------------------------------ drawing helpers
def zone(x0, y0, x1, y1, color, fill, title, sub=None, tcolor=None, sub_at_bottom=False):
    d.rounded_rectangle((x0, y0, x1, y1), 28, fill=fill, outline=color, width=8)
    d.text((x0 + 24, y0 + 14), title, font=F_ZONE, fill=tcolor or color)
    if sub:
        sy = y1 - 44 if sub_at_bottom else y0 + 56
        d.text((x0 + 24, sy), sub, font=F_ZSUB, fill="#444444")


LH = {"b": 44, "n": 37, "i": 37}
FONTS = {"b": F_B, "n": F_N, "i": F_I}


def box(x, y, w, lines, fill="white", outline="#444444", width=3, dashed=False):
    """lines: (style, text) with style b (bold title), n (normal), i (italic). Returns the rectangle."""
    rect = (x, y, x + w, y + sum(LH[s] for s, _ in lines) + 30)
    if dashed:
        d.rounded_rectangle(rect, 18, fill=fill)
        x0, y0, x1, y1 = rect
        for a in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            seg(*a, outline, width, 22, 14)
    else:
        d.rounded_rectangle(rect, 18, fill=fill, outline=outline, width=width)
    cy = y + 15
    for s, t in lines:
        d.text((x + 20, cy), t, font=FONTS[s], fill="#444444" if s == "i" else "#1a1a1a")
        cy += LH[s]
    return rect


def seg(ax, ay, bx, by, color, width, dash=0, gap=0):
    if not dash:
        d.line((ax, ay, bx, by), fill=color, width=width)
        return
    length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
    for i in range(int(length // (dash + gap)) + 1):
        s, e = i * (dash + gap) / length, min(1.0, (i * (dash + gap) + dash) / length)
        if s < 1:
            d.line((ax + (bx - ax) * s, ay + (by - ay) * s, ax + (bx - ax) * e, ay + (by - ay) * e), fill=color, width=width)


def tip(p, q, color, width, head):
    (ax, ay), (bx, by) = p, q
    L, Wd = 24 + width * 2, 12 + width * 1.5
    if ax == bx:
        sg = 1 if by > ay else -1
        poly = [(bx, by), (bx - Wd, by - sg * L), (bx + Wd, by - sg * L)]
    else:
        sg = 1 if bx > ax else -1
        poly = [(bx, by), (bx - sg * L, by - Wd), (bx - sg * L, by + Wd)]
    if head == "hollow":
        d.polygon(poly, fill="white")
        d.line(poly + [poly[0]], fill=color, width=4)
    elif head != "none":
        d.polygon(poly, fill=color)


def arrow(pts, color, width=5, dashed=False, head="solid"):
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg(ax, ay, bx, by, color, width, 20 if dashed else 0, 12 if dashed else 0)
    tip(pts[-2], pts[-1], color, width, head)


def label(x, y, text, color="#222222", bold=False, center=False):
    f = F_EB if bold else F_E
    rows = text.split("\n")
    wmax = max(d.textlength(t, font=f) for t in rows)
    if center:
        x -= wmax / 2
    d.rectangle((x - 6, y - 2, x + wmax + 6, y + 34 * len(rows) + 1), fill="white")
    for i, t in enumerate(rows):
        d.text((x, y + 34 * i), t, font=f, fill=color)


# anchors on a rect
def top(r, x):
    return (x, r[1])


def bot(r, x):
    return (x, r[3])


def left(r, y):
    return (r[0], y)


def right(r, y):
    return (r[2], y)


# ------------------------------------------------------------------ title
d.text((40, 22), "42Factors shop on AWS: final architecture (variant B, ECS on Fargate)", font=F_TITLE, fill="#111111")
d.text((40, 98), "INF2006 group 21 · region us-east-1 · every AWS resource is created by terraform apply from src/infrastructure/ "
       "(base/, fargate/, modules/web-entry/)", font=F_SUB, fill="#333333")
d.text((40, 140), "Variant A (EC2 + Auto Scaling) is the evaluated alternative and is drawn dashed. Labels are Terraform resource "
       "names; evidence/architecture.md maps every label to its test evidence.", font=F_SUB, fill="#333333")

# ------------------------------------------------------------------ zones
zone(40, 200, 580, 2460, Z1, "#fdf3f2", "TRUST BOUNDARY 1", "Internet (untrusted) and the team laptop")
d.rounded_rectangle((620, 200, 3560, 2460), 30, outline="#888888", width=4)
d.text((650, 214), "AWS Cloud · us-east-1 · Learner Lab account · one VPC (aws_vpc.main) · every role is LabRole",
       font=F_ZONE, fill="#333333")
zone(660, 260, 3520, 570, Z4, "#f3f8fd", "TRUST BOUNDARY 4 · AWS-managed services (edge and scaling)")
zone(660, 610, 2560, 1670, Z2, "#fffaf0", "TRUST BOUNDARY 2", "Public subnets, 2 AZs", "#8a5a00")
d.text((1400, 622), "aws_subnet.public (a, b)", font=F_ZSUB, fill="#444444")
d.text((1400, 656), "route 0.0.0.0/0 to aws_internet_gateway.main, no NAT gateway", font=F_ZSUB, fill="#444444")
zone(2600, 610, 3520, 1670, Z3, "#f1f9f4", "TRUST BOUNDARY 3", "aws_subnet.private (a, b) · no route to the internet",
     "#22543d", sub_at_bottom=True)
d.text((2624, 654), "Private data subnets, 2 AZs", font=F_ZSUB, fill="#22543d")
zone(660, 1810, 3520, 2430, Z4, "#f3f8fd", "TRUST BOUNDARY 4", "AWS-managed services")
d.text((684, 2386), "Reached over HTTPS 443 on public endpoints (sg-app egress 443); no NAT gateway", font=F_ZSUB, fill="#444444")

# ------------------------------------------------------------------ zone 1
browser = box(80, 300, 460, [("b", "Browser"), ("n", "customer and operator"), ("i", "manifest component 1")],
              "#fdecea", Z1)
laptop = box(80, 1420, 460, [("b", "Team laptop (deploy-time)"), ("n", "terraform: scripts/tf.sh, up.sh"),
                             ("n", "scripts/push-image.sh"), ("n", "scripts/jobs.sh, evidence.sh")], "#f2f2f2", "#555555")
analytics = box(80, 1880, 460, [("b", "Offline analytics and ML"), ("n", "analytics/ (pandas, scikit-learn)"),
                                ("n", "runs locally, outside the image"), ("n", "build_shoe_dataset.py"),
                                ("n", "verify_refresh.py"), ("n", "segment_customers.py (not run"), ("n", "on AWS: DATA-02)"),
                                ("i", "manifest component 12")], "#f2f2f2", "#555555")
mailbox = box(80, 2290, 460, [("b", "Operator mailbox"), ("n", "alarm email (ALARM and OK)")], "#fdecea", Z1)

# ------------------------------------------------------------------ top band (zone 4: edge and scaling)
route53 = box(690, 330, 480, [("b", "Route 53"), ("n", "aws_route53_zone.main"), ("n", "aws_route53_record.app (alias)"),
                              ("n", "shop-fargate.fourtytwofactors.me")])
acm = box(1210, 330, 470, [("b", "ACM certificate"), ("n", "aws_acm_certificate.shop"), ("n", "for the 443 listener, DNS-validated")])
waf = box(1720, 330, 700, [("b", "WAF web ACL"), ("n", "aws_wafv2_web_acl.app, attached to the ALB"),
                           ("n", "rule login-rate-limit: POST /login/"), ("n", "count by default, block tested (SEC-17)")])
appscale = box(2460, 330, 1020, [("b", "Application Auto Scaling"), ("n", "aws_appautoscaling_target.app + _policy.requests"),
                                 ("n", "ALBRequestCountPerTarget, 300 per target per minute")])

# ------------------------------------------------------------------ zone 2 (public subnets)
alb = box(700, 760, 640, [("b", "Application Load Balancer"), ("n", "aws_lb.app (manifest component 3)"),
                          ("n", "sg-alb: 443 and 80 from the internet"), ("n", "listener 443: TLS 1.2/1.3 policy"),
                          ("n", "listener 80: 301 redirect to 443"), ("n", "aws_lb_target_group.app: ip, 8000,"),
                          ("n", "health check /health/")], "#fff6e0", "#8a5a00")
fargate = box(1620, 760, 760, [("b", "ECS Fargate service and tasks"), ("n", "aws_ecs_cluster.app · aws_ecs_service.app"),
                               ("n", "aws_ecs_task_definition.app, 1 to 2 tasks"), ("n", "2 vCPU / 4 GB, public IP, no sticky sessions"),
                               ("n", "container web: Django 5, Gunicorn, WhiteNoise"),
                               ("n", "sg-app: port 8000 from sg-alb only"), ("i", "manifest components 5 and 6")],
              "#fff6e0", "#8a5a00", width=6)
loadgen = box(700, 1120, 520, [("b", "Load generator"), ("n", "aws_instance.loadgen (c5.large)"),
                               ("n", "benchmarks only, no inbound"), ("n", "tests/load/ · manifest component 13")],
              "#eeeeee", "#777777")
jobs = box(1960, 1120, 440, [("b", "One-off job tasks"), ("n", "aws ecs run-task, same task"),
                             ("n", "definition and sg-app:"), ("n", "bootstrap, migrate, check,"),
                             ("n", "import, operator, refresh")], "#fff6e0", "#8a5a00")
varA = box(700, 1370, 570, [("b", "Variant A: alternative"), ("n", "aws_launch_template.app +"),
                            ("n", "aws_autoscaling_group.app"), ("n", "EC2 c5.large, 1 to 2 instances"),
                            ("n", "own ALB shop-ec2.* (same module)"), ("i", "manifest component 4")],
           "#f6f6f6", "#666666", width=4, dashed=True)

# ------------------------------------------------------------------ zone 3
rds = box(2640, 760, 840, [("b", "Amazon RDS PostgreSQL 17"), ("n", "aws_db_instance.main (component 7)"),
                           ("n", "db.t4g.small, single-AZ, not public"), ("n", "encrypted, TLS forced (rds.force_ssl)"),
                           ("n", "sg-db: 5432 from sg-app only"), ("n", "sessions, carts, orders, dataset,"),
                           ("n", "analytics summaries")], "#e6f4ea", "#22543d", width=6)

# ------------------------------------------------------------------ bottom band: row a and row b
YA, YB = 1915, 2185
ecr = box(700, YA, 530, [("b", "Amazon ECR"), ("n", "aws_ecr_repository.app"), ("n", "image run by digest (aws_ecr_image)"),
                         ("i", "manifest component 8")])
secrets = box(1330, YA, 610, [("b", "AWS Secrets Manager (component 9)"), ("n", "aws_secretsmanager_secret.app:"),
                              ("n", "web, migration, trainer, bootstrap,"), ("n", "operator + RDS-managed master secret")])
s3 = box(1980, YA, 600, [("b", "Amazon S3 bucket (private)"), ("n", "data.aws_s3_bucket.main"),
                         ("n", "public access blocked, versioned,"), ("n", "AES256, TLS-only; data/ and exports/")])
logs = box(2620, YA, 860, [("b", "CloudWatch Logs"), ("n", "aws_cloudwatch_log_group.app: /inf2006-grp21-fargate/app"),
                           ("n", "7-day retention, one JSON line per request"),
                           ("n", "aws_cloudwatch_log_group.db (PostgreSQL log)")])
sns = box(700, YB, 530, [("b", "Amazon SNS (component 11)"), ("n", "aws_sns_topic.alarms"),
                         ("n", "+ aws_sns_topic_subscription"), ("n", ".alarm_email")])
alarms = box(1330, YB, 610, [("b", "CloudWatch alarms"), ("n", "aws_cloudwatch_metric_alarm:"),
                             ("n", "unhealthy_hosts, no_healthy_hosts,"), ("n", "target_5xx (WAF metrics also here)")])
insights = box(2620, YB, 860, [("b", "Logs Insights saved queries"), ("n", "aws_cloudwatch_query_definition:"),
                               ("n", "recent_problems, problems_per_minute")])
for i, t in enumerate(("Manifest component 10: security groups", "as trust boundaries (sg-alb, sg-app,",
                       "sg-db), named on the arrows between", "the zones.")):
    d.text((1990, YB + 6 + 37 * i), t, font=F_I, fill="#444444")

# ------------------------------------------------------------------ user traffic (blue)
arrow([right(browser, 400), left(route53, 400)], BLUE, 5)
label(615, 355, "DNS", BLUE, center=True)
arrow([(310, browser[3]), (310, 860), left(alb, 860)], BLUE, 9)
label(335, 790, "HTTPS 443\n(80 redirects)", BLUE, True)
arrow([bot(route53, 1100), top(alb, 1100)], BLUE, 5)
label(1115, 700, "alias", BLUE)
arrow([right(alb, 860), left(fargate, 860)], BLUE, 9)
label(1480, 770, "HTTP 8000\n+ /health/", BLUE, True, center=True)
label(1480, 885, "sg-app: only\nfrom sg-alb", BLUE, False, center=True)
arrow([top(loadgen, 960), bot(alb, 960)], BLUE, 5)
label(980, 1050, "HTTPS 443 (benchmark)", BLUE)
# configuration attachments (grey, no head)
arrow([bot(acm, 1240), (1240, 760)], GREY, 4, head="none")
arrow([bot(waf, 1800), (1800, 590), (1310, 590), top(alb, 1310)], GREY, 4, head="none")

# ------------------------------------------------------------------ data (green)
arrow([right(fargate, 860), left(rds, 860)], GREEN, 9)
label(2510, 770, "PostgreSQL 5432\nTLS verify-full", GREEN, True, center=True)
label(2510, 885, "sg-db: from\nsg-app only", GREEN, False, center=True)
arrow([right(jobs, 1200), (2900, 1200), bot(rds, 2900)], GREEN, 5)
label(2510, 1215, "5432: migrate,\nimport, refresh", GREEN)
arrow([right(varA, 1480), (3200, 1480), bot(rds, 3200)], GREY, 5, dashed=True)
label(3215, 1260, "variant A:\n5432 from its\nown sg-app", "#555555")
arrow([top(s3, 2250), bot(jobs, 2250)], GREEN, 5)
label(2265, 1640, "import: dataset\ndownload", GREEN)
arrow([right(analytics, 2130), (2300, 2130), bot(s3, 2300)], GREEN, 5)
label(1960, 2100, "dataset files: aws s3 sync (jobs.sh import)", GREEN)

# ------------------------------------------------------------------ secrets (purple)
arrow([bot(fargate, 1740), (1740, 1760), (1560, 1760), top(secrets, 1560)], PURPLE, 5)
label(1760, 1500, "read at start-up\nwith the task role", PURPLE)
arrow([bot(jobs, 2000), (2000, 1790), (1850, 1790), top(secrets, 1850)], PURPLE, 5)
label(2010, 1580, "job secrets;\noperator written", PURPLE)

# ------------------------------------------------------------------ logs and metrics (orange)
arrow([right(fargate, 990), (2490, 990), (2490, 1730), (3000, 1730), top(logs, 3000)], ORANGE, 5)
label(2505, 1560, "awslogs: JSON\nlog lines", "#b35a00")
arrow([bot(rds, 3400), top(logs, 3400)], ORANGE, 5)
label(3415, 1440, "PostgreSQL\nlog export", "#b35a00")
arrow([bot(logs, 3300), top(insights, 3300)], ORANGE, 5)
label(3315, 2100, "queried by", "#b35a00")
arrow([bot(alb, 1290), (1290, 2155), (1400, 2155), top(alarms, 1400)], ORANGE, 5)
label(1305, 1085, "ELB metrics", "#b35a00")
arrow([left(alarms, 2330), right(sns, 2330)], ORANGE, 5)
label(1240, 2262, "ALARM,\nOK", "#b35a00")
arrow([left(sns, 2330), right(mailbox, 2330)], ORANGE, 5)
label(572, 2290, "email", "#b35a00", center=False)
arrow([bot(appscale, 2500), (2500, 590), (2300, 590), top(fargate, 2300)], ORANGE, 5)
label(2020, 598, "DesiredCount 1 to 2", "#b35a00")

# ------------------------------------------------------------------ deploy-time (dark, hollow head)
arrow([right(laptop, 1600), (600, 1600), (600, 1950), left(ecr, 1950)], DARK, 6, head="hollow")
label(615, 1700, "docker push", DARK, True)
arrow([top(ecr, 1050), (1050, 1730), (1650, 1730), bot(fargate, 1650)], DARK, 6, head="hollow")
label(1305, 1690, "image pull by digest", DARK, True)
arrow([right(laptop, 1490), (640, 1490), (640, 1330), left(jobs, 1330)], DARK, 6, head="hollow")
label(1330, 1288, "aws ecs run-task", DARK, True)

# ------------------------------------------------------------------ legend
zone(40, 2490, 3560, 2700, "#999999", "white", "Legend", None, "#333333")
x = 60
d.text((x, 2545), "Boundaries:", font=F_EB, fill="#222222")
x += 170
for c, f, t in ((Z1, "#fdf3f2", "1 Internet"), (Z2, "#fffaf0", "2 Public subnets"), (Z3, "#f1f9f4", "3 Private data"),
                (Z4, "#f3f8fd", "4 AWS-managed")):
    d.rounded_rectangle((x, 2545, x + 56, 2581), 8, fill=f, outline=c, width=6)
    d.text((x + 68, 2546), t, font=F_E, fill="#222222")
    x += 68 + int(d.textlength(t, font=F_E)) + 36
x += 20
d.text((x, 2545), "Arrows:", font=F_EB, fill="#222222")
x += 110
for col, wd, t, dashed, head in ((BLUE, 8, "user traffic", False, "solid"), (GREEN, 8, "data", False, "solid"),
                                 (ORANGE, 5, "logs and metrics", False, "solid"), (PURPLE, 5, "secrets", False, "solid"),
                                 (DARK, 6, "deploy-time", False, "hollow"), (GREY, 5, "variant A", True, "solid")):
    arrow([(x, 2563), (x + 80, 2563)], col, wd, dashed=dashed, head=head)
    d.text((x + 92, 2546), t, font=F_E, fill="#222222")
    x += 92 + int(d.textlength(t, font=F_E)) + 30
d.text((60, 2610), "Thick arrows are the main request path (browser, ALB, task, RDS). Grey lines without heads attach the "
       "certificate and the web ACL to the ALB.", font=F_E, fill="#444444")
d.text((60, 2646), "Dashed box and dashed arrow: variant A, built and measured, not part of the final flow. Names such as sg-alb, "
       "sg-app and sg-db are the security groups that enforce the boundaries.", font=F_E, fill="#444444")

img.save(OUT, dpi=(300, 300))
print(OUT, img.size)
