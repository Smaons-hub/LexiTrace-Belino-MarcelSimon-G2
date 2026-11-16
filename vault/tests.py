from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import User

from .forms import DUPLICATE_WORD_MESSAGE, FOREIGN_TAG_MESSAGE, TOO_MANY_TAGS_MESSAGE, VaultEntryForm
from .models import (
    TAG_BLANK_MESSAGE,
    TAG_CHARACTERS_MESSAGE,
    TAG_MAX_LENGTH_MESSAGE,
    TAG_MIN_LENGTH_MESSAGE,
    VaultEntry,
    VaultTag,
    normalise_tag_name,
    tag_name_problem,
)

LOGIN_URL = reverse('accounts:login')
LIST_URL = reverse('vault:list')


def make_user(username, role=User.Role.LEARNER):
    return User.objects.create_user(username, f'{username}@example.com', role=role)


def make_entry(user, word, **fields):
    fields.setdefault('meaning', f'Meaning of {word}.')
    return VaultEntry.objects.create(user=user, word=word, **fields)


def tag_names(entry):
    return sorted(entry.tags.values_list('name', flat=True))


class TagNameRuleTests(SimpleTestCase):
    def test_blank_name_is_rejected(self):
        self.assertEqual(tag_name_problem('').message, TAG_BLANK_MESSAGE)
        self.assertEqual(tag_name_problem('   ').message, TAG_BLANK_MESSAGE)

    def test_symbols_are_rejected(self):
        self.assertEqual(tag_name_problem('c++').message, TAG_CHARACTERS_MESSAGE)

    def test_one_character_is_too_short(self):
        self.assertEqual(tag_name_problem('a').message, TAG_MIN_LENGTH_MESSAGE)
        self.assertIsNone(tag_name_problem('ab'))

    def test_thirty_one_characters_is_too_long(self):
        self.assertEqual(tag_name_problem('a' * 31).message, TAG_MAX_LENGTH_MESSAGE)
        self.assertIsNone(tag_name_problem('a' * 30))

    def test_runs_of_spaces_are_collapsed(self):
        self.assertEqual(normalise_tag_name('  my \t  tag '), 'my tag')

    def test_accents_digits_and_hyphens_are_allowed(self):
        for name in ('Été 2026', 'phrasal-verbs', 'B2'):
            with self.subTest(name=name):
                self.assertIsNone(tag_name_problem(name))


class VaultModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.other = make_user('omar')
        cls.entry = make_entry(cls.learner, 'bank')
        cls.tag = VaultTag.objects.create(user=cls.learner, name='Travel')

    def test_word_is_unique_per_user_ignoring_case(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_entry(self.learner, 'BANK')
        self.assertEqual(self.learner.vault_entries.count(), 1)

    def test_same_word_is_allowed_for_another_user(self):
        make_entry(self.other, 'Bank')
        self.assertEqual(VaultEntry.objects.filter(word__iexact='bank').count(), 2)

    def test_invalid_tag_names_give_exactly_one_error(self):
        for name in ('', 'c++', 'a', 'a' * 31):
            with self.subTest(name=name):
                with self.assertRaises(ValidationError) as raised:
                    VaultTag(user=self.learner, name=name).full_clean()
                self.assertEqual(list(raised.exception.message_dict), ['name'])
                self.assertEqual(len(raised.exception.message_dict['name']), 1)

    def test_clean_collapses_spaces_in_the_name(self):
        tag = VaultTag(user=self.learner, name='  exam    prep ')
        tag.full_clean()
        self.assertEqual(tag.name, 'exam prep')

    def test_tag_name_is_unique_per_user_ignoring_case(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            VaultTag.objects.create(user=self.learner, name='TRAVEL')
        VaultTag.objects.create(user=self.other, name='travel')
        self.assertEqual(VaultTag.objects.filter(name__iexact='travel').count(), 2)

    def test_set_tags_rejects_another_users_tag(self):
        foreign = VaultTag.objects.create(user=self.other, name='secret')
        with self.assertRaises(ValidationError):
            self.entry.set_tags([self.tag, foreign])
        self.assertEqual(self.entry.tags.count(), 0)

    def test_get_or_create_for_user_reuses_an_existing_tag(self):
        found = VaultTag.get_or_create_for_user(self.learner, '  tRaVeL ')
        created = VaultTag.get_or_create_for_user(self.learner, 'my   tag')
        self.assertEqual(found.pk, self.tag.pk)
        self.assertEqual(created.name, 'my tag')
        self.assertEqual(self.learner.vault_tags.count(), 2)


class VaultEntryFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.other = make_user('omar')
        cls.entry = make_entry(cls.learner, 'bank')
        cls.tag = VaultTag.objects.create(user=cls.learner, name='Travel')
        cls.foreign_tag = VaultTag.objects.create(user=cls.other, name='secret')

    def form(self, **data):
        data.setdefault('word', 'river')
        data.setdefault('meaning', 'A stream of water.')
        return VaultEntryForm(data, user=self.learner)

    def test_duplicate_word_shows_one_clear_message(self):
        form = self.form(word='  BANK ')
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['word'], [DUPLICATE_WORD_MESSAGE])

    def test_new_tags_are_split_trimmed_and_deduplicated(self):
        form = self.form(new_tags=' verbs , Verbs,, B2   level ,')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['new_tags'], ['verbs', 'B2 level'])

    def test_invalid_new_tag_gives_one_error_naming_it(self):
        form = self.form(new_tags='verbs, c++')
        self.assertFalse(form.is_valid())
        self.assertEqual(list(form.errors), ['new_tags'])
        self.assertEqual(len(form.errors['new_tags']), 1)
        self.assertIn('"c++"', form.errors['new_tags'][0])

    def test_new_tag_reuses_an_existing_tag_ignoring_case(self):
        form = self.form(new_tags='TRAVEL')
        self.assertTrue(form.is_valid(), form.errors)
        entry = form.save()
        self.assertEqual(list(entry.tags.all()), [self.tag])
        self.assertEqual(self.learner.vault_tags.count(), 1)

    def test_save_sets_selected_tags_and_creates_missing_ones(self):
        form = self.form(tags=[self.tag.pk], new_tags='exam')
        self.assertTrue(form.is_valid(), form.errors)
        entry = form.save()
        self.assertEqual(tag_names(entry), ['Travel', 'exam'])
        self.assertEqual(self.learner.vault_tags.count(), 2)

    def test_more_than_five_tags_is_rejected(self):
        form = self.form(tags=[self.tag.pk], new_tags='one1, two2, three3, four4, five5')
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['tags'], [TOO_MANY_TAGS_MESSAGE])

    def test_another_users_tag_id_is_rejected(self):
        form = self.form(tags=[self.foreign_tag.pk])
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['tags'], [FOREIGN_TAG_MESSAGE])


class VaultAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.other = make_user('omar')
        cls.admin = make_user('ada', role=User.Role.ADMIN)
        cls.entry = make_entry(cls.learner, 'bank')
        cls.tag = VaultTag.objects.create(user=cls.learner, name='Travel')
        cls.favorite_url = reverse('vault:toggle_favorite', args=[cls.entry.pk])
        cls.delete_url = reverse('vault:delete', args=[cls.entry.pk])
        cls.tag_delete_url = reverse('vault:tag_delete', args=[cls.tag.pk])
        cls.admin_delete_url = reverse('vault:admin_entry_delete', args=[cls.entry.pk])
        cls.learner_urls = [
            LIST_URL,
            reverse('vault:create'),
            reverse('vault:detail', args=[cls.entry.pk]),
            reverse('vault:update', args=[cls.entry.pk]),
            cls.delete_url,
            reverse('vault:tag_list'),
            cls.tag_delete_url,
        ]
        cls.admin_urls = [
            reverse('vault:admin_entry_list'),
            reverse('vault:admin_entry_detail', args=[cls.entry.pk]),
            cls.admin_delete_url,
        ]

    def assert_unchanged(self):
        self.entry.refresh_from_db()
        self.assertFalse(self.entry.is_favorite)
        self.assertTrue(VaultTag.objects.filter(pk=self.tag.pk).exists())

    def test_anonymous_is_redirected_to_login_on_every_vault_url(self):
        for url in self.learner_urls + self.admin_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith(f'{LOGIN_URL}?next='))
        response = self.client.post(self.favorite_url)
        self.assertTrue(response['Location'].startswith(f'{LOGIN_URL}?next='))
        self.assert_unchanged()

    def test_admin_gets_403_on_learner_vault_urls(self):
        self.client.force_login(self.admin)
        for url in self.learner_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.favorite_url).status_code, 403)
        self.assertEqual(self.client.post(self.delete_url).status_code, 403)
        self.assert_unchanged()

    def test_learner_gets_403_on_moderation_urls(self):
        self.client.force_login(self.learner)
        for url in self.admin_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.admin_delete_url).status_code, 403)
        self.assert_unchanged()

    def test_another_users_entry_urls_give_404(self):
        self.client.force_login(self.other)
        for url in self.learner_urls[2:5]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(self.favorite_url).status_code, 404)
        self.assertEqual(self.client.post(self.delete_url).status_code, 404)
        self.assert_unchanged()

    def test_another_users_tag_delete_gives_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.tag_delete_url).status_code, 404)
        self.assertEqual(self.client.post(self.tag_delete_url).status_code, 404)
        self.assert_unchanged()

    def test_unknown_moderation_ids_give_404(self):
        self.client.force_login(self.admin)
        missing = self.entry.pk + 1000
        self.assertEqual(self.client.get(reverse('vault:admin_entry_detail', args=[missing])).status_code, 404)
        self.assertEqual(self.client.get(reverse('vault:admin_entry_delete', args=[missing])).status_code, 404)
        self.assertEqual(self.client.post(reverse('vault:admin_entry_delete', args=[missing])).status_code, 404)

    def test_get_never_changes_data_on_delete_and_favorite_urls(self):
        self.client.force_login(self.learner)
        self.assertEqual(self.client.get(self.delete_url).status_code, 200)
        self.assertEqual(self.client.get(self.tag_delete_url).status_code, 200)
        self.assertEqual(self.client.get(self.favorite_url).status_code, 405)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.admin_delete_url).status_code, 200)
        self.assert_unchanged()

    def test_post_without_csrf_token_is_refused(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.learner)
        for url in (self.delete_url, self.favorite_url, self.tag_delete_url):
            with self.subTest(url=url):
                self.assertEqual(strict.post(url).status_code, 403)
        strict.force_login(self.admin)
        self.assertEqual(strict.post(self.admin_delete_url).status_code, 403)
        self.assert_unchanged()


class VaultEntryCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.tag = VaultTag.objects.create(user=cls.learner, name='Travel')
        cls.entry = make_entry(cls.learner, 'bank')
        cls.entry.set_tags([cls.tag])

    def setUp(self):
        self.client.force_login(self.learner)

    def test_create_entry_with_selected_and_new_tags(self):
        response = self.client.post(reverse('vault:create'), {
            'word': 'river',
            'meaning': 'A stream of water.',
            'example': 'We sat by the river.',
            'tags': [self.tag.pk],
            'new_tags': 'nature',
        })
        entry = VaultEntry.objects.get(user=self.learner, word='river')
        self.assertRedirects(response, reverse('vault:detail', args=[entry.pk]), fetch_redirect_response=False)
        self.assertEqual(entry.example, 'We sat by the river.')
        self.assertEqual(tag_names(entry), ['Travel', 'nature'])

    def test_create_rejects_a_duplicate_word(self):
        response = self.client.post(reverse('vault:create'), {'word': 'Bank', 'meaning': 'Again.'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].errors['word'], [DUPLICATE_WORD_MESSAGE])
        self.assertEqual(self.learner.vault_entries.count(), 1)

    def test_edit_entry_changes_fields_and_tags(self):
        response = self.client.post(reverse('vault:update', args=[self.entry.pk]), {
            'word': 'bank',
            'meaning': 'The side of a river.',
            'new_tags': 'geography',
        })
        self.assertRedirects(response, reverse('vault:detail', args=[self.entry.pk]), fetch_redirect_response=False)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.meaning, 'The side of a river.')
        self.assertEqual(tag_names(self.entry), ['geography'])

    def test_delete_entry_on_post_keeps_its_tags(self):
        response = self.client.post(reverse('vault:delete', args=[self.entry.pk]))
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)
        self.assertFalse(VaultEntry.objects.filter(pk=self.entry.pk).exists())
        self.assertTrue(VaultTag.objects.filter(pk=self.tag.pk).exists())


class FavoriteToggleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.entry = make_entry(cls.learner, 'bank')
        cls.url = reverse('vault:toggle_favorite', args=[cls.entry.pk])

    def setUp(self):
        self.client.force_login(self.learner)

    def test_toggle_flips_the_flag_and_returns_to_a_safe_next(self):
        target = f'{LIST_URL}?q=bank&sort=az'
        response = self.client.post(self.url, {'next': target})
        self.assertRedirects(response, target, fetch_redirect_response=False)
        self.entry.refresh_from_db()
        self.assertTrue(self.entry.is_favorite)
        self.client.post(self.url, {'next': target})
        self.entry.refresh_from_db()
        self.assertFalse(self.entry.is_favorite)

    def test_unsafe_or_missing_next_falls_back_to_the_list(self):
        unsafe = ('https://evil.example/x', '//evil.example/x', '/\\evil.example', 'javascript:alert(1)', 'vault/', '')
        for value in unsafe:
            with self.subTest(next=value):
                response = self.client.post(self.url, {'next': value})
                self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)
        response = self.client.post(self.url)
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)


class VaultListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.other = make_user('omar')
        cls.newcomer = make_user('nina')
        cls.food = VaultTag.objects.create(user=cls.learner, name='food')
        cls.foreign_tag = VaultTag.objects.create(user=cls.other, name='secret')
        make_entry(cls.learner, 'apple', meaning='A round fruit.')
        make_entry(cls.learner, 'Banana', meaning='A long yellow fruit.', example='Monkeys love it.')
        make_entry(cls.learner, 'cherry', meaning='Small and red.', memory_anchor='Think of a zebra crossing.', is_favorite=True)
        date = make_entry(cls.learner, 'date', meaning='Sweet orchard fruit.', is_favorite=True)
        elder = make_entry(cls.learner, 'elder', meaning='A shrub.')
        date.set_tags([cls.food])
        elder.set_tags([cls.food])
        make_entry(cls.other, 'zebra', meaning='A striped fruit thief.', example='Monkeys in the orchard.', is_favorite=True)
        make_entry(cls.other, 'apple', meaning='Private fruit note.')
        cls.own_words = ['apple', 'Banana', 'cherry', 'date', 'elder']

    def setUp(self):
        self.client.force_login(self.learner)

    def listed(self, **params):
        return [entry.word for entry in self.client.get(LIST_URL, params).context['page'].object_list]

    def test_search_matches_word_meaning_example_and_anchor(self):
        self.assertEqual(self.listed(q='BANAN'), ['Banana'])
        self.assertEqual(self.listed(q='orchard'), ['date'])
        self.assertEqual(self.listed(q='monkeys'), ['Banana'])
        self.assertEqual(self.listed(q='zebra'), ['cherry'])

    def test_blank_query_is_ignored_and_long_query_is_capped(self):
        self.assertCountEqual(self.listed(q='   '), self.own_words)
        response = self.client.get(LIST_URL, {'q': 'x' * 150})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['query']), 100)

    def test_favorites_filter_and_invalid_value(self):
        self.assertCountEqual(self.listed(fav='1'), ['cherry', 'date'])
        for value in ('yes', 'true', '0', ''):
            with self.subTest(fav=value):
                self.assertCountEqual(self.listed(fav=value), self.own_words)

    def test_search_favorites_and_tag_combine(self):
        self.assertCountEqual(self.listed(q='fruit'), ['apple', 'Banana', 'date'])
        self.assertEqual(self.listed(q='fruit', fav='1'), ['date'])
        self.assertEqual(self.listed(q='shrub', tag=self.food.pk), ['elder'])
        self.assertEqual(self.listed(q='fruit', fav='1', tag=self.food.pk), ['date'])

    def test_sort_orders_and_invalid_sort_falls_back_to_newest(self):
        newest = self.own_words[::-1]
        self.assertEqual(self.listed(), newest)
        self.assertEqual(self.listed(sort='oldest'), self.own_words)
        self.assertEqual(self.listed(sort='az'), ['apple', 'Banana', 'cherry', 'date', 'elder'])
        self.assertEqual(self.listed(sort='nonsense'), newest)

    def test_tag_filter_ignores_bad_missing_and_foreign_ids(self):
        self.assertCountEqual(self.listed(tag=self.food.pk), ['date', 'elder'])
        for value in ('abc', '', '-1', '999999999', str(self.foreign_tag.pk)):
            with self.subTest(tag=value):
                self.assertCountEqual(self.listed(tag=value), self.own_words)

    def test_no_results_state_differs_from_the_empty_vault(self):
        response = self.client.get(LIST_URL, {'q': 'zzz-nothing'})
        self.assertContains(response, 'id="vault-no-results"')
        self.assertNotContains(response, 'id="vault-empty"')
        self.client.force_login(self.newcomer)
        response = self.client.get(LIST_URL, {'q': 'zzz-nothing'})
        self.assertContains(response, 'id="vault-empty"')
        self.assertNotContains(response, 'id="vault-no-results"')

    def test_another_users_entries_are_never_listed(self):
        for params in ({}, {'q': 'fruit'}, {'q': 'zebra'}, {'fav': '1'}, {'sort': 'az'}, {'tag': self.foreign_tag.pk}):
            with self.subTest(params=params):
                page = self.client.get(LIST_URL, params).context['page']
                self.assertTrue(all(entry.user_id == self.learner.pk for entry in page.object_list))

    def test_pagination_keeps_search_favorites_tag_and_sort(self):
        entries = VaultEntry.objects.bulk_create([
            VaultEntry(user=self.learner, word=f'bulk{letter}', meaning='Bulk.', is_favorite=True)
            for letter in 'abcdefghijkl'
        ])
        VaultEntry.tags.through.objects.bulk_create([
            VaultEntry.tags.through(vaultentry=entry, vaulttag=self.food) for entry in entries
        ])
        params = {'q': 'bulk', 'fav': '1', 'tag': self.food.pk, 'sort': 'az'}
        response = self.client.get(LIST_URL, params)
        self.assertEqual(len(response.context['page'].object_list), 10)
        self.assertContains(response, f'href="?page=2&amp;q=bulk&amp;fav=1&amp;tag={self.food.pk}&amp;sort=az"')
        self.assertEqual(self.listed(page=2, **params), ['bulkk', 'bulkl'])


class TagManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.other = make_user('omar')
        cls.tag = VaultTag.objects.create(user=cls.learner, name='Travel')
        cls.unused = VaultTag.objects.create(user=cls.learner, name='unused')
        VaultTag.objects.create(user=cls.other, name='secret')
        cls.entry = make_entry(cls.learner, 'bank')
        cls.entry.set_tags([cls.tag])

    def setUp(self):
        self.client.force_login(self.learner)

    def test_tag_list_shows_only_own_tags_with_counts(self):
        response = self.client.get(reverse('vault:tag_list'))
        counts = {tag.name: tag.entry_count for tag in response.context['tags']}
        self.assertEqual(counts, {'Travel': 1, 'unused': 0})
        self.assertNotContains(response, 'secret')

    def test_tag_delete_keeps_the_entries(self):
        response = self.client.post(reverse('vault:tag_delete', args=[self.tag.pk]), follow=True)
        self.assertRedirects(response, reverse('vault:tag_list'))
        self.assertContains(response, 'Tag &quot;Travel&quot; was deleted. Your words were kept.')
        self.assertFalse(VaultTag.objects.filter(pk=self.tag.pk).exists())
        self.assertTrue(VaultEntry.objects.filter(pk=self.entry.pk).exists())
        self.assertEqual(self.entry.tags.count(), 0)


class ModerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user('ada', role=User.Role.ADMIN)
        cls.alice = make_user('alice')
        cls.bruno = make_user('bruno')
        cls.tag = VaultTag.objects.create(user=cls.alice, name='Travel')
        cls.entry = make_entry(cls.alice, 'harbor', example='Ships rest in the harbor.', is_favorite=True)
        cls.entry.set_tags([cls.tag])
        make_entry(cls.bruno, 'meadow')
        cls.list_url = reverse('vault:admin_entry_list')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_list_shows_owners_and_paginates_at_ten(self):
        VaultEntry.objects.bulk_create([
            VaultEntry(user=self.bruno, word=f'bulk{letter}', meaning='Bulk.') for letter in 'abcdefghijkl'
        ])
        response = self.client.get(self.list_url)
        page = response.context['page']
        self.assertEqual(len(page.object_list), 10)
        self.assertEqual(page.paginator.count, 14)
        self.assertContains(response, 'data-label="Owner">bruno</td>')
        self.assertContains(response, 'href="?page=2"')

    def test_search_by_word_and_by_owner(self):
        by_word = self.client.get(self.list_url, {'q': 'HARB'}).context['page']
        self.assertEqual([entry.word for entry in by_word.object_list], ['harbor'])
        by_owner = self.client.get(self.list_url, {'q': 'brun'}).context['page']
        self.assertEqual([entry.word for entry in by_owner.object_list], ['meadow'])
        blank = self.client.get(self.list_url, {'q': '  '}).context['page']
        self.assertEqual(blank.paginator.count, 2)

    def test_detail_is_read_only(self):
        response = self.client.get(reverse('vault:admin_entry_detail', args=[self.entry.pk]))
        self.assertContains(response, 'alice')
        self.assertContains(response, 'Ships rest in the harbor.')
        self.assertContains(response, '<li class="tag-chip">Travel</li>')
        self.assertContains(response, reverse('vault:admin_entry_delete', args=[self.entry.pk]))
        self.assertNotContains(response, reverse('vault:update', args=[self.entry.pk]))
        self.assertNotContains(response, reverse('vault:toggle_favorite', args=[self.entry.pk]))

    def test_delete_removes_the_entry_and_keeps_the_tags(self):
        response = self.client.post(reverse('vault:admin_entry_delete', args=[self.entry.pk]), follow=True)
        self.assertRedirects(response, self.list_url)
        self.assertContains(response, 'Entry &quot;harbor&quot; by alice was removed.')
        self.assertFalse(VaultEntry.objects.filter(pk=self.entry.pk).exists())
        self.assertTrue(VaultTag.objects.filter(pk=self.tag.pk).exists())
