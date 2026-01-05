# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
URL configuration for orchestrator project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from google_marketing_platform.views import index, liveness

urlpatterns = [
    path("", index, name="index"),
    # Liveness endpoint - lightweight check that app process is responsive
    path("liveness/", liveness, name="liveness"),
    # Readiness endpoint - comprehensive health checks (database, cache)
    path("readiness/", include("watchman.urls"), name="readiness"),
    # Legacy health endpoint - keeping for backwards compatibility
    path("health/", include("watchman.urls"), name="health"),
]

# Only enable admin in DEBUG mode (development)
if settings.DEBUG:
    urlpatterns += [
        path("admin/", admin.site.urls),
    ]
