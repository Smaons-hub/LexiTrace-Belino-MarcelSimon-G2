# LexiTrace

LexiTrace is a context-aware vocabulary lookup system. Instead of listing every meaning of a word, it reads the sentence the word appears in and gives the definition that fits, online, with an offline dictionary for when there is no connection. This repository contains the first feature of the project: the **Account** module (registration, login, role-based dashboards and profiles), built with Django templates on PostgreSQL (Supabase).

## Account features

- **Registration** with first name, last name, username, email and password. Usernames and emails are unique (case-insensitive), emails are stored in lowercase, and Django's password validators apply. New accounts are always **Learners**.
- **Hashed passwords** through Django's built-in authentication. Plain-text passwords are never stored.
- **Login with username or email** (any letter case), with clear error messages for wrong credentials and inactive accounts.
- **Logout** through a CSRF-protected POST form.
- **Login-protected pages**: visitors who are not signed in are sent to the login page and returned to the page they wanted (`next`). Unsafe external `next` values are ignored.
- **Two roles, Learner and Admin**, each with their own dashboard. Opening the other role's dashboard returns a friendly 403 page.
- **Admin dashboard** with user statistics, the 10 newest users, and a link to Django admin for staff.
- **Profile** page and edit form for the signed-in user only: name, email, contact number, profile photo (JPEG, PNG or WebP, up to 2 MB), language level and offline-download preference.
- **Red theme with light and dark mode**, which follows the system setting and remembers your choice.

## Tech stack

- Python 3.12+
- Django 6.1 with Django templates
- PostgreSQL on Supabase (through the Session pooler), with `psycopg2-binary`
- `python-decouple` for settings from `.env`
- Pillow for profile-photo validation
- Bootstrap 5.3 and Bootstrap Icons (CDN)

## Setup

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

4. Create your own `.env` from the example and fill in your values:

   ```bash
   copy .env.example .env
   ```

   On macOS or Linux, use `cp .env.example .env`.

   For Supabase, use the **Session pooler** connection details from your project's **Connect** panel, and set `DB_SSLMODE=require`. Never commit `.env`; it is already in `.gitignore`.

5. Apply the migrations:

   ```bash
   python manage.py migrate
   ```

6. Create an admin account. Superusers get the Admin role automatically.

   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server and open http://127.0.0.1:8000/:

   ```bash
   python manage.py runserver
   ```

## Roles and access

| URL | Page | Anonymous | Learner | Admin |
|---|---|---|---|---|
| `/` | Home | Yes | Yes | Yes |
| `/register/` | Sign up | Yes | Redirected to dashboard | Redirected to dashboard |
| `/login/` | Log in | Yes | Redirected to dashboard | Redirected to dashboard |
| `/logout/` | Log out (POST only) | No | Yes | Yes |
| `/dashboard/` | Sends you to your role's dashboard | Redirected to login | Yes | Yes |
| `/dashboard/learner/` | Learner dashboard | Redirected to login | Yes | 403 |
| `/dashboard/admin/` | Admin dashboard | Redirected to login | 403 | Yes |
| `/profile/` | Your profile | Redirected to login | Own profile | Own profile |
| `/profile/edit/` | Edit your profile | Redirected to login | Own profile | Own profile |
| `/admin/` | Django admin | Redirected to admin login | No | Staff only |

## Running the tests

The tests use Django's `TestCase` and run against a temporary test database on the same PostgreSQL server.

```bash
python manage.py test --keepdb
```

`--keepdb` keeps the test database between runs. This is needed with the Supabase Session pooler, which can keep a connection open to the test database and block Django from deleting it at the end. Profile-photo tests write to a temporary folder that is removed afterwards.

## Project structure

```
LexiTrace/
├── accounts/                 Account app
│   ├── backends.py           Username-or-email authentication backend
│   ├── decorators.py         role_required decorator
│   ├── forms.py              Register, login and profile forms
│   ├── models.py             Custom User model with roles
│   ├── admin.py              User in Django admin
│   ├── urls.py               Account routes
│   ├── views.py              Views for every account page
│   ├── migrations/
│   ├── templatetags/ui.py    add_class form filter
│   └── tests/                Automated tests
├── config/                   Django project settings and root URLs
├── static/
│   ├── css/theme.css         Red theme and light/dark palette
│   └── js/theme.js           Theme toggle
├── templates/
│   ├── base.html             Shared layout and navbar
│   ├── 403.html, 404.html    Error pages
│   ├── partials/             Form-field and avatar partials
│   └── accounts/             Account pages
├── .env.example              Settings template (copy to .env)
├── manage.py
└── requirements.txt
```
