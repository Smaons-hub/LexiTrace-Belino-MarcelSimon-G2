from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = 'Lexi-Trace-Test-2026!'
INVALID_LOGIN = 'Invalid username/email or password. Please try again.'
LOGIN_FAILED = 'Login failed. Check your credentials and try again.'


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            'alice', 'alice@example.com', PASSWORD, first_name='Alice', last_name='Reyes'
        )
        cls.inactive = User.objects.create_user(
            'sleepy', 'sleepy@example.com', PASSWORD, is_active=False
        )
        cls.admin = User.objects.create_superuser('boss', 'boss@example.com', PASSWORD)

    def setUp(self):
        self.url = reverse('accounts:login')

    def logged_in_user_id(self, client):
        return client.session.get('_auth_user_id')

    def test_login_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username or email')

    def test_login_by_username_or_email_in_any_case(self):
        for login in ('alice', 'ALICE', 'alice@example.com', 'Alice@Example.COM'):
            with self.subTest(login=login):
                client = Client()
                response = client.post(self.url, {'username': login, 'password': PASSWORD})
                self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)
                self.assertEqual(self.logged_in_user_id(client), str(self.alice.pk))

    def test_successful_login_shows_welcome_message(self):
        response = self.client.post(self.url, {'username': 'alice', 'password': PASSWORD}, follow=True)
        self.assertContains(response, 'Welcome back, Alice Reyes!')

    def test_wrong_password_shows_error(self):
        response = self.client.post(self.url, {'username': 'alice', 'password': 'wrong-password'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, INVALID_LOGIN)
        self.assertContains(response, LOGIN_FAILED)
        self.assertIsNone(self.logged_in_user_id(self.client))

    def test_unknown_user_shows_error(self):
        response = self.client.post(self.url, {'username': 'nobody', 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, INVALID_LOGIN)
        self.assertIsNone(self.logged_in_user_id(self.client))

    def test_inactive_user_is_rejected(self):
        response = self.client.post(self.url, {'username': 'sleepy', 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This account is inactive.')
        self.assertIsNone(self.logged_in_user_id(self.client))

    def test_next_returns_user_to_requested_page(self):
        response = self.client.post(
            f'{self.url}?next=/profile/',
            {'username': 'alice', 'password': PASSWORD, 'next': '/profile/'},
        )
        self.assertRedirects(response, '/profile/', fetch_redirect_response=False)

    def test_unsafe_next_is_ignored(self):
        response = self.client.post(
            self.url,
            {'username': 'alice', 'password': PASSWORD, 'next': 'https://example.com/steal'},
        )
        self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)

    def test_signed_in_user_is_redirected_away_from_login(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)

    def test_django_admin_login_with_username_still_works(self):
        response = self.client.post(
            '/admin/login/?next=/admin/',
            {'username': 'boss', 'password': PASSWORD, 'next': '/admin/'},
        )
        self.assertRedirects(response, '/admin/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/admin/').status_code, 200)


class LogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('alice', 'alice@example.com', PASSWORD)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('accounts:logout')

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_post_ends_session_and_shows_message(self):
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertContains(response, 'You have been logged out.')
        self.assertNotIn('_auth_user_id', self.client.session)
        dashboard = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard.status_code, 302)


class LoginRequiredTests(TestCase):
    def test_anonymous_visitors_are_redirected_to_login_with_next(self):
        login_url = reverse('accounts:login')
        for name in ('dashboard', 'learner_dashboard', 'admin_dashboard', 'profile', 'profile_edit'):
            with self.subTest(page=name):
                url = reverse(f'accounts:{name}')
                response = self.client.get(url)
                self.assertRedirects(response, f'{login_url}?next={url}', fetch_redirect_response=False)
