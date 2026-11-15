import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import FileExtensionValidator
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


class ProfileForm(forms.ModelForm):
    CONTACT_PATTERN = re.compile(r'^[0-9+\-()\s]+$')
    MAX_PHOTO_BYTES = 2 * 1024 * 1024
    PHOTO_FORMATS = {'JPEG', 'PNG', 'WEBP'}

    remove_photo = forms.BooleanField(required=False, label='Remove current photo')

    field_order = (
        'first_name',
        'last_name',
        'email',
        'contact_number',
        'profile_photo',
        'remove_photo',
        'language_level',
        'offline_download',
    )

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'contact_number',
            'profile_photo',
            'language_level',
            'offline_download',
        )
        widgets = {
            'profile_photo': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }
        help_texts = {
            'contact_number': 'Optional. Digits, spaces, +, - and parentheses, with 7 to 15 digits.',
            'profile_photo': 'Optional. JPEG, PNG or WebP, up to 2 MB.',
        }

    field_attrs = {
        'first_name': {'autocomplete': 'given-name'},
        'last_name': {'autocomplete': 'family-name'},
        'email': {'autocomplete': 'email'},
        'contact_number': {'autocomplete': 'tel', 'inputmode': 'tel', 'placeholder': '0917 123 4567'},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.previous_photo_name = self.instance.profile_photo.name or ''
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['profile_photo'].validators.append(
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])
        )
        for name, attrs in self.field_attrs.items():
            self.fields[name].widget.attrs.update(attrs)
        if not self.previous_photo_name:
            del self.fields['remove_photo']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        taken = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists()
        if taken:
            raise forms.ValidationError('An account with this email already exists.', code='duplicate_email')
        return email

    def clean_contact_number(self):
        number = self.cleaned_data.get('contact_number', '').strip()
        if not number:
            return ''
        if not self.CONTACT_PATTERN.match(number):
            raise forms.ValidationError(
                'Use only digits, spaces, +, - and parentheses.',
                code='invalid_characters',
            )
        digits = sum(char.isdigit() for char in number)
        if not 7 <= digits <= 15:
            raise forms.ValidationError(
                'Enter a contact number with 7 to 15 digits.',
                code='invalid_length',
            )
        return number

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if not isinstance(photo, UploadedFile):
            return photo
        if photo.size > self.MAX_PHOTO_BYTES:
            raise forms.ValidationError('The photo must be 2 MB or smaller.', code='file_too_large')
        image = getattr(photo, 'image', None)
        if image is None or image.format not in self.PHOTO_FORMATS:
            raise forms.ValidationError('Upload a JPEG, PNG or WebP image.', code='invalid_format')
        return photo

    def has_new_photo(self):
        return isinstance(self.cleaned_data.get('profile_photo'), UploadedFile)

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('remove_photo') and not self.has_new_photo():
            user.profile_photo = None
        if commit:
            user.save()
            self.save_m2m()
            self.delete_replaced_photo(user)
        return user

    def delete_replaced_photo(self, user):
        current = user.profile_photo.name or ''
        if self.previous_photo_name and self.previous_photo_name != current:
            storage = User._meta.get_field('profile_photo').storage
            storage.delete(self.previous_photo_name)
