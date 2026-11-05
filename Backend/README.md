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
| `PRIVATE_MEDIA_ROOT` | `Backend/private_media` | Where uploads are stored. Must not be inside a public web folder |
| `FILE_UPLOAD_MAX_BYTES` | `5242880` (5 MB) | Largest accepted upload |
| `FILE_LINK_MAX_AGE` | `300` | Seconds a download link works |

## Secure File Storage

The `files` app stores CVs and other uploads so that only the right people can ever read them.

| Endpoint | Does |
| --- | --- |
| `POST /api/files/` (signed in, multipart field `file`) | Validates and stores the upload. Returns its id, name, type, size, SHA 256 and a download link |
| `GET /api/files/<id>/` | Details and a fresh download link, for the owner or staff |
| `DELETE /api/files/<id>/` | Owner only. Removes the record and the file on disk |
| `GET /api/files/download/<token>/` | Serves the file, if the link is valid, not expired, and opened by the user it was issued to |

**What makes it safe:**

* **Content is checked, not just the name.** Allowed types are PDF, DOCX, PNG and JPEG. The file's first bytes must match its extension (a DOCX must really contain a Word document), so a renamed script or HTML page is rejected even if it is called `cv.pdf`.
* **Nothing is public.** Files are stored outside any public folder, under a random name (never the uploader's file name), with `0640` permissions.
* **Signed, expiring links.** A download link is signed with `SECRET_KEY`, names the user it was issued to, and stops working after 5 minutes. A changed character gives 404, an old link gives 410. A forwarded link does not work for anyone else.
* **No probing.** "Does not exist" and "not yours" both answer 404, so file IDs cannot be tested.
* **Safe delivery.** Downloads are always attachments with `nosniff`, `no-store` and a sandboxing Content-Security-Policy, so a browser never runs a file inside the site.
* **Integrity.** Each file's SHA 256 is stored, to detect tampering or duplicate uploads later.

Who may open a file is decided in one place, `files.views.can_access` (today: the owner and staff). When applications exist, extend it so a project owner can open the CVs of students who applied to their project.

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
