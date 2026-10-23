# Goodreads Reader API

An **unofficial, self-hosted** FastAPI app that imports your Goodreads shelves, ratings, and reviews into SQLite. Read-only toward Goodreads. This is a reusable starter for anyone's library, not affiliated with Goodreads.

## Zero-setup GitHub Codespaces workflow

This repository now includes a devcontainer and one-command launcher. In a **new Codespace**, Python dependencies install automatically. For an **existing Codespace**, open its terminal and run:

```bash
git pull
bash scripts/start.sh
```

The launcher generates a random API key locally in ignored `.env` and starts Uvicorn. For the owner's personal workspace, the starter account ID is `167934914`; **other users must set `GOODREADS_USER_ID` in `.env` to their own profile ID before syncing.** Do not commit your `.env`.

Keep Codespaces forwarded port 8000 set to **Private**. Then, in a **second Codespaces terminal**, run:

```bash
bash scripts/sync.sh
bash scripts/stats.sh
```

Goodreads may block public RSS; if sync fails, export your Goodreads library to CSV and use `POST /import/csv` as documented below. This does not grant an assistant direct access to the private Codespaces terminal.

## Run online in GitHub Codespaces

1. Click **Code → Codespaces → Create codespace on main**.
2. In its terminal:

```sh
pip install -r requirements.txt
export READING_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export GOODREADS_USER_ID="YOUR_NUMERIC_GOODREADS_ID"
uvicorn app:app --host 127.0.0.1 --port 8000
```

3. In another terminal, use `curl http://127.0.0.1:8000/health`, then `curl -H "X-API-Key: $READING_API_KEY" http://127.0.0.1:8000/stats`.

**Keep Codespaces forwarded ports private.** Data in a Codespace is not a managed persistent service; back up the database.

## Run with Docker

```sh
cp .env.example .env
# Set a random READING_API_KEY and your own GOODREADS_USER_ID in .env
docker compose up --build -d
```

Compose binds to localhost and persists SQLite in a named Docker volume.

## Import your books

For the most reliable input, export CSV from https://www.goodreads.com/review/import and run:

```sh
curl -X POST http://127.0.0.1:8000/import/csv -H "X-API-Key: YOUR_SECRET" -F "file=@goodreads_library_export.csv"
```

Optionally try Goodreads public RSS (which may be unavailable or incomplete):

```sh
curl -X POST http://127.0.0.1:8000/sync/goodreads -H "X-API-Key: YOUR_SECRET"
```

All routes except `GET /health` require `X-API-Key`.

| Route | Purpose |
|---|---|
| `GET /health` | Basic health check |
| `GET /books?shelf=read&min_rating=4` | Search/filter/paginate collection |
| `GET /books/{book_id}` | Book details |
| `GET /stats` | Totals and ratings |
| `POST /import/csv` | Import Goodreads library export |
| `POST /sync/goodreads` | Best-effort public RSS sync |

Open `/docs` for API docs.

## Development

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Limitations

- Goodreads no longer offers its historical public developer API. Public RSS can be blocked or incomplete. CSV is the dependable fallback.
- RSS updates are additive; deleted books and shelf removals are not reconciled automatically.
- One library per service instance, with one shared API key; no multi-user accounts or automatic ChatGPT integration yet.
- Do not commit API keys, your library CSV, or SQLite files. Before exposing publicly, implement TLS, stronger authentication, rate limiting, and a persistent database host. Vercel ephemeral functions are not suitable for local SQLite state.
