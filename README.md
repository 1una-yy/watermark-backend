# Dual-WaterMark Backend

FastAPI + MySQL backend that wraps the Dual-WaterMark partner API
(`https://api.watermark.nyanfox.com`) with user auth, image storage
on Vercel Blob, and a full audit trail in MySQL.

---

## Project structure

```
watermark-backend/
├── app/
│   ├── main.py              # FastAPI app + CORS + lifespan
│   ├── config.py            # Pydantic settings (reads .env)
│   ├── database.py          # Async SQLAlchemy engine + session
│   ├── models/              # ORM models (users, images, embed_tasks, verify_logs)
│   ├── schemas/             # Pydantic request / response models
│   ├── core/
│   │   ├── security.py      # JWT + bcrypt
│   │   └── deps.py          # FastAPI dependency injection
│   ├── routers/
│   │   ├── auth.py          # POST /auth/register, /auth/login, GET /auth/me
│   │   ├── images.py        # POST /images/upload, GET /images/
│   │   ├── embed.py         # POST /embed/, GET /embed/{id}
│   │   └── verify.py        # POST /verify/, GET /verify/
│   └── services/
│       ├── watermark_api.py # Async httpx client → partner API
│       └── storage.py       # Vercel Blob REST upload / delete
├── alembic/                 # DB migrations
├── schema.sql               # Raw MySQL DDL (reference)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick start

### 1. Clone & install

```bash
cd watermark-backend
python -m venv .venv && source .venv/bin/activate
(.venv\Scripts\activate)
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in DATABASE_URL, SECRET_KEY, BLOB_READ_WRITE_TOKEN
```

| Variable | Description |
|---|---|
| `DATABASE_URL` | `mysql+aiomysql://user:pass@host:3306/watermark_db` |
| `SECRET_KEY` | Random 32-char string for JWT signing |
| `BLOB_READ_WRITE_TOKEN` | Vercel Blob token from your project settings |
| `WATERMARK_API_BASE_URL` | Default: `https://api.watermark.nyanfox.com` |
| `ALLOWED_ORIGINS` | Comma-separated front-end origins |

### 3. Create the MySQL database

```bash
mysql -u root -p < schema.sql
# OR let SQLAlchemy auto-create (development only):
# Tables are created automatically on first startup via create_all()
```

### 4. Run migrations (production)

```bash
# Generate your first migration after any model change
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

---

## API overview

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| GET  | `/auth/me` | Current user info |

### Images
| Method | Path | Description |
|--------|------|-------------|
| POST | `/images/upload` | Upload image → Vercel Blob |
| GET  | `/images/` | List my images |
| GET  | `/images/{id}` | Get single image |

### Embed (watermark tasks)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/embed/` | Create embed task (async background job) |
| GET  | `/embed/` | List my tasks |
| GET  | `/embed/{id}` | Poll task status + get result URLs |

### Verify
| Method | Path | Description |
|--------|------|-------------|
| POST | `/verify/` | Run verification → stores result in DB |
| GET  | `/verify/` | List verification history |
| GET  | `/verify/{id}` | Get single verify log |

---

## Typical usage flow

```
1. POST /auth/register          → get account
2. POST /auth/login             → get JWT token
3. POST /images/upload          → upload original image, get image_id
4. POST /embed/                 → { image_id, editguard_bits, stegastamp_secret }
                                   returns task_id, status=pending
5. GET  /embed/{task_id}        → poll until status=done
                                   response includes result_image_url + metadata_json
6. POST /verify/                → { image_url or image_id, metadata_json }
                                   returns overall_pass, editguard_accuracy, mask_url
7. GET  /verify/                → audit history
```

---

## Notes

- Embedding runs as a **FastAPI background task**. For production scale, replace with Celery + Redis.
- `editguard_bits` must be exactly 64 binary characters.
- `stegastamp_secret` must be ≤ 7 UTF-8 bytes.
- Image uploads are capped at 20 MB; accepted formats: JPEG, PNG, WEBP.
- All endpoints require `Authorization: Bearer <token>` except `/health`, `/auth/register`, `/auth/login`.
