from django import forms

from django_banking.contrib.card.backend.foloosi.models import FoloosiCharge
from jibrel.payments.tasks import foloosi_update


class FoloosiFixMatchForm(forms.ModelForm):
    class Meta:
        model = FoloosiCharge
        fields = ('charge_id',)

    def save(self, *args, **kwargs):
        foloosi_update.delay(deposit_id=self.instance.operation.pk)
        return self.instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'charge_id' in self.fields:
            self.fields['charge_id'].required = True
