from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.services import get_daily_review
from vault.models import VaultEntry, VaultTag


def make_user(username, role=User.Role.LEARNER):
    return User.objects.create_user(username, f'{username}@example.com', role=role)


def make_entries(user, *words, **fields):
    return [VaultEntry.objects.create(user=user, word=word, meaning=f'Meaning of {word}.', **fields) for word in words]


class DailyReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.other = make_user('omar')
        cls.newcomer = make_user('nina')
        cls.own = make_entries(cls.learner, 'apple', 'banana', 'cherry')
        make_entries(cls.other, 'zebra', 'yak')

    def review_on(self, days_ahead):
        day = timezone.localdate() + timedelta(days=days_ahead)
        with mock.patch('accounts.services.timezone.localdate', return_value=day):
            return get_daily_review(self.learner)

    def test_returns_none_without_entries(self):
        self.assertIsNone(get_daily_review(self.newcomer))

    def test_returns_only_the_users_own_entry(self):
        own_ids = {entry.pk for entry in self.own}
        for days_ahead in range(5):
            with self.subTest(days_ahead=days_ahead):
                self.assertIn(self.review_on(days_ahead).pk, own_ids)

    def test_returns_the_same_entry_twice_on_one_day(self):
        self.assertEqual(get_daily_review(self.learner).pk, get_daily_review(self.learner).pk)

    def test_changes_on_the_next_day_and_rotates_through_all_entries(self):
        picks = [self.review_on(days_ahead).pk for days_ahead in range(3)]
        self.assertNotEqual(picks[0], picks[1])
        self.assertCountEqual(picks, [entry.pk for entry in self.own])


class LearnerDashboardVaultTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = make_user('lena')
        cls.other = make_user('omar')
        cls.newcomer = make_user('nina')
        cls.admin = make_user('ada', role=User.Role.ADMIN)
        cls.entries = make_entries(cls.learner, 'apple', 'banana', 'cherry')
        cls.entries += make_entries(cls.learner, 'date', is_favorite=True)
        VaultTag.objects.create(user=cls.learner, name='food')
        VaultTag.objects.create(user=cls.learner, name='exam')
        make_entries(cls.other, 'quokka', 'xylem')
        cls.url = reverse('accounts:learner_dashboard')

    def test_counts_and_three_latest_words(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url)
        summary = response.context['vault_summary']
        self.assertEqual((summary['words'], summary['favorites'], summary['tags']), (4, 1, 2))
        self.assertEqual([entry.word for entry in summary['recent']], ['date', 'cherry', 'banana'])
        self.assertContains(response, reverse('vault:detail', args=[self.entries[-1].pk]))
        self.assertContains(response, 'id="vault-open-link" href="/vault/"')
        self.assertNotContains(response, 'href="#"')

    def test_another_learners_words_are_not_shown(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'quokka')
        self.assertNotContains(response, 'xylem')
        self.assertEqual(response.context['daily_review'].user_id, self.learner.pk)

    def test_new_learner_sees_the_empty_states(self):
        self.client.force_login(self.newcomer)
        response = self.client.get(self.url)
        self.assertIsNone(response.context['daily_review'])
        self.assertContains(response, 'id="vault-summary-empty"')
        self.assertContains(response, 'id="daily-review-add-link"')

    def test_daily_review_card_links_to_the_word(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url)
        review = response.context['daily_review']
        self.assertContains(response, f'id="daily-review-link" href="/vault/{review.pk}/"')

    def test_profile_shows_vault_counts_for_learners_only(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.context['vault_counts'], {'words': 4, 'favorites': 1, 'tags': 2})
        self.assertContains(response, 'id="profile-vault"')
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:profile'))
        self.assertIsNone(response.context['vault_counts'])
        self.assertNotContains(response, 'id="profile-vault"')


class AdminOverviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user('ada', role=User.Role.ADMIN)
        cls.busy = make_user('busy')
        cls.quiet = make_user('quiet')
        cls.idle = make_user('idle')
        make_entries(cls.busy, 'apple', 'banana', 'cherry')
        make_entries(cls.quiet, 'date')
        VaultTag.objects.create(user=cls.busy, name='food')
        VaultTag.objects.create(user=cls.quiet, name='exam')
        cls.url = reverse('accounts:admin_dashboard')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_overview_totals_match_the_database(self):
        response = self.client.get(self.url)
        overview = response.context['vault_overview']
        self.assertEqual(response.context['stats']['learners'], 3)
        self.assertEqual((overview['words'], overview['tags'], overview['words_this_week']), (4, 2, 4))
        self.assertContains(response, 'id="review-entries-btn" href="/vault/admin/entries/"')

    def test_old_words_are_left_out_of_the_weekly_total(self):
        old = timezone.now() - timedelta(days=8)
        VaultEntry.objects.filter(user=self.quiet).update(created_at=old)
        overview = self.client.get(self.url).context['vault_overview']
        self.assertEqual((overview['words'], overview['words_this_week']), (4, 3))

    def test_top_learners_are_ordered_and_skip_learners_without_words(self):
        response = self.client.get(self.url)
        top = [(learner.username, learner.word_count) for learner in response.context['vault_overview']['top_learners']]
        self.assertEqual(top, [('busy', 3), ('quiet', 1)])
        self.assertContains(response, 'data-label="Username"')
