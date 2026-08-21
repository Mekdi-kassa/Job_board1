from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta

from user.models import User
from jobs.models import Job
from applications.models import Application
from profiles.models import ApplicantProfile, Skill


def get_company_dashboard(user):
    """
    Compute real-time employer hiring metrics, candidate pipeline, and activity.
    """
    company_jobs = Job.objects.filter(company=user)
    company_applications = Application.objects.filter(job__company=user)

    # Overview
    total_jobs = company_jobs.count()
    active_jobs = company_jobs.filter(status=Job.Status.PUBLISHED).count()
    closed_jobs = company_jobs.filter(status__in=[Job.Status.CLOSED, Job.Status.ARCHIVED]).count()
    draft_jobs = company_jobs.filter(status=Job.Status.DRAFT).count()
    total_applications = company_applications.count()
    total_views = company_jobs.aggregate(total=Sum('views_count'))['total'] or 0

    # Pipeline Breakdown
    pipeline_counts = dict(
        company_applications.order_by().values_list('status').annotate(count=Count('id'))
    )

    pipeline = {
        'pending': pipeline_counts.get(Application.Status.PENDING, 0),
        'reviewed': pipeline_counts.get(Application.Status.REVIEWED, 0),
        'shortlisted': pipeline_counts.get(Application.Status.SHORTLISTED, 0),
        'interviewed': pipeline_counts.get(Application.Status.INTERVIEWED, 0),
        'offered': pipeline_counts.get(Application.Status.OFFERED, 0),
        'hired': pipeline_counts.get(Application.Status.HIRED, 0),
        'rejected': pipeline_counts.get(Application.Status.REJECTED, 0),
        'withdrawn': pipeline_counts.get(Application.Status.WITHDRAWN, 0),
    }

    # Top Performing Jobs
    top_jobs = company_jobs.filter(status=Job.Status.PUBLISHED).order_by('-applications_count', '-views_count')[:5].values(
        'id', 'title', 'slug', 'views_count', 'applications_count', 'created_at'
    )

    # Recent Applicants Stream
    recent_applications = company_applications.select_related('applicant', 'job').order_by('-applied_at')[:5]
    recent_applicants_list = [
        {
            'id': str(app.id),
            'applicant_name': app.applicant.get_full_name() or app.applicant.username,
            'applicant_email': app.applicant.email,
            'job_id': str(app.job.id),
            'job_title': app.job.title,
            'status': app.status,
            'status_display': app.get_status_display(),
            'rating': app.rating,
            'applied_at': app.applied_at
        }
        for app in recent_applications
    ]

    return {
        'overview': {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'draft_jobs': draft_jobs,
            'closed_jobs': closed_jobs,
            'total_applications': total_applications,
            'total_job_views': total_views,
        },
        'pipeline': pipeline,
        'top_jobs': list(top_jobs),
        'recent_applicants': recent_applicants_list
    }


def get_applicant_dashboard(user):
    """
    Compute job seeker application tracker and personalized job recommendations.
    """
    my_applications = Application.objects.filter(applicant=user).select_related('job', 'job__company')

    total_applications = my_applications.count()
    status_counts = dict(
        my_applications.order_by().values_list('status').annotate(count=Count('id'))
    )

    overview = {
        'total_applications': total_applications,
        'pending_review': status_counts.get(Application.Status.PENDING, 0),
        'reviewed': status_counts.get(Application.Status.REVIEWED, 0),
        'shortlisted': status_counts.get(Application.Status.SHORTLISTED, 0),
        'interviewed': status_counts.get(Application.Status.INTERVIEWED, 0),
        'offered': status_counts.get(Application.Status.OFFERED, 0),
        'hired': status_counts.get(Application.Status.HIRED, 0),
        'rejected': status_counts.get(Application.Status.REJECTED, 0),
        'withdrawn': status_counts.get(Application.Status.WITHDRAWN, 0),
    }

    # Recent Applications
    recent_apps = my_applications.order_by('-applied_at')[:5]
    recent_apps_list = [
        {
            'id': str(app.id),
            'job_id': str(app.job.id),
            'job_title': app.job.title,
            'job_slug': app.job.slug,
            'company_name': app.job.company.get_full_name() or app.job.company.username,
            'location': app.job.location,
            'workplace_type': app.job.workplace_type,
            'status': app.status,
            'status_display': app.get_status_display(),
            'applied_at': app.applied_at
        }
        for app in recent_apps
    ]

    # Skill-Matched Recommended Jobs
    try:
        profile = user.applicant_profile
        user_skill_names = list(profile.skills.values_list('name', flat=True))
    except Exception:
        profile = None
        user_skill_names = []

    applied_job_ids = my_applications.values_list('job_id', flat=True)
    recommended_qs = Job.objects.filter(
        status=Job.Status.PUBLISHED
    ).exclude(
        id__in=applied_job_ids
    ).select_related('company', 'category')

    if user_skill_names:
        # Match any of the candidate's skills in title, requirements, or description
        skill_query = Q()
        for skill_name in user_skill_names[:5]:
            skill_query |= Q(title__icontains=skill_name) | Q(requirements__icontains=skill_name)
        recommended_qs = recommended_qs.filter(skill_query)

    # Fallback to latest published jobs if no skill matches found
    if not recommended_qs.exists():
        recommended_qs = Job.objects.filter(status=Job.Status.PUBLISHED).exclude(id__in=applied_job_ids)

    recommended_jobs = recommended_qs.order_by('-is_featured', '-created_at')[:5].values(
        'id', 'title', 'slug', 'company__first_name', 'company__last_name',
        'location', 'workplace_type', 'job_type', 'min_salary', 'max_salary', 'is_featured'
    )

    return {
        'overview': overview,
        'recent_applications': recent_apps_list,
        'recommended_jobs': list(recommended_jobs)
    }


def get_admin_dashboard():
    """
    Platform health, user distributions, and conversion analytics for Super Admin.
    """
    total_users = User.objects.count()
    applicants_count = User.objects.filter(role=User.Role.APPLICANT).count()
    companies_count = User.objects.filter(role=User.Role.COMPANY).count()
    verified_companies = User.objects.filter(role=User.Role.COMPANY, is_verified=True).count()

    # 30-day user growth
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_users_month = User.objects.filter(created_at__gte=thirty_days_ago).count()

    # Jobs Metrics
    total_jobs = Job.objects.count()
    active_jobs = Job.objects.filter(status=Job.Status.PUBLISHED).count()
    closed_jobs = Job.objects.filter(status__in=[Job.Status.CLOSED, Job.Status.ARCHIVED]).count()
    featured_jobs = Job.objects.filter(status=Job.Status.PUBLISHED, is_featured=True).count()
    total_job_views = Job.objects.aggregate(total=Sum('views_count'))['total'] or 0

    # Applications & Hiring Conversion
    total_applications = Application.objects.count()
    total_hired = Application.objects.filter(status=Application.Status.HIRED).count()
    conversion_rate = round((total_hired / total_applications * 100), 1) if total_applications > 0 else 0.0

    # Recent Registrations
    recent_users = User.objects.order_by('-created_at')[:5].values(
        'id', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'created_at'
    )

    # Recent Job Postings
    recent_jobs = Job.objects.select_related('company').order_by('-created_at')[:5].values(
        'id', 'title', 'slug', 'company__email', 'status', 'created_at'
    )

    return {
        'user_metrics': {
            'total_users': total_users,
            'applicants_count': applicants_count,
            'companies_count': companies_count,
            'verified_companies_count': verified_companies,
            'new_users_past_30_days': new_users_month,
        },
        'job_metrics': {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'closed_jobs': closed_jobs,
            'featured_jobs': featured_jobs,
            'total_views': total_job_views,
        },
        'application_metrics': {
            'total_applications': total_applications,
            'total_hired': total_hired,
            'hiring_conversion_rate_percentage': conversion_rate,
        },
        'recent_activity': {
            'recent_users': list(recent_users),
            'recent_jobs': list(recent_jobs)
        }
    }
