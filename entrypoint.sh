#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py createcachetable --noinput || true

exec gunicorn lti_project_selection.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2
