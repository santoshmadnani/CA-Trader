#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/home/ubuntu/ca-trader-final"
BACKUP_DIR="/home/ubuntu/ca-trader-backups"
NETWORK_MAIN="ca-trader_default"
NETWORK_SHARED="ca-trader-shared"
APP_CONTAINER="ca-trader"
CADDY_CONTAINER="ca-trader-caddy"
APP_PORT="8000"

echo "=========================================="
echo "       CA TRADER SAFE DEPLOYMENT"
echo "=========================================="

mkdir -p "$BACKUP_DIR"

# -------------------------------------------------
# 1. Find newest ZIP
# -------------------------------------------------
ZIP="$(find /home/ubuntu -maxdepth 1 -type f -name '*.zip' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -1 \
    | cut -d' ' -f2-)"

if [ -z "${ZIP:-}" ]; then
    echo "ERROR: No ZIP found in /home/ubuntu"
    exit 1
fi

ZIP_NAME="$(basename "$ZIP")"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEPLOY_ID="${STAMP}_$(basename "$ZIP" .zip | tr -cd '[:alnum:]_-')"

echo
echo "ZIP selected:"
echo "  $ZIP"

# -------------------------------------------------
# 2. Validate ZIP
# -------------------------------------------------
echo
echo "Checking ZIP..."
unzip -t "$ZIP" >/dev/null

# Check required files
for f in Dockerfile app.py requirements.txt terminal.html CA_Trader_Login.html; do
    if ! unzip -l "$ZIP" | grep -qE "[[:space:]]${f}$"; then
        echo "ERROR: ZIP is missing required file: $f"
        exit 1
    fi
done

echo "ZIP OK."

# -------------------------------------------------
# 3. Verify Docker networks
# -------------------------------------------------
echo
echo "Checking Docker networks..."

for net in "$NETWORK_MAIN" "$NETWORK_SHARED"; do
    if ! sudo docker network inspect "$net" >/dev/null 2>&1; then
        echo "ERROR: Required network does not exist: $net"
        exit 1
    fi
done

# -------------------------------------------------
# 4. Capture exact currently-live image
# -------------------------------------------------
OLD_IMAGE_ID=""

if sudo docker inspect "$APP_CONTAINER" >/dev/null 2>&1; then
    OLD_IMAGE_ID="$(sudo docker inspect "$APP_CONTAINER" --format '{{.Image}}')"
fi

echo
echo "Current image:"
echo "  ${OLD_IMAGE_ID:-NONE}"

# -------------------------------------------------
# 5. Backup current source
# -------------------------------------------------
BACKUP="$BACKUP_DIR/$DEPLOY_ID"

echo
echo "Creating backup:"
echo "  $BACKUP"

mkdir -p "$BACKUP"

if [ -d "$APP_DIR" ]; then
    cp -a "$APP_DIR" "$BACKUP/source"
fi

if [ -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env" "$BACKUP/.env"
fi

# -------------------------------------------------
# 6. Create temporary build directory
# -------------------------------------------------
BUILD_DIR="/home/ubuntu/.ca-trader-build-$DEPLOY_ID"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo
echo "Extracting new version..."

unzip -q "$ZIP" -d "$BUILD_DIR"

# Handle ZIP with a single top-level directory
if [ ! -f "$BUILD_DIR/Dockerfile" ]; then
    ROOT="$(find "$BUILD_DIR" -maxdepth 3 -type f -name Dockerfile -print -quit | xargs -r dirname)"

    if [ -n "${ROOT:-}" ] && [ "$ROOT" != "$BUILD_DIR" ]; then
        cp -a "$ROOT"/. "$BUILD_DIR"/
    fi
fi

if [ ! -f "$BUILD_DIR/Dockerfile" ]; then
    echo "ERROR: Dockerfile not found after extraction."
    rm -rf "$BUILD_DIR"
    exit 1
fi

# -------------------------------------------------
# 7. Preserve production .env
# -------------------------------------------------
if [ -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env" "$BUILD_DIR/.env"
elif [ -f "$BACKUP/.env" ]; then
    cp "$BACKUP/.env" "$BUILD_DIR/.env"
else
    echo "ERROR: Production .env not found."
    rm -rf "$BUILD_DIR"
    exit 1
fi

# -------------------------------------------------
# 8. Preserve existing application data
# -------------------------------------------------
rm -rf "$BUILD_DIR/data"
mkdir -p "$BUILD_DIR/data"

if [ -d "$APP_DIR/data" ]; then
    cp -a "$APP_DIR/data"/. "$BUILD_DIR/data"/
fi

# -------------------------------------------------
# 9. Build uniquely tagged image
# -------------------------------------------------
IMAGE_TAG="ca-trader:${DEPLOY_ID}"

echo
echo "Building:"
echo "  $IMAGE_TAG"

sudo docker build \
    --pull \
    -t "$IMAGE_TAG" \
    "$BUILD_DIR"

# -------------------------------------------------
# 10. Test new image BEFORE replacing production
# -------------------------------------------------
TEST_CONTAINER="ca-trader-test-$DEPLOY_ID"

echo
echo "Starting temporary test container..."

sudo docker run -d \
    --name "$TEST_CONTAINER" \
    --env-file "$BUILD_DIR/.env" \
    -v "$APP_DIR/data:/app/data" \
    --network "$NETWORK_MAIN" \
    "$IMAGE_TAG" >/dev/null

sudo docker network connect "$NETWORK_SHARED" "$TEST_CONTAINER" 2>/dev/null || true

echo "Waiting for application..."

TEST_OK=0

for i in $(seq 1 30); do
    if sudo docker exec "$TEST_CONTAINER" \
        python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3); print(r.status); raise SystemExit(0 if r.status == 200 else 1)" \
        >/dev/null 2>&1; then
        TEST_OK=1
        break
    fi
    sleep 2
done

if [ "$TEST_OK" -ne 1 ]; then
    echo
    echo "=========================================="
    echo " NEW VERSION FAILED LOCAL TEST"
    echo "=========================================="

    sudo docker logs --tail 100 "$TEST_CONTAINER" || true
    sudo docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
    rm -rf "$BUILD_DIR"

    echo
    echo "CURRENT LIVE CONTAINER WAS NOT TOUCHED."
    echo "Website remains on the previous version."
    exit 1
fi

echo "New application passed local HTTP test."

# -------------------------------------------------
# 11. Replace production container
# -------------------------------------------------
echo
echo "Replacing production container..."

if sudo docker inspect "$APP_CONTAINER" >/dev/null 2>&1; then
    sudo docker stop "$APP_CONTAINER" >/dev/null 2>&1 || true
    sudo docker rm "$APP_CONTAINER" >/dev/null 2>&1 || true
fi

sudo docker run -d \
    --name "$APP_CONTAINER" \
    --restart unless-stopped \
    --env-file "$BUILD_DIR/.env" \
    -v "$APP_DIR/data:/app/data" \
    --network "$NETWORK_MAIN" \
    --network-alias "$APP_CONTAINER" \
    "$IMAGE_TAG" >/dev/null

sudo docker network connect "$NETWORK_SHARED" "$APP_CONTAINER" 2>/dev/null || true

# -------------------------------------------------
# 12. Test production container directly
# -------------------------------------------------
echo
echo "Testing new production container..."

PROD_OK=0

for i in $(seq 1 30); do
    if sudo docker exec "$APP_CONTAINER" \
        python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3); raise SystemExit(0 if r.status == 200 else 1)" \
        >/dev/null 2>&1; then
        PROD_OK=1
        break
    fi
    sleep 2
done

# -------------------------------------------------
# 13. Test Caddy -> application
# -------------------------------------------------
CADDY_OK=0

if [ "$PROD_OK" -eq 1 ]; then
    echo "Testing Caddy -> application..."

    for i in $(seq 1 20); do
        if sudo docker exec "$CADDY_CONTAINER" \
            wget -qSO- "http://$APP_CONTAINER:$APP_PORT/" -O /dev/null 2>&1 \
            | grep -q "200 OK"; then
            CADDY_OK=1
            break
        fi
        sleep 1
    done
fi

# -------------------------------------------------
# 14. Test public HTTPS
# -------------------------------------------------
PUBLIC_STATUS="000"

if [ "$PROD_OK" -eq 1 ] && [ "$CADDY_OK" -eq 1 ]; then
    sleep 2
    PUBLIC_STATUS="$(curl -sk -o /dev/null -w '%{http_code}' https://catrader.site/ || true)"
fi

# Accept successful HTTP and common redirect responses.
PUBLIC_OK=0
case "$PUBLIC_STATUS" in
    200|204|301|302|307|308)
        PUBLIC_OK=1
        ;;
esac

# -------------------------------------------------
# 15. Rollback exact old image if needed
# -------------------------------------------------
if [ "$PROD_OK" -ne 1 ] || [ "$CADDY_OK" -ne 1 ] || [ "$PUBLIC_OK" -ne 1 ]; then

    echo
    echo "=========================================="
    echo " DEPLOYMENT FAILED - ROLLING BACK"
    echo "=========================================="

    echo "Production test: $PROD_OK"
    echo "Caddy test:      $CADDY_OK"
    echo "Public status:   $PUBLIC_STATUS"

    sudo docker logs --tail 80 "$APP_CONTAINER" || true

    sudo docker stop "$APP_CONTAINER" >/dev/null 2>&1 || true
    sudo docker rm "$APP_CONTAINER" >/dev/null 2>&1 || true

    if [ -n "${OLD_IMAGE_ID:-}" ]; then
        echo
        echo "Restoring exact previous image:"
        echo "  $OLD_IMAGE_ID"

        sudo docker run -d \
            --name "$APP_CONTAINER" \
            --restart unless-stopped \
            --env-file "$APP_DIR/.env" \
            -v "$APP_DIR/data:/app/data" \
            --network "$NETWORK_MAIN" \
            --network-alias "$APP_CONTAINER" \
            "$OLD_IMAGE_ID" >/dev/null

        sudo docker network connect "$NETWORK_SHARED" "$APP_CONTAINER" 2>/dev/null || true

        sleep 5
    fi

    sudo docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
    rm -rf "$BUILD_DIR"

    echo
    echo "ROLLBACK COMPLETE."
    echo "The exact previous image has been restored."
    exit 1
fi

# -------------------------------------------------
# 16. Remove temporary test container
# -------------------------------------------------
sudo docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true

# -------------------------------------------------
# 17. Install source files for future reference
# -------------------------------------------------
rm -rf "$APP_DIR.new"
cp -a "$BUILD_DIR" "$APP_DIR.new"
rm -rf "$APP_DIR"
mv "$APP_DIR.new" "$APP_DIR"

# Keep existing production .env and data in place.
# The running container is already using its mounted data/config.

rm -rf "$BUILD_DIR"

# -------------------------------------------------
# 18. Cleanup old dangling images only
# -------------------------------------------------
sudo docker image prune -f >/dev/null 2>&1 || true

echo
echo "=========================================="
echo "       DEPLOYMENT SUCCESSFUL"
echo "=========================================="
echo
echo "ZIP:"
echo "  $ZIP_NAME"
echo
echo "Image:"
echo "  $IMAGE_TAG"
echo
echo "Public status:"
echo "  HTTP $PUBLIC_STATUS"
echo
echo "Container:"
sudo docker ps --filter "name=^${APP_CONTAINER}$" \
    --format '  {{.Names}} | {{.Image}} | {{.Status}}'
echo
echo "Website:"
echo "  https://catrader.site"
echo
echo "Backup:"
echo "  $BACKUP"
echo
echo "=========================================="
