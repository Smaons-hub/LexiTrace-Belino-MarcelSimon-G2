from django import forms

from .models import VaultEntry

DUPLICATE_WORD_MESSAGE = 'This word is already in your vault.'


class VaultEntryForm(forms.ModelForm):
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

    def clean_word(self):
        word = self.cleaned_data['word'].strip()
        duplicates = VaultEntry.objects.filter(user=self.user, word__iexact=word)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(DUPLICATE_WORD_MESSAGE, code='duplicate_word')
        return word
