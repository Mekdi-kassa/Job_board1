from django.contrib import admin
from .models import Category, Job


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'category', 'job_type', 'workplace_type', 'location', 'status', 'is_featured', 'deadline', 'views_count', 'created_at']
    list_filter = ['status', 'job_type', 'workplace_type', 'experience_level', 'is_featured', 'category', 'created_at']
    search_fields = ['title', 'description', 'requirements', 'location', 'company__email', 'company__first_name', 'company__last_name']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['company', 'category']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
