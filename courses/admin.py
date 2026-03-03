from django.contrib import admin
from .models import Category, Language, CourseFormat, Cohort, CohortSchedule


class CohortScheduleInline(admin.TabularInline):
    model = CohortSchedule
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'order')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order',)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'flag_emoji', 'order')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order',)


@admin.register(CourseFormat)
class CourseFormatAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_online', 'is_individual', 'order')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order',)


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'language', 'format',
        'price', 'start_date', 'is_active', 'is_featured', 'order',
    )
    list_filter = ('category', 'language', 'format', 'is_active', 'is_featured')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'is_featured', 'order')
    inlines = [CohortScheduleInline]
