"""
Marketing URL configuration.

CMS management routes: templates, campaigns, subscribers.
All protected by @login_required in the views.
"""
from django.urls import path
from . import views

app_name = 'marketing'

urlpatterns = [
    # Email Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:pk>/preview/', views.template_preview, name='template_preview'),

    # Email Campaigns
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaigns/<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),
    path('campaigns/<int:pk>/populate/', views.campaign_populate, name='campaign_populate'),
    path('campaigns/<int:pk>/send/', views.campaign_send, name='campaign_send'),
    path('campaigns/<int:pk>/cancel/', views.campaign_cancel, name='campaign_cancel'),
    path('campaigns/<int:pk>/preview/', views.campaign_preview, name='campaign_preview'),

    # Subscribers
    path('subscribers/', views.subscriber_list, name='subscriber_list'),

    # Notification Log
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),
]
