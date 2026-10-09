#!/usr/bin/env python3
"""Build Group_<id>_INF2006_Project.zip from a commit, then check it the way Appendix A of the brief asks.

  python scripts/package_submission.py --group G021                  # package HEAD, write ../Group_G021_INF2006_Project.zip
  python scripts/package_submission.py --group G021 --add report.pdf --add architecture.png:evidence/architecture.png
  python scripts/package_submission.py --check-only Group_G021_INF2006_Project.zip

Only files committed at the chosen ref go in (git archive semantics), so state files, tfvars and .env files that git
ignores can never be packaged. Files that are not in git yet (the report PDF, the diagram) are added with --add
SRC[:PATH-IN-ZIP]. AGENTS.md and CLAUDE.md are left out by default (instructions for coding agents, not part of the
deliverable); change EXCLUDE below if you disagree.

Exit status 1 when a check FAILS; WARN lines need a human look. Standard library only; no network, no AWS.
"""
import argparse
import io
import posixpath
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

EXCLUDE = {"docs/EVIDENCE_WRITER.md"}   # AGENTS.md and CLAUDE.md are kept: the README links to them and the AI-use declaration refers to them
REQUIRED = ["README.md", "project_manifest.yaml", "report.pdf", "src", "data/DATA_DICTIONARY.md", "analytics/README.md",
            "evidence", "tests", "TEAM_CONTRIBUTIONS.md", "AI_USE_DECLARATION.md", "video_link.txt",
            "evidence/architecture.png", "evidence/test-functional.md", "evidence/test-security.md",
            "evidence/test-data-ai.md", "evidence/test-resilience.md", "evidence/monitoring.md",
            "evidence/threat-control-map.md", "data/README.md"]
TEXT = {".md", ".yaml", ".yml", ".txt", ".py", ".sh", ".tf", ".json", ".csv", ".toml", ".cfg", ".ini", ".html", ".example"}
PATH_IN_TEXT = re.compile(r"(?<![\w./-])((?:evidence|data|analytics|src|tests|docs)/[A-Za-z0-9_./-]*[A-Za-z0-9_])")
LINK = re.compile(r"\]\((?!https?:|mailto:|#)([^)#\s]+)")
SECRET_RULES = [
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY")),
    ("12-digit account id", re.compile(r"(?<![\w.\-])\d{12}(?![\w\-])")),
    ("email address", re.compile(r"[\w.+-]+@(?!example\.|amazonaws\.com|sns\.)[\w-]+\.[a-z]{2,}", re.I)),
]
EMAIL_OK = ("noreply", "no-reply", "<EMAIL>")


def git(*args, binary=False):
    out = subprocess.run(["git", *args], check=True, capture_output=True)
    return out.stdout if binary else out.stdout.decode()


def build(ref, dest, adds):
    tar = tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", ref, binary=True)))
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for m in tar.getmembers():
            if m.isfile() and m.name not in EXCLUDE:
                z.writestr(m.name, tar.extractfile(m).read())
        for spec in adds:
            src, _, arc = spec.partition(":")
            z.write(src, arc or Path(src).name)
    return git("rev-parse", ref).strip()


def check(zpath, group, commit):
    z = zipfile.ZipFile(zpath)
    names = set(z.namelist())
    results = []

    def say(level, msg):
        results.append((level, msg))

    expected = f"Group_{group}_INF2006_Project.zip"
    say("PASS" if Path(zpath).name == expected else "FAIL", f"file name is {Path(zpath).name} (expected {expected})")
    for r in REQUIRED:
        ok = r in names or any(n.startswith(r + "/") for n in names)
        say("PASS" if ok else "FAIL", f"present: {r}")
    manifest = z.read("project_manifest.yaml").decode() if "project_manifest.yaml" in names else ""
    gid = re.search(r'group_id:\s*"([^"]*)"', manifest)
    say("PASS" if gid and gid.group(1) == group else "FAIL", f"manifest group_id {gid.group(1) if gid else '?'} equals {group}")
    rc = re.search(r'repository_commit:\s*"([^"]*)"', manifest)
    if not rc or not rc.group(1):
        say("WARN", "manifest repository_commit is empty")
    elif commit and not commit.startswith(rc.group(1)[:7]):
        say("WARN", f"manifest repository_commit {rc.group(1)[:12]} is not the packaged commit {commit[:12]}")
    missing = sorted({p.rstrip(".") for p in PATH_IN_TEXT.findall(manifest)
                      if "<" not in p and "*" not in p and not p.endswith("/.env") and p not in names and not any(n.startswith(p + "/") for n in names)})
    say("PASS" if not missing else "FAIL", "every path named in the manifest exists" + (f": missing {missing[:8]}" if missing else ""))
    bad_names = [n for n in names if re.search(r"(\.tfstate|\.tfvars$|\.tfplan|(^|/)\.env$|\.pem$)", n)
                 and not n.endswith("rds-global-bundle.pem")]
    say("PASS" if not bad_names else "FAIL", "no state, tfvars, .env or key files" + (f": {bad_names[:5]}" if bad_names else ""))
    hits, todo, broken = [], [], []
    for n in sorted(names):
        if Path(n).suffix.lower() not in TEXT or n.endswith("/"):
            continue
        text = z.read(n).decode("utf-8", "replace")
        for label, rx in SECRET_RULES:
            for m in rx.finditer(text):
                if label == "email address" and any(ok in m.group(0) for ok in EMAIL_OK):
                    continue
                hits.append(f"{n}: {label} ({m.group(0).strip()[:40]})")
                break
        if n in ("README.md", "project_manifest.yaml", "TEAM_CONTRIBUTIONS.md", "AI_USE_DECLARATION.md", "video_link.txt") and re.search(r"\bTODO\b", text):
            todo.append(n)
        if n.endswith(".md"):
            for target in LINK.findall(text):
                p = posixpath.normpath(posixpath.join(posixpath.dirname(n), target.split("?")[0]))
                if p not in names and not any(k.startswith(p.rstrip("/") + "/") for k in names):
                    broken.append(f"{n} -> {target}")
    say("PASS" if not hits else "WARN", f"leak scan ({len(hits)} possible hits; check each)" + ("" if not hits else ": " + "; ".join(hits[:10])))
    say("PASS" if not todo else "FAIL", "no TODO in the required top-level files" + (f": {todo}" if todo else ""))
    say("PASS" if not broken else "WARN", f"relative markdown links resolve ({len(broken)} broken)" + ("" if not broken else ": " + "; ".join(broken[:8])))
    mb = Path(zpath).stat().st_size / 1e6
    say("PASS" if mb < 100 else "WARN", f"size {mb:.1f} MB")
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", help="group id as in the file name, e.g. G021")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--out")
    ap.add_argument("--add", action="append", default=[], help="SRC[:PATH-IN-ZIP] for a file that is not committed")
    ap.add_argument("--check-only", metavar="ZIP")
    a = ap.parse_args()
    if a.check_only:
        zpath, commit = a.check_only, ""
        group = a.group or (re.search(r"Group_(\w+)_INF2006", Path(zpath).name) or [None, ""])[1]
    else:
        if not a.group:
            sys.exit("--group is required (for example G021)")
        group = a.group
        zpath = a.out or f"../Group_{group}_INF2006_Project.zip"
        commit = build(a.ref, zpath, a.add)
        print(f"Wrote {zpath} from commit {commit[:12]}")
    results = check(zpath, group, commit)
    for level, msg in results:
        print(f"{level:4}  {msg}")
    fails = sum(level == "FAIL" for level, _ in results)
    print(f"\n{fails} FAIL, {sum(level == 'WARN' for level, _ in results)} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
