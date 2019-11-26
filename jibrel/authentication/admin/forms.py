from django import forms
from django.contrib.auth.forms import UserCreationForm


class CustomerUserCreationForm(UserCreationForm):
    user_email = forms.EmailField(
        label='Email',
        required=True,
        help_text='Enter a unique value.'
    )

    def save(self, commit=True):
        user = super(CustomerUserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data['user_email']
        if commit:
            user.save()
        return user
