from django.db.models import Q
from django.utils import timezone


def filter_jobs(queryset, params):
    """
    Filter and search Job queryset according to query parameters.
    """
    # 1. Keyword search (title, description, requirements, company name)
    search_query = params.get('q') or params.get('search')
    if search_query:
        search_query = search_query.strip()
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(requirements__icontains=search_query) |
            Q(responsibilities__icontains=search_query) |
            Q(company__first_name__icontains=search_query) |
            Q(company__last_name__icontains=search_query) |
            Q(company__username__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    # 2. Category filter (by slug or ID)
    category = params.get('category')
    if category:
        queryset = queryset.filter(
            Q(category__slug=category) | Q(category__id=category) if len(category) > 30 else Q(category__slug=category)
        )

    # 3. Job Type filter
    job_type = params.get('job_type')
    if job_type:
        types = [t.strip() for t in job_type.split(',')]
        queryset = queryset.filter(job_type__in=types)

    # 4. Workplace Type filter (remote, on_site, hybrid)
    workplace_type = params.get('workplace_type')
    if workplace_type:
        workplaces = [w.strip() for w in workplace_type.split(',')]
        queryset = queryset.filter(workplace_type__in=workplaces)

    # 5. Experience Level filter
    experience_level = params.get('experience_level')
    if experience_level:
        levels = [l.strip() for l in experience_level.split(',')]
        queryset = queryset.filter(experience_level__in=levels)

    # 6. Location filter
    location = params.get('location')
    if location:
        queryset = queryset.filter(location__icontains=location.strip())

    # 7. Salary filters
    min_salary = params.get('min_salary')
    if min_salary:
        try:
            queryset = queryset.filter(max_salary__gte=float(min_salary))
        except ValueError:
            pass

    max_salary = params.get('max_salary')
    if max_salary:
        try:
            queryset = queryset.filter(min_salary__lte=float(max_salary))
        except ValueError:
            pass

    # 8. Featured only
    featured = params.get('is_featured')
    if featured and featured.lower() in ('true', '1'):
        queryset = queryset.filter(is_featured=True)

    # 9. Active deadline filter (optional flag: active_only=true)
    active_only = params.get('active_only', 'true').lower() in ('true', '1')
    if active_only:
        queryset = queryset.filter(
            Q(deadline__isnull=True) | Q(deadline__gte=timezone.now().date())
        )

    # 10. Ordering
    ordering = params.get('ordering', '-created_at')
    allowed_orderings = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'salary_high': '-max_salary',
        'salary_low': 'min_salary',
        'closing_soon': 'deadline',
        'popular': '-views_count',
        '-created_at': '-created_at',
        'created_at': 'created_at',
        '-views_count': '-views_count',
        'views_count': 'views_count',
        '-max_salary': '-max_salary',
        'min_salary': 'min_salary',
        'deadline': 'deadline',
    }
    order_field = allowed_orderings.get(ordering, '-created_at')
    queryset = queryset.order_by(order_field)

    return queryset
