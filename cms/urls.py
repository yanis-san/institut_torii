from django.urls import path
from . import views

app_name = 'cms'

urlpatterns = [
    # Auth
    path('login/', views.cms_login, name='login'),
    path('logout/', views.cms_logout, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Prospects
    path('prospects/', views.prospect_list, name='prospect_list'),
    path('prospects/<int:pk>/', views.prospect_detail, name='prospect_detail'),
    path('prospects/<int:pk>/rating/', views.prospect_set_rating, name='prospect_set_rating'),
    path('prospects/<int:pk>/status/', views.prospect_set_status, name='prospect_set_status'),
    path('prospects/<int:pk>/delete/', views.prospect_delete, name='prospect_delete'),

    # Enrollments
    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/<int:pk>/', views.enrollment_detail, name='enrollment_detail'),
    path('enrollments/<int:pk>/confirm/', views.enrollment_confirm, name='enrollment_confirm'),
    path('enrollments/<int:pk>/reject/', views.enrollment_reject, name='enrollment_reject'),
    path('enrollments/<int:pk>/refund/', views.enrollment_refund, name='enrollment_refund'),

    # Cohorts
    path('cohorts/', views.cohort_list, name='cohort_list'),
    path('cohorts/create/', views.cohort_create, name='cohort_create'),
    path('cohorts/<int:pk>/', views.cohort_edit, name='cohort_edit'),
    path('cohorts/<int:pk>/delete/', views.cohort_delete, name='cohort_delete'),
    path('cohorts/<int:pk>/toggle/', views.cohort_toggle, name='cohort_toggle'),

    # Catalog
    path('catalog/', views.catalog_settings, name='catalog_settings'),
    path('catalog/category/', views.category_form, name='category_create'),
    path('catalog/category/<int:pk>/', views.category_form, name='category_edit'),
    path('catalog/language/', views.language_form, name='language_create'),
    path('catalog/language/<int:pk>/', views.language_form, name='language_edit'),
    path('catalog/format/', views.format_form, name='format_create'),
    path('catalog/format/<int:pk>/', views.format_form, name='format_edit'),

    # Content
    path('content/homepage/', views.edit_homepage, name='edit_homepage'),
    path('content/settings/', views.edit_settings, name='edit_settings'),

    # Analytics
    path('analytics/', views.analytics, name='analytics'),

    # Appointments
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='appointment_delete'),
    path('appointments/categories/', views.appointment_category_list, name='appointment_category_list'),
    path('appointments/categories/create/', views.appointment_category_form, name='appointment_category_create'),
    path('appointments/categories/<int:pk>/edit/', views.appointment_category_form, name='appointment_category_edit'),
    path('appointments/categories/<int:pk>/delete/', views.appointment_category_delete, name='appointment_category_delete'),
    path('appointments/categories/<int:category_pk>/timeslots/create/', views.timeslot_form, name='timeslot_create'),
    path('appointments/categories/<int:category_pk>/timeslots/bulk/', views.timeslot_bulk_create, name='timeslot_bulk_create'),
    path('appointments/categories/<int:category_pk>/timeslots/<int:pk>/edit/', views.timeslot_form, name='timeslot_edit'),
    path('appointments/timeslots/<int:pk>/delete/', views.timeslot_delete, name='timeslot_delete'),

    # Protected media (receipts)
    path('media/receipts/<path:path>', views.serve_receipt, name='serve_receipt'),
]
