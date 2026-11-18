#!/usr/bin/env bash
# Smoke test of the built Docker image: what pytest cannot see, i.e. how the
# Dockerfile assembles the app (env vars, embedded model, writable /data).
# The app itself is tested by `uv run pytest`.
#
# Usage: scripts/test-image.sh [image]      (default: pokedex)
# Run in CI right after `docker build`; a non-zero exit means: do not publish.
#
# The container runs as in production (--read-only, /data volume) on a Docker
# network with no Internet access, so the model must come from the image.
# Requests are sent from inside the container: no host port is needed.
set -euo pipefail

IMAGE="${1:-pokedex}"
NAME="pokedex-test-$$"
NETWORK="pokedex-test-$$"

cleanup() {
    docker rm -f -v "$NAME" >/dev/null 2>&1 || true
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create --internal "$NETWORK" >/dev/null
docker run -d --name "$NAME" --network "$NETWORK" \
    --read-only --tmpfs /tmp "$IMAGE" >/dev/null

# Print the HTTP status of METHOD PATH [JSON_BODY], sent from inside the container.
status() {
    docker exec "$NAME" python -c '
import sys, urllib.request as u
method, path, body = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None
req = u.Request("http://127.0.0.1:8000" + path, method=method,
                data=body.encode() if body else None,
                headers={"Content-Type": "application/json"})
try:
    print(u.urlopen(req, timeout=10).status)
except u.HTTPError as e:
    print(e.code)
except OSError:
    print("no-answer")
' "$@" 2>/dev/null || echo "no-answer"
}

logs_and_fail() {
    echo "FAIL  $1"
    echo "--- container logs ---"
    docker logs "$NAME" 2>&1 | tail -20
    exit 1
}

# Wait for the server (up to 30 s).
for _ in $(seq 30); do
    [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" = true ] \
        || logs_and_fail "container stopped at startup"
    [ "$(status GET /api/health)" = 200 ] && break
    sleep 1
done

failures=0
check() {
    local label=$1 expected=$2
    shift 2
    local got
    got=$(status "$@")
    if [ "$got" = "$expected" ]; then
        echo "ok    $label"
    else
        echo "FAIL  $label: expected $expected, got $got"
        failures=$((failures + 1))
    fi
}

check "frontend served at /"                  200 GET /
check "server up, pokedex.db readable"        200 GET /api/health
check "model embedded (search with no network)" 200 GET \
    "/api/pokemon/identify?description=small%20yellow%20mouse%20with%20red%20cheeks"
check "/data writable (feedback saved)"       201 POST /api/feedback/missing-result \
    '{"kind": "name", "query": "image smoke test", "shown_ids": []}'

[ "$failures" -eq 0 ] || logs_and_fail "$failures check(s) failed"
