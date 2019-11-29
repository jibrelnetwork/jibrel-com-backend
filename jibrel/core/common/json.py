from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class LazyEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, models.Model):
            return str(obj.pk)
        return super().default(obj)
