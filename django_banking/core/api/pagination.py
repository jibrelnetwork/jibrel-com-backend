from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class CustomCursorPagination(CursorPagination):
    ordering = '-created_at'
    page_size = 20

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'data': data,
        })
