# Document Management System (DMS) — Sanaap Backend Challenge

A secure, role-based Document Management System built with **Django REST Framework**, **MinIO** object storage, **Celery** + **RabbitMQ** background tasks, **Redis** caching, and **WebSocket** real-time notifications.

---

## Architecture

```
                          ┌──────────────────────────────────────┐
                          │         Nginx (Docker)               │
                          │         Reverse Proxy :80            │
                          └──────────┬───────────────────────────┘
                                     │
                          ┌──────────▼───────────────────────────┐
                          │       Django / DRF (Gunicorn)        │
                          │              :8000                   │
                          └─────────────────────────‌‌‌‌‌‌-----───────-┘
                               │      │         │           │
                      ┌────────▼┐  ┌──▼──────┐ ┌▼────────┐ ┌▼──────────┐
                      │PostgreSQL│ │  Redis  │ │ RabbitMQ│ │   MinIO   │
                      │  :5432   │ │ (cache) │ │ (broker)│ │ (storage) │
                      │          │ │  :6379  │ │  :5672  │ │   :9000   │
                      └──────────┘ └─────────┘ └──┬──────┘ └───────────┘
                                                  │
                                           ┌──────▼──────┐
                                           │   Celery    │
                                           │   Worker    │
                                           └─────────────┘
```

**RabbitMQ** → Message Broker (Celery task queue)
**Redis** → Cache only (Django cache + Channels layer)

## Features

- **Document CRUD** — Upload, retrieve, update, and delete documents via REST API
- **MinIO Object Storage** — S3-compatible storage with presigned URLs
- **JWT Authentication** — Secure login with access/refresh tokens
- **Role-Based Access Control (RBAC)** — admin, editor, viewer roles
- **Secure Document URLs** — Downloads via authenticated API endpoint only
- **Filtering & Pagination** — Filter by title, content type, date; limit/offset pagination
- **Background Task Processing** — Celery + RabbitMQ for post-upload processing
- **Audit Logging** — Tracks all create, read, update, delete, download actions
- **WebSocket Notifications** — Real-time events on document create/update
- **Nginx Reverse Proxy** — Dockerized with security headers and WebSocket support
- **Swagger/OpenAPI Docs** — Auto-generated via drf-spectacular
- **Unit Tests** — Comprehensive suite covering models, services, APIs, and RBAC
- **SOLID Principles** — Clean service/selector/API layer separation
- **Docker Compose** — One-command deployment

## Tech Stack

| Component        | Technology                     |
|------------------|--------------------------------|
| Backend          | Django 5.1 + DRF 3.15         |
| Python           | 3.12                           |
| Database         | PostgreSQL 16                  |
| Object Storage   | MinIO (S3-compatible)          |
| Cache            | Redis 7                        |
| Message Broker   | RabbitMQ 3.13                  |
| Task Queue       | Celery 5.4                     |
| Real-time        | Django Channels + Redis        |
| Reverse Proxy    | Nginx 1.27 (Docker)            |
| Auth             | JWT (simplejwt)                |
| API Docs         | Swagger (drf-spectacular)      |
| Containerization | Docker & Docker Compose        |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose v2+

### 1. Clone & Configure

```bash
git clone https://github.com/pedram12dev/api-challenge-backend-sanaap
cd api-challenge-backend-sanaap

touch .env 

cp .env.expamle .env

# Review .env (defaults work out of the box)
cat .env
```

### 2. Build & Run

```bash
docker compose up --build -d
```

This starts **8 services**: PostgreSQL, Redis, RabbitMQ, MinIO, Django (Gunicorn), Celery Worker, Celery Beat, Nginx.

### 3. Create a Superuser

```bash
docker compose exec django python manage.py createsuperuser
```

### 4. Access the Application

| Service           | URL                          |
|-------------------|------------------------------|
| **API (Nginx)**   | http://localhost              |
| **Swagger UI**    | http://localhost/             |
| **Redoc**         | http://localhost/redoc/       |
| **Admin Panel**   | http://localhost/admin/       |
| **MinIO Console** | http://localhost:9001         |
| **RabbitMQ UI**   | http://localhost:15672        |

---

## API Endpoints

### User Authentication Authorization

| Method | Endpoint                 | Description          |
|--------|--------------------------|----------------------|
| POST   | `/api/auth/jwt/login/`   | Get JWT tokens       |
| POST   | `/api/auth/jwt/refresh/` | Refresh access token |
| POST   | `/api/auth/jwt/verify/`  | Verify token         |
| POST   | `/api/users/register/`   | Register new user    |

### Documents

| Method | Endpoint                        | Roles      | Description                          |
|--------|---------------------------------|------------|--------------------------------------|
| GET    | `/api/documents/`               | viewer+    | List documents (filtered, paginated) |
| POST   | `/api/documents/`               | editor+    | Upload a document                    |
| GET    | `/api/documents/{id}/`          | viewer+    | Retrieve document details            |
| PUT    | `/api/documents/{id}/`          | editor+    | Update a document                    |
| DELETE | `/api/documents/{id}/`          | admin only | Delete a document                    |
| GET    | `/api/documents/{id}/download/` | viewer+    | Download file                        |

### Admin Management

| Method | Endpoint                                | Roles      | Description           |
|--------|-----------------------------------------|------------|-----------------------|
| GET    | `/api/documents/admin/users/`           | admin only | List all users        |
| POST   | `/api/documents/admin/users/`           | admin only | Create user with role |
| PATCH  | `/api/documents/admin/users/{id}/role/` | admin only | Update user role      |
| GET    | `/api/documents/audit-logs/`            | admin only | View audit logs       |

### Filtering & Pagination

```
GET /api/documents/?title=report&content_type=pdf&created_after=2025-01-01&limit=10&offset=0
```

---

## Role-Based Access Control (RBAC)

| Role     | Documents                    | Users                      | Audit Logs |
|----------|------------------------------|----------------------------|------------|
| `admin`  | Create, Read, Update, Delete | Create, List, Assign Roles | Read       |
| `editor` | Create, Read, Update         | —                          | —          |
| `viewer` | Read only                    | —                          | —          |

---

## Running Tests

```bash
# Inside Docker
docker compose exec django bash

python manage.py test

```
---
## Project Structure

```
├── apichallenge/
│   ├── api/                 # API utils, pagination, exception handlers
│   ├── authentication/      # JWT auth URLs
│   ├── common/              # BaseModel
│   ├── core/                # Core exceptions
│   ├── documents/           # ★ Document Management System
│   │   ├── apis.py          #   API views (CRUD + admin)
│   │   ├── consumers.py     #   WebSocket consumer
│   │   ├── filters.py       #   Django-filter definitions
│   │   ├── models.py        #   Document & AuditLog models
│   │   ├── notifications.py #   WebSocket notification helper
│   │   ├── permissions.py   #   RBAC permission classes
│   │   ├── routing.py       #   WebSocket URL routing
│   │   ├── selectors.py     #   Query layer
│   │   ├── services.py      #   Business logic layer
│   │   ├── tasks.py         #   Celery background tasks
│   │   ├── tests/           #   Unit tests
│   │   └── urls.py          #   URL routing
│   └── users/               # User model with roles
├── config/
│   ├── django/              # Settings (base, local, test, production)
│   ├── settings/            # Modular settings (JWT, CORS, Celery, etc.)
│   ├── asgi.py              # ASGI + Channels
│   ├── celery.py            # Celery app
│   └── urls.py              # Root URLs
├── docker/
│   ├── Dockerfile           # Python 3.12 image
│   ├── nginx/
│   │   └── nginx.conf       # Nginx reverse proxy config
│   ├── web_entrypoint.sh    # Django startup
│   ├── celery_entrypoint.sh # Celery worker startup
│   └── beats_entrypoint.sh  # Celery beat startup
├── docker-compose.yml       # PostgreSQL + Redis + RabbitMQ + MinIO + Django + Celery + Nginx
├── .env                     # Environment variables
├── requirements/            # Python dependencies
└── pytest.ini               # Test config
```

---

## Environment Variables

| Variable            | Default                           | Description              |
|---------------------|-----------------------------------|--------------------------|
| `SECRET_KEY`        | (see .env)                        | Django secret key        |
| `DEBUG`             | `True`                            | Debug mode               |
| `DATABASE_URL`      | `psql://postgres:postgres@db:...` | PostgreSQL connection    |
| `REDIS_LOCATION`    | `redis://redis:6379/0`            | Redis (cache + channels) |
| `CELERY_BROKER_URL` | `amqp://guest:guest@rabbitmq:...` | RabbitMQ broker          |
| `MINIO_ENDPOINT`    | `minio:9000`                      | MinIO server             |
| `MINIO_ACCESS_KEY`  | `minioadmin`                      | MinIO access key         |
| `MINIO_SECRET_KEY`  | `minioadmin`                      | MinIO secret key         |
| `MINIO_BUCKET_NAME` | `documents`                       | MinIO bucket name        |

> ⚠️ **Production**: Change `SECRET_KEY`, `POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY/SECRET_KEY`, `RABBITMQ_PASS` to strong unique values. Set `DEBUG=False`.
