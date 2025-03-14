#!/bin/sh

CURRENT=$(alembic current)
HEADS=$(alembic heads)

if [ "$CURRENT" = "$HEADS" ]; then
  echo "Database is up to date"
else
  echo "Database is not up to date, run alembic upgrade head"
  exit 1
fi

exec "$@"
