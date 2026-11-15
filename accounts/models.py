from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CustomUserManager(UserManager):
    """User manager whose superusers default to the Admin role."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        LEARNER = 'learner', 'Learner'
        ADMIN = 'admin', 'Admin'

    class LanguageLevel(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'

    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.LEARNER)
    contact_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    language_level = models.CharField(
        max_length=20,
        choices=LanguageLevel.choices,
        default=LanguageLevel.INTERMEDIATE,
    )
    offline_download = models.BooleanField(
        'Download offline dictionary data',
        default=True,
    )

    objects = CustomUserManager()

    def __str__(self):
        return self.username

    @property
    def display_name(self):
        return self.get_full_name() or self.username
