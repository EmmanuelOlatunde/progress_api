from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 20          # default
    page_size_query_param = 'page_size'  # allow client override
    max_page_size = 100     # cap it to avoid abuse
