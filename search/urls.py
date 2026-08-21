from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    # Unified Search
    path('', views.UnifiedSearchView.as_view(), name='unified-search'),
    
    # Autocomplete Suggestions
    path('suggestions/', views.AutocompleteSuggestionsView.as_view(), name='search-suggestions'),
    
    # Search Facets & Filter Aggregations
    path('facets/', views.SearchFacetsView.as_view(), name='search-facets'),
    
    # Trending & Discovery Hub
    path('trending/', views.TrendingDiscoveryView.as_view(), name='trending-discovery'),
]
