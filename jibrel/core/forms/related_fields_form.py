from typing import Dict

from django import forms
from django.core.exceptions import (
    FieldDoesNotExist,
    ImproperlyConfigured
)
from django.db import transaction
from kombu.utils import cached_property


class RelatedFieldsForm(forms.ModelForm):
    override_fields_options: Dict[str, Dict] = {}

    @cached_property
    def override_fields(self):
        model = self._meta.model

        def override_fields_():
            for name, field in self.fields.items():
                if '__' not in name:
                    continue

                try:
                    # ensure that it is not model field
                    # contained doubled lodash symbol in its name itself
                    model._meta.get_field(name)
                    continue
                except FieldDoesNotExist:
                    pass

                options = self.override_fields_options.get(name, {})
                rel_name, rel_field_name = name.split('__')
                rel_name = options.get('rel', rel_name)
                rel_field_name = options.get('field', rel_field_name)

                if not hasattr(model, rel_name):
                    # if relation does not exist skip it
                    # if it specified explicitly raise an error
                    if options:
                        raise ImproperlyConfigured(f'{name} is specified as override_fields_options,' +
                                                   f'but {model.__name__} has no relation with `{rel_name}` name')
                    continue

                yield name, {
                    'rel': rel_name,
                    'field': rel_field_name
                }

        return dict(override_fields_())

    def get_initial_for_field(self, field, field_name):
        if field_name in self.override_fields:
            options = self.override_fields[field_name]
            related_model = getattr(self.instance, options['rel'], None)
            return related_model and getattr(related_model, options['field'])
        return super().get_initial_for_field(field, field_name)

    @transaction.atomic
    def save(self, commit=True):
        self.instance = super(RelatedFieldsForm, self).save(commit=False)
        self.save_related_fields()
        self.instance.save(commit)
        return self.instance

    def save_related_fields(self):
        raise NotImplementedError('save_related_fields must be implemented')
