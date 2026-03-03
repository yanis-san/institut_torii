from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('japanese/', views.language_detail, {'slug': 'japanese'}, name='japanese'),
    path('chinese/', views.language_detail, {'slug': 'chinese'}, name='chinese'),
    path('korean/', views.language_detail, {'slug': 'korean'}, name='korean'),
    path('workshops/artistic/', views.workshop_list, {'workshop_type': 'artistic'}, name='workshops_artistic'),
    path('workshops/culinary/', views.workshop_list, {'workshop_type': 'culinary'}, name='workshops_culinary'),
    path('api/cohorts/', views.cohorts_by_category, name='api_cohorts'),
]
