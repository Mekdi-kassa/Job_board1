from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .services import (
    perform_unified_search,
    get_autocomplete_suggestions,
    get_search_facets,
    get_trending_discovery
)
from jobs.serializers import JobPublicListSerializer
from jobs.views import StandardResultsSetPagination
from jobs.models import Job


class UnifiedSearchView(generics.ListAPIView):
    """
    Unified full-text search across jobs, companies, skills, and categories.
    Supports multi-filtering (category, workplace, salary, experience, location) and sorting.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = JobPublicListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return perform_unified_search(self.request.query_params)


class AutocompleteSuggestionsView(APIView):
    """
    Fast typeahead autocomplete suggestions for search bars.
    Returns matching jobs, companies, categories, and skills.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        suggestions = get_autocomplete_suggestions(query)
        return Response({
            'success': True,
            'query': query,
            'data': suggestions
        })


class SearchFacetsView(APIView):
    """
    Faceted filter aggregations (workplace type, job type, experience level, categories).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        search_queryset = perform_unified_search(request.query_params)
        facets = get_search_facets(search_queryset)
        return Response({
            'success': True,
            'total_matches': search_queryset.count(),
            'facets': facets
        })


class TrendingDiscoveryView(APIView):
    """
    Trending job searches, top active categories, featured companies, and featured jobs.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        discovery_data = get_trending_discovery()
        featured_jobs = Job.objects.filter(
            status=Job.Status.PUBLISHED,
            is_featured=True
        ).select_related('company', 'category')[:6]

        discovery_data['featured_jobs'] = JobPublicListSerializer(featured_jobs, many=True).data

        return Response({
            'success': True,
            'data': discovery_data
        })
