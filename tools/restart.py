#!/usr/bin/env python3

"""Rebuild the hermes-proxy image from source and (re)deploy the local
docker-compose stack.

This replaces the former native-binary flow (build a Go binary, auto-start host
PostgreSQL/Redis, run the binary). Instead it:

  1. builds the Docker image `hermes-proxy-local:latest` from the repo, and
  2. brings up the docker-compose stack defined under `deploy/`
     (`docker-compose.local.yml` + `docker-compose.local.override.yml`,
     project name `hermes-proxy`) waiting until containers are healthy.

Usage:
  tools/restart.py                 # build image + (re)deploy + health check
  tools/restart.py --restart-only  # skip build; just (re)create the stack
  tools/restart.py --no-cache      # rebuild image without layer cache
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import NoReturn, Optional


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parent.parent
DEPLOY_DIR = REPO_ROOT / "deploy"
VERSION_FILE = REPO_ROOT / "backend" / "cmd" / "server" / "VERSION"
ENV_FILE = DEPLOY_DIR / ".env"

# Compose files are layered: the base local stack + the local override that
# pins locally-available images (this host can't reach Docker Hub) and maps a
# loopback postgres port. Keep this in sync with the deploy/ directory.
COMPOSE_FILES = ("docker-compose.local.yml", "docker-compose.local.override.yml")
PROJECT_NAME = "hermes-proxy"
IMAGE_TAG = "hermes-proxy-local:latest"
DEFAULT_WAIT_TIMEOUT = 180
HEALTH_PATH = "/health"

DOCKER_EXTRA_PATHS = [
    "/opt/homebrew/bin/docker",
    "/usr/local/bin/docker",
    "/Applications/Docker.app/Contents/Resources/bin/docker",
]


def print_step(message: str) -> None:
    print(f"[deploy] {message}")


def fail(message: str) -> NoReturn:
    print(f"[deploy] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve_docker_bin(override: str = "") -> str:
    candidates = [override, os.environ.get("DOCKER_BIN", ""), shutil.which("docker") or ""]
    candidates.extend(DOCKER_EXTRA_PATHS)
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    fail(
        "cannot find `docker`. Install Docker Desktop, or set `DOCKER_BIN` / "
        f"pass `--docker-bin`. Checked PATH and {', '.join(DOCKER_EXTRA_PATHS)}"
    )


def run_command(
    command: list[str],
    cwd: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    location = f" (cwd={cwd})" if cwd else ""
    print_step(f"run: {' '.join(command)}{location}")
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        fail(f"command failed with exit code {result.returncode}: {' '.join(command)}{location}")
    return result


def read_env_value(env_file: Path, key: str, default: str) -> str:
    if not env_file.exists():
        return default
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip("'\"") or default
    return default


def read_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "docker"


def compose_base_command(docker_bin: str) -> list[str]:
    command = [docker_bin, "compose"]
    for compose_file in COMPOSE_FILES:
        command.extend(["-f", str(DEPLOY_DIR / compose_file)])
    command.extend(["-p", PROJECT_NAME])
    return command


def collect_preflight_issues(docker_bin: str) -> list[str]:
    issues: list[str] = []

    version = subprocess.run(
        [docker_bin, "version", "--format", "{{.Server.Version}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if version.returncode != 0 or not version.stdout.strip():
        issues.append("`docker`: daemon not reachable. Start Docker Desktop first (`docker version` failed)")

    compose = subprocess.run(
        [docker_bin, "compose", "version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if compose.returncode != 0:
        issues.append("`docker compose`: v2 plugin not available (`docker compose version` failed)")

    for compose_file in COMPOSE_FILES:
        path = DEPLOY_DIR / compose_file
        if not path.exists():
            issues.append(f"`{path}`: compose file not found")

    if not ENV_FILE.exists():
        issues.append(
            f"`{ENV_FILE}`: env file not found. Copy `deploy/.env.example` to `deploy/.env` "
            "and set at least POSTGRES_PASSWORD"
        )

    return issues


def ensure_preflight_ready(docker_bin: str) -> None:
    issues = collect_preflight_issues(docker_bin)
    if issues:
        fail("preflight checks failed before deploy:\n  - " + "\n  - ".join(issues))


def build_image(docker_bin: str, no_cache: bool = False) -> None:
    version = read_version()
    commit = git_commit()
    command = [
        docker_bin,
        "build",
        "-t",
        IMAGE_TAG,
        "--build-arg",
        f"VERSION={version}",
        "--build-arg",
        f"COMMIT={commit}",
    ]
    if no_cache:
        command.append("--no-cache")
    command.append(".")

    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"
    print_step(f"building image {IMAGE_TAG} (version={version} commit={commit})")
    run_command(command, cwd=REPO_ROOT, env=env)


def compose_up(docker_bin: str, wait_timeout: int) -> None:
    command = compose_base_command(docker_bin) + [
        "up",
        "-d",
        "--wait",
        "--wait-timeout",
        str(wait_timeout),
    ]
    run_command(command, cwd=DEPLOY_DIR)


def compose_ps(docker_bin: str) -> None:
    run_command(compose_base_command(docker_bin) + ["ps"], cwd=DEPLOY_DIR)


def probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "", "::"} else host


def health_check(host: str, port: str, timeout_seconds: float = 10) -> None:
    url = f"http://{probe_host(host)}:{port}{HEALTH_PATH}"
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 (local URL)
            code = response.getcode()
            body = response.read(200).decode("utf-8", "replace").strip()
    except Exception as exc:  # noqa: BLE001 - surface any failure as a deploy error
        fail(f"health check failed: GET {url} -> {exc}")
    if code != 200:
        fail(f"health check failed: GET {url} -> HTTP {code}")
    print_step(f"health OK: {url} -> {code} {body}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the hermes-proxy image and (re)deploy the local docker-compose stack."
    )
    parser.add_argument(
        "--restart-only",
        action="store_true",
        help="skip the image build; only (re)create/restart the compose stack with the current image",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="build the image without using the Docker layer cache",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=DEFAULT_WAIT_TIMEOUT,
        help=f"seconds to wait for containers to become healthy (default: {DEFAULT_WAIT_TIMEOUT})",
    )
    parser.add_argument("--docker-bin", default="", help="path to the docker executable")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docker_bin = resolve_docker_bin(args.docker_bin)
    ensure_preflight_ready(docker_bin)

    if args.restart_only:
        print_step("restart-only: skipping image build")
    else:
        build_image(docker_bin, no_cache=args.no_cache)

    compose_up(docker_bin, args.wait_timeout)
    compose_ps(docker_bin)

    host = read_env_value(ENV_FILE, "BIND_HOST", "127.0.0.1")
    port = read_env_value(ENV_FILE, "SERVER_PORT", "8080")
    health_check(host, port)
    print_step(f"done: project={PROJECT_NAME} image={IMAGE_TAG} url=http://{probe_host(host)}:{port}")


if __name__ == "__main__":
    main()
