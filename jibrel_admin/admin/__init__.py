from django.contrib import admin
from django_banking.models import Fee


admin.site.unregister([Fee])
