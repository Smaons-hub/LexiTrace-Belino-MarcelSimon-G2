from django.test import TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = 'Lexi-Trace-Test-2026!'


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = User.objects.create_user('lena', 'lena@example.com', PASSWORD)
        cls.admin = User.objects.create_superuser('ada', 'ada@example.com', PASSWORD)
        cls.admin_without_staff = User.objects.create_user(
            'nora', 'nora@example.com', PASSWORD, role=User.Role.ADMIN
        )

    def login_and_follow(self, username):
        return self.client.post(
            reverse('accounts:login'),
            {'username': username, 'password': PASSWORD},
            follow=True,
        )

    def test_learner_lands_on_learner_dashboard(self):
        response = self.login_and_follow('lena')
        self.assertEqual(response.redirect_chain[-1][0], reverse('accounts:learner_dashboard'))
        self.assertTemplateUsed(response, 'accounts/learner_dashboard.html')

    def test_admin_lands_on_admin_dashboard(self):
        response = self.login_and_follow('ada')
        self.assertEqual(response.redirect_chain[-1][0], reverse('accounts:admin_dashboard'))
        self.assertTemplateUsed(response, 'accounts/admin_dashboard.html')

    def test_learner_cannot_open_admin_dashboard(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertContains(response, 'This page is off-limits', status_code=403)

    def test_admin_cannot_open_learner_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:learner_dashboard'))
        self.assertContains(response, 'This page is off-limits', status_code=403)

    def test_manage_users_button_only_for_staff_admins(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('accounts:admin_dashboard')), 'id="manage-users-btn"')

        self.client.force_login(self.admin_without_staff)
        self.assertNotContains(self.client.get(reverse('accounts:admin_dashboard')), 'id="manage-users-btn"')

        self.client.force_login(self.learner)
        self.assertNotContains(self.client.get(reverse('accounts:learner_dashboard')), 'id="manage-users-btn"')

    def test_admin_dashboard_shows_stats_and_recent_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(
            response.context['stats'],
            {'total': 3, 'learners': 1, 'admins': 2, 'new_this_week': 3},
        )
        self.assertContains(response, 'id="recent-users"')
        for email in ('lena@example.com', 'ada@example.com', 'nora@example.com'):
            self.assertContains(response, email)
        self.assertNotContains(response, 'Coming soon')

    def test_learner_dashboard_has_no_admin_content(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse('accounts:learner_dashboard'))
        self.assertNotContains(response, 'id="admin-stats"')
        self.assertNotContains(response, 'id="recent-users"')
        self.assertContains(response, 'Coming soon', count=1)
