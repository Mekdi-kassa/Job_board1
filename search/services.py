from django.db.models import Q, Count, Case, When, IntegerField, F
from django.utils import timezone
from jobs.models import Job, Category
from profiles.models import CompanyProfile, Skill


def perform_unified_search(params):
    """
    Perform unified full-text search and filtering on published active jobs.
    """
    queryset = Job.objects.filter(
        status=Job.Status.PUBLISHED
    ).filter(
        Q(deadline__isnull=True) | Q(deadline__gte=timezone.now().date())
    ).select_related('company', 'category')

    query = params.get('q', '').strip()
    if query:
        # Multi-field search
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(requirements__icontains=query) |
            Q(responsibilities__icontains=query) |
            Q(location__icontains=query) |
            Q(company__first_name__icontains=query) |
            Q(company__last_name__icontains=query) |
            Q(company__username__icontains=query) |
            Q(category__name__icontains=query)
        )

    # Filter: Category (slug or id)
    category_param = params.get('category')
    if category_param:
        queryset = queryset.filter(
            Q(category__slug=category_param) | Q(category__id__iexact=category_param)
        )

    # Filter: Workplace Type
    workplace_param = params.get('workplace_type')
    if workplace_param:
        queryset = queryset.filter(workplace_type=workplace_param.lower())

    # Filter: Job Type
    job_type_param = params.get('job_type')
    if job_type_param:
        queryset = queryset.filter(job_type=job_type_param.lower())

    # Filter: Experience Level
    exp_param = params.get('experience_level')
    if exp_param:
        queryset = queryset.filter(experience_level=exp_param.lower())

    # Filter: Location
    location_param = params.get('location')
    if location_param:
        queryset = queryset.filter(location__icontains=location_param)

    # Filter: Minimum Salary
    min_salary_param = params.get('min_salary')
    if min_salary_param:
        try:
            queryset = queryset.filter(min_salary__gte=float(min_salary_param))
        except ValueError:
            pass

    # Filter: Maximum Salary
    max_salary_param = params.get('max_salary')
    if max_salary_param:
        try:
            queryset = queryset.filter(max_salary__lte=float(max_salary_param))
        except ValueError:
            pass

    # Filter: Featured Only
    featured_param = params.get('is_featured')
    if featured_param and featured_param.lower() in ('true', '1'):
        queryset = queryset.filter(is_featured=True)

    # Ordering
    ordering = params.get('ordering', 'newest')
    if ordering == 'salary_high_to_low':
        queryset = queryset.order_by('-max_salary', '-min_salary')
    elif ordering == 'salary_low_to_high':
        queryset = queryset.order_by('min_salary', 'max_salary')
    elif ordering == 'most_viewed':
        queryset = queryset.order_by('-views_count')
    elif ordering == 'most_applied':
        queryset = queryset.order_by('-applications_count')
    elif ordering == 'deadline_soonest':
        queryset = queryset.order_by(F('deadline').asc(nulls_last=True))
    elif ordering == 'relevance' and query:
        # Give highest weight to title match, then featured, then created_at
        queryset = queryset.annotate(
            title_match=Case(
                When(title__icontains=query, then=2),
                default=0,
                output_field=IntegerField()
            )
        ).order_by('-is_featured', '-title_match', '-created_at')
    else:  # newest (default)
        queryset = queryset.order_by('-is_featured', '-created_at')

    return queryset


def get_autocomplete_suggestions(query):
    """
    Fast typeahead autocomplete returning top matches across jobs, companies, categories, and skills.
    """
    if not query or len(query.strip()) < 2:
        return {'jobs': [], 'companies': [], 'categories': [], 'skills': []}

    q = query.strip()

    # Matching Jobs
    job_matches = Job.objects.filter(
        status=Job.Status.PUBLISHED,
        title__icontains=q
    ).values('id', 'title', 'slug', 'location', 'job_type', 'workplace_type')[:5]

    # Matching Companies
    company_matches = CompanyProfile.objects.filter(
        company_name__icontains=q
    ).values('id', 'company_name', 'slug', 'headquarters', 'is_verified_badge')[:5]

    # Matching Categories
    category_matches = Category.objects.filter(
        is_active=True,
        name__icontains=q
    ).values('id', 'name', 'slug', 'icon')[:5]

    # Matching Skills
    skill_matches = Skill.objects.filter(
        name__icontains=q
    ).values('id', 'name', 'slug')[:5]

    return {
        'jobs': list(job_matches),
        'companies': list(company_matches),
        'categories': list(category_matches),
        'skills': list(skill_matches)
    }


def get_search_facets(queryset):
    """
    Compute faceted counts across workplace types, job types, experience levels, and categories.
    """
    # Workplace Types aggregation
    workplace_counts = dict(
        queryset.order_by().values_list('workplace_type').annotate(count=Count('id'))
    )

    # Job Types aggregation
    job_type_counts = dict(
        queryset.order_by().values_list('job_type').annotate(count=Count('id'))
    )

    # Experience Levels aggregation
    experience_counts = dict(
        queryset.order_by().values_list('experience_level').annotate(count=Count('id'))
    )

    # Categories breakdown
    category_counts = list(
        Category.objects.filter(is_active=True).annotate(
            count=Count('jobs', filter=Q(jobs__status=Job.Status.PUBLISHED))
        ).filter(count__gt=0).values('id', 'name', 'slug', 'count')
    )

    return {
        'workplace_types': workplace_counts,
        'job_types': job_type_counts,
        'experience_levels': experience_counts,
        'categories': category_counts
    }


def get_trending_discovery():
    """
    Trending job searches, top active categories, and featured employers.
    """
    # Top Categories with active jobs
    top_categories = Category.objects.filter(is_active=True).annotate(
        job_count=Count('jobs', filter=Q(jobs__status=Job.Status.PUBLISHED))
    ).order_by('-job_count')[:6].values('id', 'name', 'slug', 'icon', 'job_count')

    # Top Featured Jobs
    featured_jobs = Job.objects.filter(
        status=Job.Status.PUBLISHED,
        is_featured=True
    ).select_related('company', 'category')[:6]

    # Top Companies
    featured_companies = CompanyProfile.objects.annotate(
        active_jobs=Count('user__jobs', filter=Q(user__jobs__status=Job.Status.PUBLISHED))
    ).order_by('-is_verified_badge', '-active_jobs')[:6].values(
        'id', 'company_name', 'slug', 'headquarters', 'is_verified_badge', 'active_jobs'
    )

    return {
        'top_categories': list(top_categories),
        'featured_companies': list(featured_companies),
        'trending_keywords': [
            'Python', 'Django', 'React', 'Remote', 'Full Stack',
            'DevOps', 'Data Science', 'Machine Learning', 'UI/UX'
        ]
    }
