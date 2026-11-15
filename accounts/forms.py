from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    field_attrs = {
        'first_name': {'autocomplete': 'given-name', 'placeholder': 'Juan'},
        'last_name': {'autocomplete': 'family-name', 'placeholder': 'Dela Cruz'},
        'username': {'autocomplete': 'username', 'placeholder': 'juandc'},
        'email': {'autocomplete': 'email', 'placeholder': 'you@example.com'},
        'password1': {'autocomplete': 'new-password', 'placeholder': 'Create a password'},
        'password2': {'autocomplete': 'new-password', 'placeholder': 'Repeat your password'},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.required = True
            field.widget.attrs.pop('autofocus', None)
            field.widget.attrs.update(self.field_attrs.get(name, {}))
        self.fields['first_name'].widget.attrs['autofocus'] = True

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken.', code='duplicate_username')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.', code='duplicate_email')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.LEARNER
        if commit:
            user.save()
            self.save_m2m()
        return user
