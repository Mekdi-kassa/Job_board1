from rest_framework import serializers
from jobs.serializers import JobPublicListSerializer


class SearchSuggestionsSerializer(serializers.Serializer):
    """Autocomplete suggestions response"""
    jobs = serializers.ListField(child=serializers.DictField())
    companies = serializers.ListField(child=serializers.DictField())
    categories = serializers.ListField(child=serializers.DictField())
    skills = serializers.ListField(child=serializers.DictField())


class FacetsSerializer(serializers.Serializer):
    """Search faceted aggregations"""
    workplace_types = serializers.DictField()
    job_types = serializers.DictField()
    experience_levels = serializers.DictField()
    categories = serializers.ListField(child=serializers.DictField())


class TrendingDiscoverySerializer(serializers.Serializer):
    """Trending and discovery hub"""
    top_categories = serializers.ListField(child=serializers.DictField())
    featured_jobs = JobPublicListSerializer(many=True)
    featured_companies = serializers.ListField(child=serializers.DictField())
    trending_keywords = serializers.ListField(child=serializers.CharField())
