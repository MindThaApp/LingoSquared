#!/usr/bin/env bash
# bootstrap_wsl.sh -- one-shot, idempotent dev-environment setup for WSL2 Ubuntu 24.04
# (also works on plain Ubuntu/Debian). Safe to re-run; never overwrites backend/.env.
#
# usage: scripts/bootstrap_wsl.sh [--with-e2e] [--with-stack | --no-stack]
#   --with-e2e    also install e2e/ deps + Playwright chromium (default: off)
#   --with-stack  force docker compose up + alembic upgrade (default: on only if docker works)
#   --no-stack    never touch docker
# env: BOOTSTRAP_ALLOW_NON_WSL=1 skips the WSL check (for container validation)
set -euo pipefail

WITH_E2E=0
WITH_STACK=auto
for arg in "$@"; do
  case "$arg" in
    --with-e2e) WITH_E2E=1 ;;
    --with-stack) WITH_STACK=1 ;;
    --no-stack) WITH_STACK=0 ;;
    -h|--help) grep '^#' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$*"; }
info() { printf '    %s\n' "$*"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

# ---------------------------------------------------------------------------
step "1/9 Checking environment"
if [ "$(uname -s)" != "Linux" ]; then
  echo "!! This script is for Linux/WSL2 only (found $(uname -s))." >&2; exit 1
fi
if [ -z "${BOOTSTRAP_ALLOW_NON_WSL:-}" ] && ! grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  echo "!! Not running under WSL (set BOOTSTRAP_ALLOW_NON_WSL=1 to override)." >&2; exit 1
fi
case "$REPO_ROOT" in
  /mnt/*)
    cat >&2 <<MSG
!! The repo is under $REPO_ROOT (the Windows filesystem via /mnt/).
   File watching, permissions, symlinks and speed are all broken there.
   Clone into the WSL filesystem instead:
     git clone <url> ~/<any-dir>/LingoSquared
MSG
    exit 1 ;;
esac
info "repo: $REPO_ROOT"

# ---------------------------------------------------------------------------
step "2/9 Git line-ending config"
if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$REPO_ROOT" config core.autocrlf input
  info "core.autocrlf=input"
else
  info "not a git checkout -- skipped"
fi

# ---------------------------------------------------------------------------
step "3/9 System packages (apt)"
PKGS=(python3-venv python3-pip jq rsync curl build-essential ca-certificates git openssl)
MISSING=()
for p in "${PKGS[@]}"; do
  dpkg -s "$p" >/dev/null 2>&1 || MISSING+=("$p")
done
if [ "${#MISSING[@]}" -eq 0 ]; then
  info "all present"
else
  info "installing: ${MISSING[*]}"
  $SUDO apt-get update -y
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y "${MISSING[@]}"
fi

# ---------------------------------------------------------------------------
step "4/9 Node (>= 22 via nvm, version from .nvmrc)"
node_major() { command -v node >/dev/null 2>&1 && node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0; }
if [ "$(node_major)" -lt 22 ]; then
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    info "installing nvm"
    touch "$HOME/.bashrc"   # nvm's installer appends its init lines here
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  fi
  # nvm.sh is not nounset/errexit-safe
  set +eu
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  nvm install || { echo "!! nvm install failed" >&2; exit 1; }   # reads .nvmrc
  nvm alias default "$(cat .nvmrc)" >/dev/null
  set -eu
  if ! grep -q 'NVM_DIR' "$HOME/.bashrc" 2>/dev/null; then
    {
      echo ''
      echo '# nvm (added by LingoSquared bootstrap_wsl.sh)'
      echo 'export NVM_DIR="$HOME/.nvm"'
      echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"'
    } >> "$HOME/.bashrc"
    info "added nvm init to ~/.bashrc (open a new shell to pick it up)"
  fi
fi
info "node $(node -v), npm $(npm -v)"

# ---------------------------------------------------------------------------
step "5/9 Content venv (.content-venv)"
if [ ! -x .content-venv/bin/python ]; then
  python3 -m venv .content-venv
fi
.content-venv/bin/pip install -q --upgrade pip
.content-venv/bin/pip install -q -r scripts/requirements-content.txt
info "$(.content-venv/bin/python --version); PyYAML + pytest installed"

# ---------------------------------------------------------------------------
step "6/9 npm dependencies"
npm ci
if [ "$WITH_E2E" = "1" ]; then
  info "e2e: npm ci + playwright chromium"
  ( cd e2e && npm ci && npx playwright install --with-deps chromium )
else
  info "e2e skipped (re-run with --with-e2e)"
fi

# ---------------------------------------------------------------------------
step "7/9 Docker"
DOCKER_OK=0
if docker compose version >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  DOCKER_OK=1
  info "$(docker compose version)"
else
  cat <<'MSG'
    Docker (with the compose plugin) is not usable from this shell. Fix ONE of:
      A) Docker Desktop on Windows: Settings -> Resources -> WSL integration ->
         enable "Ubuntu-24.04", Apply & Restart; then open a new WSL shell.
      B) docker-ce inside WSL: follow https://docs.docker.com/engine/install/ubuntu/
         (install docker-ce docker-ce-cli containerd.io docker-compose-plugin),
         then: sudo usermod -aG docker "$USER" && sudo service docker start
         and open a new shell.
    Then re-run this script.
MSG
fi

# ---------------------------------------------------------------------------
step "8/9 Env files"
rand_hex() { openssl rand -hex "$1"; }
if [ -e backend/.env ]; then
  info "backend/.env exists -- left untouched"
else
  [ -f backend/.env.example ] || { echo "!! backend/.env.example missing" >&2; exit 1; }
  JWT="$(rand_hex 32)"
  PGPW="$(rand_hex 16)"
  cp backend/.env.example backend/.env
  # '|' delimiter; values are hex so no escaping needed
  sed -i \
    -e "s|^JWT_SECRET=.*|JWT_SECRET=${JWT}|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${PGPW}|" \
    -e "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg://lingosquared:${PGPW}@db:5432/lingosquared|" \
    -e "s|^API_PORT=.*|API_PORT=8020|" \
    -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://localhost:5173,http://localhost:5175,http://localhost:5180|" \
    backend/.env
  chmod 600 backend/.env
  info "created backend/.env (random JWT_SECRET + POSTGRES_PASSWORD, mode 600)"
  info "TTS/Azure/social-login keys are empty -- copy them by hand if needed (docs/WSL_SETUP.md)"
fi
if [ -e frontend/.env ]; then
  info "frontend/.env exists -- left untouched"
else
  echo "VITE_API_BASE_URL=http://localhost:8020" > frontend/.env
  info "created frontend/.env"
fi

# ---------------------------------------------------------------------------
step "9/9 Local stack (docker compose + migrations)"
if [ "$WITH_STACK" = "auto" ]; then WITH_STACK="$DOCKER_OK"; fi
if [ "$WITH_STACK" = "1" ] && [ "$DOCKER_OK" = "1" ]; then
  ( cd backend && docker compose up -d && docker compose run --rm api alembic upgrade head )
  info "stack up, migrations applied"
elif [ "$WITH_STACK" = "1" ]; then
  echo "!! --with-stack requested but Docker is not usable (see step 7)" >&2; exit 1
else
  info "skipped"
fi

cat <<MSG

==> Done. Next steps
    1. Open a NEW shell (or: source ~/.bashrc) so node is on PATH.
    2. Copy secrets by hand (see docs/WSL_SETUP.md): backend/.env keys, ~/.lingo_admin_pw, ~/.ssh.
    3. Sync content into the dev DB:   scripts/sync_dev_db.sh   (~25 min)
    4. Verify everything:              bash scripts/verify.sh   (judge by summary; grep COMPILE FAILED)
    5. Dev server:                     cd frontend && npm run dev -- --port 5180
MSG
