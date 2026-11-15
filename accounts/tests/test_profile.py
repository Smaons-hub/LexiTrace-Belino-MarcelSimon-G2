import io
import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from accounts.models import User

PASSWORD = 'Lexi-Trace-Test-2026!'
TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix='lexitrace_test_media_')


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


def image_upload(name, image_format, size=(64, 64), noise=False):
    if noise:
        image = Image.frombytes('RGB', size, os.urandom(size[0] * size[1] * 3))
    else:
        image = Image.new('RGB', size, (198, 40, 40))
    buffer = io.BytesIO()
    image.save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{image_format.lower()}')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = User.objects.create_user(
            'lena', 'lena@example.com', PASSWORD, first_name='Lena', last_name='Learner'
        )
        cls.admin = User.objects.create_superuser(
            'ada', 'ada@example.com', PASSWORD, first_name='Ada', last_name='Admin'
        )

    def setUp(self):
        self.client.force_login(self.learner)
        self.edit_url = reverse('accounts:profile_edit')

    def form_data(self, **overrides):
        self.learner.refresh_from_db()
        data = {
            'first_name': self.learner.first_name,
            'last_name': self.learner.last_name,
            'email': self.learner.email,
            'contact_number': self.learner.contact_number,
            'language_level': self.learner.language_level,
        }
        if self.learner.offline_download:
            data['offline_download'] = 'on'
        data.update(overrides)
        return data

    def post_edit(self, data, **files):
        return self.client.post(self.edit_url, {**data, **files})

    def photo_path(self):
        self.learner.refresh_from_db()
        return Path(TEMP_MEDIA_ROOT) / self.learner.profile_photo.name

    def test_profile_shows_only_own_data(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'lena@example.com')
        self.assertNotContains(response, 'ada@example.com')

        self.client.force_login(self.admin)
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'ada@example.com')
        self.assertNotContains(response, 'lena@example.com')

    def test_profile_urls_take_no_user_id(self):
        for name in ('profile', 'profile_edit'):
            with self.subTest(name=name), self.assertRaises(NoReverseMatch):
                reverse(f'accounts:{name}', args=[self.admin.pk])

    def test_edit_page_shows_username_and_role_as_text_only(self):
        response = self.client.get(self.edit_url)
        self.assertContains(response, 'lena')
        self.assertNotContains(response, 'name="username"')
        self.assertNotContains(response, 'name="role"')

    def test_update_details(self):
        response = self.client.post(
            self.edit_url,
            self.form_data(first_name='Lenny', last_name='Lexicon', contact_number='0917 123 4567', language_level='advanced'),
            follow=True,
        )
        self.assertRedirects(response, reverse('accounts:profile'))
        self.assertContains(response, 'Profile updated successfully.')
        self.learner.refresh_from_db()
        self.assertEqual(
            (self.learner.first_name, self.learner.last_name, self.learner.contact_number, self.learner.language_level),
            ('Lenny', 'Lexicon', '0917 123 4567', 'advanced'),
        )

    def test_first_and_last_name_are_required(self):
        response = self.post_edit(self.form_data(first_name='', last_name=''))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Could not update your profile. Please correct the errors below.')
        self.assertEqual(set(response.context['form'].errors), {'first_name', 'last_name'})

    def test_offline_download_can_be_turned_off_and_on(self):
        data = self.form_data()
        data.pop('offline_download', None)
        self.post_edit(data)
        self.learner.refresh_from_db()
        self.assertFalse(self.learner.offline_download)

        self.post_edit(self.form_data(offline_download='on'))
        self.learner.refresh_from_db()
        self.assertTrue(self.learner.offline_download)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        response = self.post_edit(self.form_data(email='ADA@Example.com'))
        self.assertEqual(response.context['form'].errors['email'], ['An account with this email already exists.'])

    def test_own_current_email_is_accepted(self):
        response = self.post_edit(self.form_data())
        self.assertRedirects(response, reverse('accounts:profile'), fetch_redirect_response=False)

    def test_new_email_is_saved_lowercase_and_user_stays_logged_in(self):
        self.post_edit(self.form_data(email='  New.Address@Example.COM '))
        self.learner.refresh_from_db()
        self.assertEqual(self.learner.email, 'new.address@example.com')
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 200)

    def test_contact_number_rules(self):
        rejected = {
            '0917-ABC-4567': 'Use only digits, spaces, +, - and parentheses.',
            '123 456': 'Enter a contact number with 7 to 15 digits.',
            '1234567890123456': 'Enter a contact number with 7 to 15 digits.',
        }
        for value, message in rejected.items():
            with self.subTest(value=value):
                response = self.post_edit(self.form_data(contact_number=value))
                self.assertEqual(response.context['form'].errors['contact_number'], [message])

        for value in ('09171234567', '+63 917 123 4567', '(02) 8123-4567', ''):
            with self.subTest(value=value):
                response = self.post_edit(self.form_data(contact_number=value))
                self.assertEqual(response.status_code, 302)
                self.learner.refresh_from_db()
                self.assertEqual(self.learner.contact_number, value)

    def test_photo_upload_replace_and_remove(self):
        self.post_edit(self.form_data(), profile_photo=image_upload('first.png', 'PNG'))
        first = self.photo_path()
        self.assertTrue(first.exists())
        page = self.client.get(reverse('accounts:profile'))
        self.assertContains(page, self.learner.profile_photo.url)

        self.post_edit(self.form_data(), profile_photo=image_upload('second.jpg', 'JPEG'))
        second = self.photo_path()
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())

        self.post_edit(self.form_data(), profile_photo=image_upload('third.webp', 'WEBP'))
        third = self.photo_path()
        self.assertFalse(second.exists())
        self.assertTrue(third.exists())

        self.post_edit(self.form_data(remove_photo='on'))
        self.learner.refresh_from_db()
        self.assertFalse(self.learner.profile_photo)
        self.assertFalse(third.exists())

    def test_invalid_photos_are_rejected(self):
        uploads = {
            'not an image': SimpleUploadedFile('fake.png', b'just some text', content_type='image/png'),
            'over 2 MB': image_upload('big.png', 'PNG', size=(1100, 1100), noise=True),
            'gif extension': image_upload('anim.gif', 'GIF'),
            'gif renamed to png': SimpleUploadedFile(
                'disguised.png', image_upload('x.gif', 'GIF').read(), content_type='image/png'
            ),
        }
        for label, upload in uploads.items():
            with self.subTest(upload=label):
                response = self.post_edit(self.form_data(), profile_photo=upload)
                self.assertEqual(response.status_code, 200)
                self.assertIn('profile_photo', response.context['form'].errors)
                self.learner.refresh_from_db()
                self.assertFalse(self.learner.profile_photo)

    def test_protected_fields_cannot_be_changed(self):
        protected = ('username', 'role', 'is_staff', 'is_superuser', 'is_active', 'password', 'id', 'date_joined')
        self.learner.refresh_from_db()
        before = {name: getattr(self.learner, name) for name in protected}
        self.admin.refresh_from_db()
        admin_before = {f.attname: getattr(self.admin, f.attname) for f in User._meta.concrete_fields}

        response = self.post_edit({
            **self.form_data(first_name='Tamper'),
            'username': 'hacked',
            'role': 'admin',
            'is_staff': 'on',
            'is_superuser': 'on',
            'is_active': '',
            'password': 'plain-text',
            'id': self.admin.pk,
            'pk': self.admin.pk,
            'date_joined': '2000-01-01',
        })

        self.assertEqual(response.status_code, 302)
        self.learner.refresh_from_db()
        self.assertEqual(self.learner.first_name, 'Tamper')
        self.assertEqual({name: getattr(self.learner, name) for name in protected}, before)
        self.admin.refresh_from_db()
        self.assertEqual({f.attname: getattr(self.admin, f.attname) for f in User._meta.concrete_fields}, admin_before)
