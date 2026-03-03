"""
Marketing public URL routes — no authentication required.

Unsubscribe and email tracking endpoints.
"""
from django.urls import path
from . import views

app_name = 'marketing_public'

urlpatterns = [
    path('unsubscribe/<uuid:token>/', views.unsubscribe, name='unsubscribe'),
    path('track/open/<uuid:token>/', views.track_open, name='track_open'),
    path('track/click/<uuid:token>/', views.track_click, name='track_click'),
]
