import django_filters

from apichallenge.documents.models import Document


class DocumentFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    content_type = django_filters.CharFilter(lookup_expr="icontains")
    uploaded_by = django_filters.NumberFilter(field_name="uploaded_by__id")
    created_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    class Meta:
        model = Document
        fields = ["title", "content_type", "uploaded_by", "created_after", "created_before"]
