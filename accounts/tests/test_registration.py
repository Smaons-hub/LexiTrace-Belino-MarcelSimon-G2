from django.contrib.auth.hashers import identify_hasher
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = 'Lexi-Trace-Test-2026!'


class RegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse('accounts:register')

    def valid_data(self, **overrides):
        data = {
            'first_name': 'Lena',
            'last_name': 'Learner',
            'username': 'lena',
            'email': 'lena@example.com',
            'password1': PASSWORD,
            'password2': PASSWORD,
        }
        data.update(overrides)
        return data

    def form_errors(self, response):
        return response.context['form'].errors

    def test_page_renders_without_role_field(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for name in ('first_name', 'last_name', 'username', 'email', 'password1', 'password2'):
            self.assertContains(response, f'name="{name}"')
        self.assertNotContains(response, 'name="role"')

    def test_success_creates_learner_with_hashed_password(self):
        response = self.client.post(self.url, self.valid_data(), follow=True)
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertContains(response, 'Account created successfully. You can now log in.')
        user = User.objects.get(username='lena')
        self.assertEqual(user.role, User.Role.LEARNER)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertIn(identify_hasher(user.password).algorithm, ('pbkdf2_sha256', 'argon2'))
        self.assertTrue(user.check_password(PASSWORD))

    def test_all_fields_are_required(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(self.form_errors(response)),
            {'first_name', 'last_name', 'username', 'email', 'password1', 'password2'},
        )
        self.assertContains(response, 'Please correct the errors below.')
        self.assertFalse(User.objects.exists())

    def test_invalid_email_is_rejected(self):
        response = self.client.post(self.url, self.valid_data(email='not-an-email'))
        self.assertIn('email', self.form_errors(response))
        self.assertFalse(User.objects.exists())

    def test_duplicate_username_is_rejected_case_insensitively(self):
        User.objects.create_user('Lena', 'other@example.com', PASSWORD)
        response = self.client.post(self.url, self.valid_data(username='LENA'))
        self.assertEqual(self.form_errors(response)['username'], ['This username is already taken.'])
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user('someone', 'lena@example.com', PASSWORD)
        response = self.client.post(self.url, self.valid_data(email='Lena@Example.COM'))
        self.assertEqual(self.form_errors(response)['email'], ['An account with this email already exists.'])
        self.assertEqual(User.objects.count(), 1)

    def test_email_is_stored_lowercase(self):
        self.client.post(self.url, self.valid_data(email='Lena@Example.COM'))
        self.assertEqual(User.objects.get(username='lena').email, 'lena@example.com')

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(self.url, self.valid_data(password2=PASSWORD + 'x'))
        self.assertIn('password2', self.form_errors(response))
        self.assertFalse(User.objects.exists())

    def test_weak_password_is_rejected(self):
        response = self.client.post(self.url, self.valid_data(password1='password', password2='password'))
        self.assertIn('password2', self.form_errors(response))
        self.assertFalse(User.objects.exists())

    def test_role_and_staff_flags_in_post_are_ignored(self):
        data = self.valid_data(role='admin', is_staff='on', is_superuser='on')
        self.client.post(self.url, data)
        user = User.objects.get(username='lena')
        self.assertEqual(user.role, User.Role.LEARNER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_signed_in_user_is_redirected_to_dashboard(self):
        self.client.force_login(User.objects.create_user('lena', 'lena@example.com', PASSWORD))
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)
