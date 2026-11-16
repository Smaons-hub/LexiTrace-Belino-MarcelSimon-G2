# LexiTrace

LexiTrace is a context-aware vocabulary lookup system for language learners. The long-term goal is to read the sentence a word appears in and give the definition that fits, instead of listing every meaning.

This repository holds the first two increments, built with Django templates on PostgreSQL (Supabase):

- **Increment 1, Accounts:** registration, login, role-based dashboards and profiles.
- **Increment 2, Personal Vault (core feature):** a private word notebook. A learner saves a word with its meaning, an example sentence and a personal memory trick, groups words with tags, marks favorites, and gets one of their own words back each day as a daily review.

## Roles

There are two roles. New accounts are always Learners. Superusers get the Admin role automatically.

**A learner can:**

- add, view, edit and delete their own vault words
- tag words (up to 5 tags per word) and manage their own tags
- search, filter by tag or favorites, sort and page through their vault
- mark and unmark favorites from a card or from the word's page
- see a daily review word and a vault summary on their dashboard
- view and edit their own profile

A learner never sees another user's words, tags or searches. Another user's record returns a 404 page.

**An admin can:**

- see user statistics, the newest users and a vault overview on the admin dashboard
- review every learner's vault entries with the owner's username, and search them by word or owner
- delete an entry after a confirmation page (the owner's tags are kept)
- open Django admin to manage users, if the account is staff
- view and edit their own profile

An admin cannot create or edit vault entries, and gets a 403 page on the learner vault pages.

### Pages and access

| URL | Page | Anonymous | Learner | Admin |
|---|---|---|---|---|
| `/` | Home | Yes | Yes | Yes |
| `/register/`, `/login/` | Sign up, log in | Yes | Redirected to dashboard | Redirected to dashboard |
| `/logout/` | Log out (POST only) | No | Yes | Yes |
| `/dashboard/` | Sends you to your role's dashboard | Redirected to login | Yes | Yes |
| `/dashboard/learner/` | Learner dashboard | Redirected to login | Yes | 403 |
| `/dashboard/admin/` | Admin dashboard | Redirected to login | 403 | Yes |
| `/profile/`, `/profile/edit/` | Your profile | Redirected to login | Own profile | Own profile |
| `/vault/` | Vault list with search, filters and sorting | Redirected to login | Own words | 403 |
| `/vault/new/` | Add a word | Redirected to login | Yes | 403 |
| `/vault/<id>/`, `/vault/<id>/edit/`, `/vault/<id>/delete/` | View, edit, delete a word | Redirected to login | Own words, others 404 | 403 |
| `/vault/<id>/favorite/` | Favorite toggle (POST only) | Redirected to login | Own words, others 404 | 403 |
| `/vault/tags/`, `/vault/tags/<id>/delete/` | Manage and delete tags | Redirected to login | Own tags, others 404 | 403 |
| `/vault/admin/entries/` | Moderation list | Redirected to login | 403 | Yes |
| `/vault/admin/entries/<id>/`, `/vault/admin/entries/<id>/delete/` | Read-only entry, delete confirmation | Redirected to login | 403 | Yes |
| `/admin/` | Django admin | Redirected to admin login | No | Staff only |

## Features

**Personal Vault**

- **Create, view, edit and delete** words. Each word has a meaning, an optional example sentence, an optional memory anchor and a favorite flag. A word can be saved only once per learner, ignoring letter case.
- **Tags:** pick existing tags or type new ones separated by commas. Tag names are 2 to 30 characters, with letters, digits, spaces and hyphens. The same name in a different letter case reuses the existing tag. Tags can be deleted without deleting any word.
- **Search** by word, meaning, example or memory anchor.
- **Favorites:** a bookmark button on every card and on the word's page, plus a "Favorites only" filter.
- **Sorting:** newest first, oldest first, or word A to Z.
- **Pagination:** 10 words per page. Page links keep the search, filters and sort order.
- **Daily review:** the learner dashboard shows one word from the learner's own vault. It stays the same for the whole day and changes the next day.
- **Dashboards:** the learner dashboard shows vault counts and the three newest words. The admin dashboard shows user statistics, vault totals, words added in the last 7 days, and the five learners with the most words.
- **Admin moderation:** a searchable list of all entries, a read-only detail page, and delete with confirmation.

**Accounts**

- Registration with unique usernames and emails (case-insensitive) and Django's password validators.
- Passwords are stored as hashes through Django's built-in authentication.
- Login with username or email, and logout through a CSRF-protected form.
- Login-protected pages return you to the page you wanted after login. Unsafe external addresses are ignored.
- Profile page and edit form: name, email, contact number, profile photo (JPEG, PNG or WebP, up to 2 MB), language level and offline-download preference.
- Recent searches on the dashboard. Searches are saved to your history; dictionary results are not available yet.

**Look and feel**

- A library theme with light and dark mode. It follows the system setting and remembers your choice.
- Friendly 403 and 404 pages.
- Layouts that work at phone width.

## Tech stack

- Python 3.12
- Django 6.1 with Django templates
- PostgreSQL on Supabase (through the Session pooler), with `psycopg2-binary`
- `python-decouple` for settings from `.env`
- Pillow for profile-photo validation
- Bootstrap 5.3 and Bootstrap Icons (CDN), and the Lora font (Google Fonts)

## Project structure

```
LexiTrace/
├── accounts/                 Accounts app
│   ├── backends.py           Username-or-email authentication backend
│   ├── decorators.py         role_required decorator
│   ├── forms.py              Register, login, profile and search forms
│   ├── models.py             Custom User model with roles, and SearchHistory
│   ├── services.py           Daily review, vault summary and admin overview
│   ├── admin.py              User in Django admin
│   ├── urls.py               Account routes
│   ├── views.py              Home, auth, dashboards, search history and profile views
│   ├── migrations/
│   ├── templatetags/ui.py    add_class form filter
│   └── tests/                Account, dashboard and service tests
├── vault/                    Personal Vault app
│   ├── forms.py              Entry form with tags
│   ├── models.py             VaultEntry and VaultTag
│   ├── urls.py               Vault, tag and moderation routes
│   ├── views.py              Learner vault views and admin moderation views
│   ├── migrations/
│   └── tests.py              Vault tests
├── config/                   Django project settings and root URLs
├── docs/
│   ├── erd.md                Entity relationship diagram and business rules
│   └── LexiTrace-Belino-MarcelSimon-G2-PD2.pdf   PD2 completion report
├── static/
│   ├── css/theme.css         Library theme, light and dark palettes
│   ├── js/theme.js           Theme toggle
│   └── img/                  Favicon and wallpaper pattern
├── templates/
│   ├── base.html             Shared layout, navigation and messages
│   ├── 403.html, 404.html    Error pages
│   ├── partials/             Form fields, avatar, search panel, daily review card
│   ├── accounts/             Home, auth, dashboard and profile pages
│   └── vault/                Vault, tag and moderation pages
├── .env.example              Settings template (copy to .env)
├── manage.py
└── requirements.txt
```

## Setup on a new machine

The commands below are for Windows. Notes for macOS and Linux follow each step where they differ.

1. Clone the repository and open a terminal in its root folder.

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

   On macOS or Linux, use `source venv/bin/activate` instead.

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create your own `.env` from the example:

   ```bash
   copy .env.example .env
   ```

   On macOS or Linux, use `cp .env.example .env`.

   Open `.env` and fill in your values. For Supabase, copy the **Session pooler** connection details from your project's **Connect** panel into `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` and `DB_PORT`, and set `DB_SSLMODE=require`. Never commit `.env`; it is already in `.gitignore`.

5. Apply the migrations:

   ```bash
   python manage.py migrate
   ```

6. Create an admin account. Superusers get the Admin role automatically:

   ```bash
   python manage.py createsuperuser
   ```

   Learner accounts are made through the **Create account** page.

7. Start the development server and open http://127.0.0.1:8000/:

   ```bash
   python manage.py runserver
   ```

## Running the tests

The tests use Django's `TestCase` and `SimpleTestCase`. They create their own users and rows and run against a separate test database on the same PostgreSQL server, never against your real data.

```bash
python manage.py test --keepdb
```

`--keepdb` keeps the test database between runs. This is needed with the Supabase Session pooler, which can keep a connection open to the test database and block Django from deleting it at the end. Profile-photo tests write to a temporary folder that is removed afterwards.

## Testing on a phone on the same Wi-Fi

1. Find your PC's local IP address. On Windows, run `ipconfig` and read the **IPv4 Address** of your Wi-Fi adapter, for example `192.168.1.23`.

2. Add that address to `ALLOWED_HOSTS` in `.env`:

   ```
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.23
   ```

3. Start the server so other devices on the network can reach it:

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

4. If Windows asks whether to allow Python through the firewall, allow it for **Private networks**. If the phone still cannot connect, allow incoming connections on port 8000 for private networks in Windows Defender Firewall.

5. On the phone, connected to the same Wi-Fi, open `http://<PC-IP>:8000`, for example `http://192.168.1.23:8000`.

## Branching workflow

- `main` is the stable branch.
- `develop` is the integration branch.
- Each feature is built on its own `feature/...` branch and merged into `develop` through a pull request.
- Merged feature branches are kept, not deleted.

## Test accounts

Two test accounts, TestAdmin (admin) and CoolSmith (learner), are listed in the [PD2 completion report](docs/LexiTrace-Belino-MarcelSimon-G2-PD2.pdf). The report holds throwaway test passwords for those two accounts only; no real credentials are stored in this repository.

## Known limitations

- When an admin deletes an entry, the learner is not notified.
- On phones, the stacked tables (the moderation list and the recent users table) may be read as plain text by some screen readers.
- Messages in the message area may not be announced by screen readers when a page loads.
- Contextual search is not built yet. The dashboard search only saves your searches.

## Next increment ideas

- Renaming a tag.
- Notifying the learner when an admin removes one of their entries.
- Contextual search: paste a sentence and get the meaning that fits.
