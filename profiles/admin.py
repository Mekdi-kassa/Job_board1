from django.contrib import admin
from .models import CompanyProfile, ApplicantProfile, Skill, WorkExperience, Education


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user_email', 'industry', 'company_size', 'is_verified_badge', 'created_at')
    list_filter = ('company_size', 'is_verified_badge', 'industry')
    search_fields = ('company_name', 'user__email', 'tagline', 'headquarters')
    prepopulated_fields = {'slug': ('company_name',)}

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'


class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 1


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ('applicant_name', 'user_email', 'headline', 'location', 'is_open_to_work', 'created_at')
    list_filter = ('is_open_to_work', 'preferred_workplace_type')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'headline', 'location')
    inlines = [WorkExperienceInline, EducationInline]

    def applicant_name(self, obj):
        return obj.user.get_full_name()
    applicant_name.short_description = 'Name'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
