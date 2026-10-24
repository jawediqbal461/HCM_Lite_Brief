#!/usr/bin/env bash
# HCM Lite — one-shot server setup.
#
#   DOMAIN=hcm.example.com bash setup.sh
#
# Safe to re-run: an existing .env is kept (so secrets survive), and nginx is
# only reloaded when its config tests clean — other sites on this box stay up.
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/HCM_Lite_Brief}
REPO=${REPO:-https://github.com/jawediqbal461/HCM_Lite_Brief.git}
DOMAIN=${DOMAIN:-}
HTTP_PORT=${HTTP_PORT:-8080}
TLS_PORT=${TLS_PORT:-8443}

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this as root." >&2
  exit 1
fi
if [ -z "$DOMAIN" ]; then
  echo "Usage: DOMAIN=hcm.example.com bash setup.sh" >&2
  exit 1
fi

echo "==> Docker"
if command -v docker >/dev/null 2>&1; then
  echo "    already installed: $(docker --version)"
else
  curl -fsSL https://get.docker.com | sh
fi

echo "==> Code"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

echo "==> Configuration"
if [ -f .env ]; then
  echo "    .env already exists — keeping it (delete it to regenerate)"
else
  cat > .env <<EOF
SITE_ADDRESS=:80
HTTP_BIND=127.0.0.1:${HTTP_PORT}
HTTPS_BIND=127.0.0.1:${TLS_PORT}
PUBLIC_URL=https://${DOMAIN}
POSTGRES_USER=hcm
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 32)
POSTGRES_DB=hcm_lite
JWT_SECRET=$(openssl rand -base64 64 | tr -dc 'A-Za-z0-9' | head -c 64)
AI_PROVIDER=anthropic
AI_API_KEY=
AI_MODEL=claude-sonnet-4-5
EOF
  chmod 600 .env
  echo "    wrote .env with freshly generated secrets"
fi

echo "==> Building and starting containers"
docker compose up -d --build

echo "==> Waiting for the app to answer on 127.0.0.1:${HTTP_PORT}"
ready=""
for _ in $(seq 1 45); do
  if curl -fsS -o /dev/null "http://127.0.0.1:${HTTP_PORT}/"; then
    ready=yes
    break
  fi
  sleep 2
done
if [ -z "$ready" ]; then
  echo "    !! app did not come up. Check: docker compose logs --tail=50" >&2
  exit 1
fi
echo "    app is responding"

echo "==> nginx"
if ! command -v nginx >/dev/null 2>&1; then
  echo "    nginx not installed — nothing to proxy through."
  echo "    The app is on 127.0.0.1:${HTTP_PORT}; put any reverse proxy in front of it."
else
  CONF=/etc/nginx/conf.d/hcm.conf
  if [ -f "$CONF" ]; then
    echo "    $CONF already exists — leaving it untouched"
  else
    cat > "$CONF" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${HTTP_PORT};
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # CSV employee imports
        client_max_body_size 10m;
    }
}
EOF
    # Never reload on a bad config: that would take down every other site here.
    if nginx -t; then
      systemctl reload nginx
      echo "    vhost added, nginx reloaded"
    else
      rm -f "$CONF"
      echo "    !! nginx config test failed — vhost removed, nginx left untouched" >&2
      exit 1
    fi
  fi
fi

cat <<EOF

Done.

  App:   http://127.0.0.1:${HTTP_PORT}  (behind nginx as ${DOMAIN})
  Logs:  docker compose -f ${APP_DIR}/docker-compose.yml logs -f

Next:
  1. certbot --nginx -d ${DOMAIN}
  2. Open https://${DOMAIN} — you should land on first-run setup
  3. In Company setup, set the timezone before anyone checks in
  4. For the AI assistant, put your key in ${APP_DIR}/.env and run:
       docker compose -f ${APP_DIR}/docker-compose.yml up -d
EOF
