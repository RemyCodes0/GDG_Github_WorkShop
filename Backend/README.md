# AUB Collab — Backend

The API behind **AUB Collab**, the AUB student collaboration platform where students post project ideas, find collaborators, and build teams.

> *Have an idea. Find your people. Build it together.*

For the full project vision, see the [root README](../README.md). The client lives in [`../Frontend`](../Frontend).

## Tech Stack

* [Python](https://www.python.org) 3.11 or newer
* [Django](https://www.djangoproject.com) 5.2 (LTS)
* [Django REST Framework](https://www.django-rest-framework.org) for the API
* [django-cors-headers](https://github.com/adamchainz/django-cors-headers) so the Vite frontend can call the API
* SQLite for local development (PostgreSQL is a candidate for production)

## Getting Started

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

On Debian/Ubuntu you may first need `sudo apt install python3-venv python3-pip`.

The API runs at http://localhost:8000. Check it with:

```bash
curl http://localhost:8000/api/health/
# {"status": "ok"}
```

The admin site is at http://localhost:8000/admin/. Create an account with `python manage.py createsuperuser`.

## Commands

| Command | Description |
| --- | --- |
| `python manage.py runserver` | Start the dev server |
| `python manage.py makemigrations` | Create migrations after model changes |
| `python manage.py migrate` | Apply migrations |
| `python manage.py startapp <name>` | Create a new Django app |
| `python manage.py test` | Run the tests |

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | insecure dev key | Secret key. Always set this in production |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated frontend origins |
| `THROTTLING_ENABLED` | `True` | Set to `False` to turn every rate limit off, for load tests |
| `THROTTLE_<SCOPE>` | see below | Override one rate, for example `THROTTLE_AUTH=10/min` |
| `NUM_PROXIES` | unset | Number of reverse proxies in front of the app, so limits see the real client IP |
| `MAX_REQUEST_BODY_BYTES` | `2097152` (2 MB) | Larger request bodies are rejected |

## Abuse Prevention

The `abuse` app protects the API from spam, scraping and password guessing.

**Global limits.** Every API request counts against two limits, a short burst and a daily total. Anonymous visitors are counted per IP address, signed in students per account:

| Scope | Default |
| --- | --- |
| `anon_burst` / `anon_sustained` | 30 per minute / 1000 per day per IP |
| `user_burst` / `user_sustained` | 120 per minute / 10000 per day per account |

**Sensitive actions** get a tighter limit on top. Add `SensitiveActionThrottle` and a scope to the view:

```python
from rest_framework.settings import api_settings
from abuse.throttles import SensitiveActionThrottle

class LoginView(APIView):
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, SensitiveActionThrottle]
    throttle_scope = "auth"
```

| Scope | Default | For |
| --- | --- | --- |
| `auth` | 5 per minute | login, registration, password reset, email verification |
| `applications` | 20 per hour | applying to projects |
| `project_create` | 10 per hour | publishing projects |

All views with the same scope share one counter, so spreading attempts over several endpoints does not get around it.

**When a limit is hit** the API answers `429 Too Many Requests` with a `Retry-After` header and:

```json
{"detail": "Too many requests. Please slow down and try again later.", "code": "rate_limited", "retry_after_seconds": 42}
```

Each rejection is logged as a warning on the `aubcollab.abuse` logger with the scope, path, client IP and user ID, so repeated abuse is easy to spot.

**Request size.** Bodies over `MAX_REQUEST_BODY_BYTES` and forms with more than 500 fields are rejected before a view runs.

Counters are stored in the default cache. With several server processes in production, point the cache at a shared store such as Redis, or each process will count separately.

## Structure

```
Backend/
├── config/           # Project settings, URLs, WSGI/ASGI
├── manage.py
├── requirements.txt
└── .env.example
```

Each feature (users, projects, applications, ...) will be its own Django app next to `config/`.

## Planned Domain

* **Users and profiles:** major, year, skills, links, and project history
* **Projects:** title, description, goals, category, duration, time commitment, required majors and skills, collaborators needed, deadline, and difficulty
* **Applications:** CV, skills, experience, motivation, availability, and status (pending, accepted, rejected)
* **Teams:** members and roles for each project
* **Discovery:** search, filtering, and, later, personalized matching and recommendations
* **Workspaces (later):** tasks, milestones, discussions, and resources

The core flow: **Idea → Project → Applications → Team → Collaboration → Completed Project**

## Contributing

AUB Collab is open source and built by students. Backend issues are labeled by difficulty:

* **Easy:** documentation, testing, bug fixes, input validation
* **Medium:** API endpoints, database models, authentication, search and filtering, notifications, application management, profile functionality
* **Hard:** recommendation systems, student-project matching algorithms, search infrastructure, real-time collaboration, advanced authorization, performance optimization, background processing, analytics infrastructure
