from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.views.decorators.debug import sensitive_variables

from .backends import UsernameOrEmailBackend
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


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Invalid username/email or password. Please try again.',
        'inactive': 'This account is inactive.',
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        username = self.fields['username']
        username.label = 'Username or email'
        username.max_length = 254
        username.widget.attrs.update({
            'autofocus': True,
            'autocomplete': 'username',
            'maxlength': 254,
            'placeholder': 'juandc or you@example.com',
        })
        self.fields['password'].widget.attrs.update({
            'autocomplete': 'current-password',
            'placeholder': 'Your password',
        })

    @sensitive_variables()
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                if self.is_inactive_account(username, password):
                    raise forms.ValidationError(self.error_messages['inactive'], code='inactive')
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    @sensitive_variables('password')
    def is_inactive_account(self, username, password):
        user = UsernameOrEmailBackend.find_user(username)
        if user is None:
            User().set_password(password)
            return False
        return user.check_password(password) and not user.is_active
