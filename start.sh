#!/usr/bin/env bash
# Start the local Kubernetes demo. Run with Git Bash: bash start.sh
set -euo pipefail
cd "$(dirname "$0")"

for command in docker kind kubectl; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing $command. Install Docker Desktop, kind and kubectl first." >&2
    exit 1
  fi
done
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running or is inaccessible. Start Docker Desktop and retry." >&2
  exit 1
fi

if [ -z "${REPO_URL:-}" ]; then
  read -r -p 'GitHub repository URL (public repository with this project on main): ' REPO_URL
fi
if [ -z "$REPO_URL" ]; then
  echo 'A repository URL is required for Jenkins to build the application.' >&2
  exit 1
fi
export REPO_URL

if docker container inspect jenkins >/dev/null 2>&1; then
  echo 'A container named jenkins already exists. Remove or rename it before starting this demo.' >&2
  echo 'It was left untouched to protect its configuration.' >&2
  exit 1
fi

if kind get clusters | grep -Fxq canary-demo; then
  echo 'The canary-demo cluster already exists. Check its setup before continuing; it was left untouched.' >&2
  exit 1
else
  bash ./demo.sh up
fi
bash ./demo.sh jenkins
echo 'Open http://localhost:8080, sign in as admin (password: JENKINS_ADMIN_PASSWORD, or admin by default), and click Build Now on canary-release.'
echo 'After the first build, open http://localhost:8000. Grafana: http://localhost:3000.'
