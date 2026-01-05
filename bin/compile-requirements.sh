#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Compile requirements.txt from requirements.in using uv with hashes
set -euo pipefail

export UV_CUSTOM_COMPILE_COMMAND="make compile-requirements"

pip install -U uv

rm -f requirements/*.txt

uv pip compile --generate-hashes --no-strip-extras requirements/requirements.in -o requirements/requirements.txt
