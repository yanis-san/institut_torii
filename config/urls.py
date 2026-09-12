
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path(f'{settings.ADMIN_URL_PREFIX}/', admin.site.urls),
    path(f'{settings.CMS_URL_PREFIX}/', include('cms.urls')),
    path(f'{settings.CMS_URL_PREFIX}/marketing/', include('marketing.urls')),
    path('email/', include('marketing.public_urls')),
    path('', include('home.urls')),
    path('', include('courses.urls')),
    path('contact/', include('contact.urls')),
    path('registration/', include('registration.urls')),
    path('appointments/', include('appointments.urls')),
]

# Sert les fichiers médias (reçus CCP) même en production (adapté pour cPanel)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
