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
