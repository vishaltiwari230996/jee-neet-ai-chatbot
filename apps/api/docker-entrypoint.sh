#!/usr/bin/env sh
set -eu

if [ "${NEETAI_DATABASE_BACKEND:-postgres}" = "postgres" ]; then
  echo "Running database migrations..."
  alembic -c migrations/alembic.ini upgrade head

  echo "Seeding onboarding questions..."
  python scripts/ingest_questions.py infra/data/onboarding_questions.csv
else
  echo "Skipping migrations/seed because NEETAI_DATABASE_BACKEND=${NEETAI_DATABASE_BACKEND:-unset}"
fi

exec uvicorn neetai_api.main:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
