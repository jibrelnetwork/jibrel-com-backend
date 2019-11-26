from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthcheckAPIView(APIView):

    permission_classes = []

    def get(self, request):
        return Response({
            'healthy': True,
            'version': getattr(settings, 'VERSION', 'undefined'),
        })
