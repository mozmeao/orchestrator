#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

set -ex

# Run Django tests with coverage
python manage.py test --noinput --parallel

# Optional: Run additional checks
python manage.py check --deploy

echo "All tests passed!"
