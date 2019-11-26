"""
COPY-MAGIC
"""
import re

import yaml
from openapi_core import create_spec
from openapi_core.shortcuts import ResponseValidator
from openapi_core.wrappers.base import BaseOpenAPIRequest, BaseOpenAPIResponse

# http://flask.pocoo.org/docs/1.0/quickstart/#variable-rules
PATH_PARAMETER_PATTERN = r'<(?:(?:string|int|float|path|uuid):)?(\w+)>'


with open('v1.swagger.yml') as fp:  # FIXME: configurable path
    spec = create_spec(yaml.safe_load(fp))


class DjangoOpenAPIRequest(BaseOpenAPIRequest):

    path_regex = re.compile(PATH_PARAMETER_PATTERN)

    def __init__(self, method, url, params, body):
        from urllib.parse import urljoin
        self.method = method.lower()
        self.path = urljoin(self.host_url, url)
        self.params = params
        self.body = body

    @property
    def host_url(self):
        return "http://localhost:8000/"

    @property
    def path_pattern(self):
        return self.path

    @property
    def parameters(self):
        return {
            # 'path': self.request.view_args,
            'query': self.params,
            # 'header': self.request.headers,
            # 'cookie': self.request.cookies,
        }


class DjangoOpenAPIResponse(BaseOpenAPIResponse):
    mimetype = "application/json"

    def __init__(self, response):
        self.response = response

    @property
    def data(self):
        return self.response.rendered_content

    @property
    def status_code(self):
        return self.response.status_code


def validate_response_schema(url, method, response, params=None, body=None):
    validator = ResponseValidator(spec)
    request = DjangoOpenAPIRequest(method, url, params, body)
    openapi_response = DjangoOpenAPIResponse(response)
    result = validator.validate(request, openapi_response)

    # raise errors if response invalid
    result.raise_for_errors()
