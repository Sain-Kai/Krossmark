from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from surveillance.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health"),
    path("api/v1/", include("surveillance.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
