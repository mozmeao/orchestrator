#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

set -ex

# Run migrations
python manage.py migrate --noinput

# Start Granian in development mode
exec granian \
    --interface wsgi \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${GRANIAN_WORKERS:-1} \
    --blocking-threads ${GRANIAN_BLOCKING_THREADS:-1} \
    --log-level ${GRANIAN_LOG_LEVEL:-debug} \
    --access-log \
    orchestrator.wsgi:application
