from django.urls import path

from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.book, name='book'),
    path('<slug:slug>/dates/', views.available_dates, name='available_dates'),
    path('<slug:slug>/slots/', views.available_slots, name='available_slots'),
    path('slot/<int:pk>/form/', views.booking_form, name='booking_form'),
    path('slot/<int:pk>/confirm/', views.confirm_booking, name='confirm_booking'),
    path('success/<str:code>/', views.success, name='success'),
]
