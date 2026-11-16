import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator, RegexValidator
from django.db import IntegrityError, models, transaction
from django.db.models.functions import Lower

# Create your models here.

WORD_MIN_LENGTH = 2

word_characters_validator = RegexValidator(
    regex=r"^(?:\s*|(?=.*[^\W\d_])(?:[^\W\d_]|[ '\-])+)$",
    message='Use only letters, spaces, hyphens and apostrophes.',
    code='invalid_word',
)
word_min_length_validator = MinLengthValidator(
    WORD_MIN_LENGTH,
    message='The word must be at least 2 characters long.',
)

TAG_MIN_LENGTH = 2
TAG_MAX_LENGTH = 30
MAX_TAGS_PER_ENTRY = 5
TAG_UNIQUE_CONSTRAINT = 'vault_tag_unique_name_per_user'
TAG_BLANK_MESSAGE = 'Enter a tag name.'
TAG_CHARACTERS_MESSAGE = 'Use only letters, numbers, spaces and hyphens.'
TAG_CONTENT_MESSAGE = 'A tag needs at least one letter or number.'
TAG_MIN_LENGTH_MESSAGE = 'A tag must be at least 2 characters long.'
TAG_MAX_LENGTH_MESSAGE = 'A tag must be 30 characters or fewer.'
TAG_CHARACTERS_PATTERN = re.compile(r'(?:[^\W_]|[ \-])+')
TAG_CONTENT_PATTERN = re.compile(r'[^\W_]')


def normalise_tag_name(name):
    return ' '.join((name or '').split())


def tag_name_problem(name):
    name = normalise_tag_name(name)
    if not name:
        return ValidationError(TAG_BLANK_MESSAGE, code='blank')
    if not TAG_CHARACTERS_PATTERN.fullmatch(name):
        return ValidationError(TAG_CHARACTERS_MESSAGE, code='invalid_tag')
    if not TAG_CONTENT_PATTERN.search(name):
        return ValidationError(TAG_CONTENT_MESSAGE, code='empty_tag')
    if len(name) < TAG_MIN_LENGTH:
        return ValidationError(TAG_MIN_LENGTH_MESSAGE, code='min_length')
    if len(name) > TAG_MAX_LENGTH:
        return ValidationError(TAG_MAX_LENGTH_MESSAGE, code='max_length')
    return None


def validate_tag_name(value):
    if len(value) > TAG_MAX_LENGTH:
        return
    problem = tag_name_problem(value)
    if problem is not None:
        raise problem


class VaultTag(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vault_tags',
    )
    name = models.CharField(
        max_length=TAG_MAX_LENGTH,
        validators=[validate_tag_name],
        error_messages={
            'blank': TAG_BLANK_MESSAGE,
            'max_length': TAG_MAX_LENGTH_MESSAGE,
        },
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                'user',
                Lower('name'),
                name=TAG_UNIQUE_CONSTRAINT,
                violation_error_message='You already have a tag with this name.',
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.name = normalise_tag_name(self.name)

    @classmethod
    def get_or_create_for_user(cls, user, name):
        name = normalise_tag_name(name)
        tag = cls.objects.filter(user=user, name__iexact=name).first()
        if tag is not None:
            return tag
        try:
            with transaction.atomic():
                return cls.objects.create(user=user, name=name)
        except IntegrityError as error:
            if TAG_UNIQUE_CONSTRAINT not in str(error):
                raise
            return cls.objects.get(user=user, name__iexact=name)


class VaultEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vault_entries',
    )
    word = models.CharField(
        max_length=60,
        validators=[word_characters_validator, word_min_length_validator],
        error_messages={
            'blank': 'Enter a word.',
            'max_length': 'The word must be 60 characters or fewer.',
        },
    )
    meaning = models.TextField(
        validators=[MaxLengthValidator(1000, message='The meaning must be 1000 characters or fewer.')],
    )
    example = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(500, message='The example must be 500 characters or fewer.')],
    )
    memory_anchor = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(500, message='The memory anchor must be 500 characters or fewer.')],
    )
    is_favorite = models.BooleanField(default=False)
    tags = models.ManyToManyField(VaultTag, blank=True, related_name='entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = 'vault entries'
        constraints = [
            models.UniqueConstraint(
                'user',
                Lower('word'),
                name='vault_entry_unique_word_per_user',
                violation_error_message='This word is already in your vault.',
            ),
        ]
        indexes = [
            models.Index(fields=['user', '-created_at'], name='vault_entry_user_created_idx'),
        ]

    def __str__(self):
        return self.word

    def clean(self):
        super().clean()
        original = self.word or ''
        self.word = original.strip()
        if self.word == original:
            return
        if not self.word:
            raise ValidationError({'word': 'Enter a word.'}, code='blank_word')
        if len(self.word) < WORD_MIN_LENGTH:
            raise ValidationError({'word': word_min_length_validator.message}, code='min_length')

    def set_tags(self, tags):
        tags = list(tags)
        if any(tag.user_id != self.user_id for tag in tags):
            raise ValidationError({'tags': 'You can only use your own tags.'}, code='foreign_tag')
        self.tags.set(tags)
