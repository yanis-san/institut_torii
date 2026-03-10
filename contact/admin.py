from django.contrib import admin
from .models import Prospect


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = (
        'first_name', 'last_name', 'email', 'phone',
        'interested_category', 'interested_language',
        'created_at', 'converted',
    )
    list_filter = (
        'interested_category', 'interested_language',
        'converted', 'source', 'level', 'created_at',
    )
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    readonly_fields = ('created_at',)
    #date_hierarchy = 'created_at'
