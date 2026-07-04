#!/usr/bin/env bash
# PortföyAI backend testlerini TAMAMEN İZOLE bir Docker+Postgres ortamında çalıştırır.
#
# Neden var: `docker compose exec backend pytest` dev container'ın kendi env'ini
# kullanır ve suite sonundaki `alembic downgrade base` GERÇEK dev veritabanını
# siler (2026-07-03'te yaşandı, satır verisi kurtarılamadı). Bu script dev
# compose stack'ine ve volume'lerine hiç dokunmaz: kendi network'ünde disposable
# bir postgres:16-alpine kaldırır, testleri --rm bir container'da o Postgres'e
# işaret eden env'lerle koşar, ne olursa olsun arkasını temizler.
#
# Kullanım (repo kökünden):
#   bash backend/scripts/run-isolated-tests.sh            # pytest + ruff
#   bash backend/scripts/run-isolated-tests.sh -k test_x  # ek argümanlar pytest'e geçer
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="portfoyai-backend-test"
SUFFIX="$$-$RANDOM"
NET="portfoyai-test-net-$SUFFIX"
PG="portfoyai-test-pg-$SUFFIX"

cleanup() {
  docker rm -f "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# --- Docker Desktop ayakta mı? Değilse başlat ve bekle (Windows) ---
if ! docker info >/dev/null 2>&1; then
  echo ">> Docker daemon yanıt vermiyor, Docker Desktop başlatılıyor..."
  if [ -f "/c/Program Files/Docker/Docker/Docker Desktop.exe" ]; then
    "/c/Program Files/Docker/Docker/Docker Desktop.exe" >/dev/null 2>&1 &
  fi
  for i in $(seq 1 60); do
    docker info >/dev/null 2>&1 && break
    [ "$i" -eq 60 ] && { echo "HATA: Docker 3 dakikada ayağa kalkmadı"; exit 1; }
    sleep 3
  done
  echo ">> Docker hazır."
fi

echo ">> Test image'ı build ediliyor ($IMAGE)..."
docker build -q -t "$IMAGE" "$REPO_ROOT/backend"

echo ">> İzole network + disposable Postgres kuruluyor ($NET)..."
docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" \
  -e POSTGRES_USER=portfoyai -e POSTGRES_PASSWORD=portfoyai -e POSTGRES_DB=portfoyai \
  postgres:16-alpine >/dev/null

# Resmi postgres imajı init sırasında bir kez yeniden başlar; pg_isready tek
# başına yeterli değil — CREATE DATABASE başarana kadar dene.
echo ">> Postgres bekleniyor..."
for i in $(seq 1 30); do
  if docker exec "$PG" psql -U portfoyai -c "CREATE DATABASE portfoyai_test;" >/dev/null 2>&1; then
    break
  fi
  if docker exec "$PG" psql -U portfoyai -tc "SELECT 1 FROM pg_database WHERE datname='portfoyai_test'" 2>/dev/null | grep -q 1; then
    break
  fi
  [ "$i" -eq 30 ] && { echo "HATA: Postgres 30 saniyede hazır olmadı"; exit 1; }
  sleep 1
done

ENVS=(
  -e "DATABASE_URL=postgresql+psycopg2://portfoyai_app:portfoyai_app@$PG:5432/portfoyai_test"
  -e "MIGRATIONS_DATABASE_URL=postgresql+psycopg2://portfoyai:portfoyai@$PG:5432/portfoyai_test"
  -e "AUTH_DATABASE_URL=postgresql+psycopg2://portfoyai_auth:portfoyai_auth@$PG:5432/portfoyai_test"
)

echo ">> pytest çalışıyor..."
docker run --rm --network "$NET" "${ENVS[@]}" "$IMAGE" pytest -q "$@"

echo ">> ruff çalışıyor..."
docker run --rm --entrypoint sh "$IMAGE" -c "pip install -q ruff && ruff check app"

echo ">> TAMAM: testler ve lint izole ortamda yeşil."
