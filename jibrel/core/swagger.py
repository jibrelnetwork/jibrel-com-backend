import yaml
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView


class SwaggerJsonSchema(APIView):
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]

    @method_decorator(cache_page(60))
    def get(self, request):
        with open('v1.swagger.yml') as yaml_file:
            schema = yaml.load(yaml_file)
        return Response(schema)
