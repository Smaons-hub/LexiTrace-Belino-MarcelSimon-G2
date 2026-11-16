from django import forms

from .models import MAX_TAGS_PER_ENTRY, VaultEntry, VaultTag, normalise_tag_name, tag_name_problem

DUPLICATE_WORD_MESSAGE = 'This word is already in your vault.'
TOO_MANY_TAGS_MESSAGE = 'A word can have at most 5 tags.'
FOREIGN_TAG_MESSAGE = 'Choose tags from your own list.'


class VaultEntryForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=VaultTag.objects.none(),
        required=False,
        label='Tags',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        error_messages={
            'invalid_choice': FOREIGN_TAG_MESSAGE,
            'invalid_pk_value': FOREIGN_TAG_MESSAGE,
            'invalid_list': FOREIGN_TAG_MESSAGE,
        },
    )
    new_tags = forms.CharField(
        required=False,
        max_length=200,
        label='New tags',
        help_text='Separate with commas. A word can have up to 5 tags.',
        error_messages={'max_length': 'New tags must be 200 characters or fewer in total.'},
        widget=forms.TextInput(attrs={'autocomplete': 'off', 'placeholder': 'e.g. travel, exam, verbs'}),
    )
    field_order = ('word', 'meaning', 'example', 'memory_anchor', 'tags', 'new_tags', 'is_favorite')

    class Meta:
        model = VaultEntry
        fields = ('word', 'meaning', 'example', 'memory_anchor', 'is_favorite')
        labels = {
            'word': 'Word',
            'meaning': 'Meaning',
            'example': 'Example sentence',
            'memory_anchor': 'Memory anchor',
            'is_favorite': 'Mark as favorite',
        }
        help_texts = {
            'word': 'Letters, spaces, hyphens and apostrophes. At least 2 characters.',
            'meaning': 'What the word means, in your own words. Up to 1000 characters.',
            'example': 'Optional. A sentence that uses the word. Up to 500 characters.',
            'memory_anchor': 'Optional. Your own trick for remembering the word, like a picture, a rhyme or a story. Up to 500 characters.',
        }
        error_messages = {
            'word': {
                'required': 'Enter a word.',
                'max_length': 'The word must be 60 characters or fewer.',
            },
            'meaning': {
                'required': 'Enter the meaning of the word.',
            },
        }
        widgets = {
            'word': forms.TextInput(attrs={'autocomplete': 'off', 'placeholder': 'e.g. serendipity'}),
            'meaning': forms.Textarea(attrs={'rows': 4, 'maxlength': 1000}),
            'example': forms.Textarea(attrs={'rows': 3, 'maxlength': 500}),
            'memory_anchor': forms.Textarea(attrs={'rows': 3, 'maxlength': 500}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.user = user
        self.selected_tags = []
        self.new_tag_names = []
        self.user_tags = list(user.vault_tags.all())
        self.fields['tags'].queryset = user.vault_tags.all()
        if self.user_tags:
            self.fields['tags'].help_text = 'Optional. Tick the tags that fit this word.'
        else:
            self.fields['tags'].help_text = 'You have no tags yet. Add your first ones below.'
        if self.instance.pk:
            self.fields['tags'].initial = list(self.instance.tags.values_list('pk', flat=True))

    def clean_word(self):
        word = self.cleaned_data['word'].strip()
        duplicates = VaultEntry.objects.filter(user=self.user, word__iexact=word)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(DUPLICATE_WORD_MESSAGE, code='duplicate_word')
        return word

    def clean_new_tags(self):
        names = []
        seen = set()
        for raw_name in self.cleaned_data['new_tags'].split(','):
            name = normalise_tag_name(raw_name)
            key = name.lower()
            if not name or key in seen:
                continue
            problem = tag_name_problem(name)
            if problem is not None:
                raise forms.ValidationError(
                    f'"{name}" cannot be used as a tag. {problem.message}',
                    code=problem.code,
                )
            seen.add(key)
            names.append(name)
        return names

    def clean(self):
        cleaned_data = super().clean()
        if 'tags' not in cleaned_data or 'new_tags' not in cleaned_data:
            return cleaned_data
        existing = {tag.name.lower(): tag for tag in self.user_tags}
        selected = {tag.pk: tag for tag in cleaned_data['tags']}
        new_names = []
        for name in cleaned_data['new_tags']:
            tag = existing.get(name.lower())
            if tag is None:
                new_names.append(name)
            else:
                selected[tag.pk] = tag
        if len(selected) + len(new_names) > MAX_TAGS_PER_ENTRY:
            self.add_error('tags', TOO_MANY_TAGS_MESSAGE)
            return cleaned_data
        self.selected_tags = list(selected.values())
        self.new_tag_names = new_names
        return cleaned_data

    def save(self, commit=True):
        entry = super().save(commit=commit)
        if commit:
            self.save_tags(entry)
        return entry

    def save_tags(self, entry):
        tags = list(self.selected_tags)
        for name in self.new_tag_names:
            tags.append(VaultTag.get_or_create_for_user(self.user, name))
        entry.set_tags(tags)
