import django_filters
from .models import Task
from django.db.models import Q

class TaskFilter(django_filters.FilterSet):

    category = django_filters.CharFilter(
        field_name='category', # Filter by the field of the related Category model
        
    )
        
    # Filter by priority (case-insensitive exact match)
    priority = django_filters.CharFilter(
        field_name='priority',
        lookup_expr='iexact'
    )

    # Filter by completion status (maps to the 'is_completed' field)
    is_completed = django_filters.BooleanFilter(
        field_name='is_completed'
    )

    # Add a search filter for title and description
    search = django_filters.CharFilter(method='filter_by_search')

    class Meta:
        model = Task
        # Specify the fields that can be filtered using the DjangoFilterBackend
        fields = ['category', 'priority', 'is_completed', 'difficulty']

    def filter_by_search(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))