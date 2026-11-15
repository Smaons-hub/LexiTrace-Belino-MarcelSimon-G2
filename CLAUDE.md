# LexiTrace

Context-aware vocabulary lookup system. Django project (`config/`) with Django templates for the frontend. Current phase: Account feature (`accounts` app).

## Rules

- **Stack:** Django (latest stable), Django templates, PostgreSQL or Supabase (PostgreSQL). Never SQLite, not even for tests.
- **Secrets:** live only in `.env` (read via python-decouple). Never print, log, commit or echo `.env` values. Never ask the user to paste credentials into chat. `.env.example` holds placeholders only.
- **Auth:** use Django's built-in authentication. Never store plain-text passwords. User model is `accounts.User` (`AUTH_USER_MODEL`).
- **Git:** commit in small steps with explicit paths (`git add <path>`); never `git add -A` or `git add .`. Conventional commit messages (`feat:`, `chore:`, `test:`, `docs:`). Do not push; the user pushes.
- **Existing code:** do not touch or reformat comments or code you did not write.
- **Testing:** keep it light; no extra setup just to test.

## Commands (Windows, venv in repo root)

```
venv\Scripts\activate
python manage.py check
python manage.py makemigrations accounts
python manage.py migrate
python manage.py runserver
```
