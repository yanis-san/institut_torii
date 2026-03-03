from django.urls import path
from . import views

app_name = 'registration'

urlpatterns = [
    path('', views.cohort_list, name='cohort_list'),
    path('enroll/<slug:slug>/', views.enroll, name='enroll'),
    path('success/<str:code>/', views.enrollment_success, name='success'),
    path('check-status/', views.check_status, name='check_status'),
    path('api/status/<slug:slug>/', views.cohort_status_api, name='cohort_status_api'),
]
