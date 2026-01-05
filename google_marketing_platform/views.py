# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.http import JsonResponse


def index(request):
    """Root endpoint returning 200 OK."""
    return JsonResponse({"status": "ok"})


def liveness(_request):
    """
    Just verifies the application process can respond to requests.
    """
    return JsonResponse({"status": "alive"})
