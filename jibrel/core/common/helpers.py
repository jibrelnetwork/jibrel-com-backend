from django.http import HttpResponseBadRequest


def get_bad_request_response(msg: str) -> HttpResponseBadRequest:
    return HttpResponseBadRequest(
        f'<h1>{msg}</h1>'.encode('utf-8')
    )
