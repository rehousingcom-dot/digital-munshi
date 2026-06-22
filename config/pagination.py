from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """50 per page default; ?page_size= se override (max 500). Billing dropdowns
    bade page_size maang sakti hain.
    """
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500
