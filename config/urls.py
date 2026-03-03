
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path(f'{settings.ADMIN_URL_PREFIX}/', admin.site.urls),
    path(f'{settings.CMS_URL_PREFIX}/', include('cms.urls')),
    path(f'{settings.CMS_URL_PREFIX}/marketing/', include('marketing.urls')),
    path('email/', include('marketing.public_urls')),
    path('', include('home.urls')),
    path('', include('courses.urls')),
    path('contact/', include('contact.urls')),
    path('registration/', include('registration.urls')),
]


if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
