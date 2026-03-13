# LTI Project Selection

An LTI 1.3 compliant Django application where professors propose projects and students submit ranked preferences. Assignments are made automatically by a greedy algorithm, with professor override support, and results are published back to the LMS via the Assignments and Grades Service (AGS).

## Requirements

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- An LTI 1.3 compatible LMS (e.g. Moodle, Canvas)

For local development without Docker:

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- PostgreSQL 15+

---

## Running with Docker Compose (recommended)

### 1. Clone and configure environment

```bash
cp .env.example .env
```

Edit `.env` and set secure values:

```env
SECRET_KEY=your-long-random-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost

POSTGRES_PASSWORD=your-secure-db-password
DATABASE_URL=postgres://postgres:your-secure-db-password@db:5432/lti_project_selection
```

### 2. Start the application

```bash
docker compose up --build -d
```

This will:
- Build the Django application image
- Start PostgreSQL, the Django app (Gunicorn), and Nginx
- Run database migrations automatically
- Serve the app at **http://localhost**

### 3. Create a Django superuser (first time only)

```bash
docker compose exec web python manage.py createsuperuser
```

The Django admin is available at **http://localhost/admin/**.

### 4. Stop the application

```bash
docker compose down
```

To also remove the database volume:

```bash
docker compose down -v
```

---

## Local Development (without Docker)

### 1. Install dependencies

```bash
uv sync
```

Or with pip:

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` for local development:

```env
SECRET_KEY=any-local-dev-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://postgres:password@localhost:5432/lti_project_selection
```

### 3. Set up the database

Create the PostgreSQL database, then run migrations:

```bash
python manage.py migrate
python manage.py createcachetable
```

### 4. Run the development server

```bash
python manage.py runserver
```

The app is available at **http://localhost:8000**.

---

## Registering the Tool in your LMS (LTI 1.3)

### Step 1: Register the platform in Django admin

1. Go to **http://localhost/admin/** and log in
2. Navigate to **LTI 1.3 → Platforms → Add**
3. Fill in the details provided by your LMS:
   - **Issuer** — the LMS issuer URL (e.g. `https://your-lms.example.com`)
   - **Client ID** — assigned by the LMS when you register an external tool
   - **Auth login URL** — LMS OIDC authentication endpoint
   - **Auth token URL** — LMS token endpoint
   - **Key set URL** — LMS JWKS endpoint

### Step 2: Register this tool in your LMS

Provide your LMS with the following tool URLs (replace `https://your-domain.com` with your actual host):

| Parameter | Value |
|-----------|-------|
| Tool URL / Launch URL | `https://your-domain.com/lti/launch/` |
| OIDC Login Initiation URL | `https://your-domain.com/lti/login/` |
| JWKS URL | `https://your-domain.com/.well-known/jwks.json` |

Configure the tool in the LMS to send the **Assignments and Grades Service** claim so that grade passback works.

### Step 3: Add the tool to a course

Add the registered external tool as an activity or link within a course. The tool will automatically create a course record on first launch.

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | Enable debug mode | `False` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,example.com` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `s3cur3p4ssw0rd` |
| `DATABASE_URL` | Full database connection URL | `postgres://postgres:pass@db:5432/lti_project_selection` |

---

## Project Structure

```
lti_project_selection/   # Django project settings and URLs
projects/                # Main app: models, views, services, LTI launch handler
templates/               # HTML templates (Bootstrap 5)
docker-compose.yml       # Docker Compose configuration
Dockerfile               # Application container definition
nginx.conf               # Nginx reverse proxy configuration
entrypoint.sh            # Container startup script (migrate + gunicorn)
.env.example             # Environment variable template
requirements.txt         # Python dependencies
```
