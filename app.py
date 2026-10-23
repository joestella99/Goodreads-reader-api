"""Unofficial single-library Goodreads reader API."""
import hmac
import os
from collections import Counter
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from store import USER_ID, SHELVES, connect, fetch_public_shelf, parse_csv, public_book, upsert

app = FastAPI(title="Goodreads Reader API", version="0.1.0")

def require_key(x_api_key: str | None = Header(None)):
    expected = os.environ.get("READING_API_KEY")
    if not expected:
        raise HTTPException(503, "Set READING_API_KEY")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(401, "Invalid API key")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/books", dependencies=[Depends(require_key)])
def list_books(shelf: str | None = None, min_rating: int | None = Query(None, ge=1, le=5),
               search: str | None = None, limit: int = Query(50, ge=1, le=500),
               offset: int = Query(0, ge=0)):
    with connect() as db:
        books = [public_book(row) for row in db.execute("SELECT * FROM books ORDER BY date_added DESC, title")]
    if shelf:
        books = [b for b in books if shelf in b["shelves"]]
    if min_rating is not None:
        books = [b for b in books if (b["rating"] or 0) >= min_rating]
    if search:
        q = search.casefold()
        books = [b for b in books if q in b["title"].casefold() or q in b["author"].casefold()]
    return {"total": len(books), "items": books[offset:offset+limit]}

@app.get("/books/{book_id}", dependencies=[Depends(require_key)])
def book_detail(book_id: str):
    with connect() as db:
        row = db.execute("SELECT * FROM books WHERE book_id=?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Book not found")
    return public_book(row)

@app.get("/stats", dependencies=[Depends(require_key)])
def stats():
    with connect() as db:
        books = [public_book(row) for row in db.execute("SELECT * FROM books")]
    return {"books": len(books), "shelves": dict(Counter(s for b in books for s in b["shelves"])),
            "ratings": dict(sorted(Counter(b["rating"] for b in books if b["rating"]).items())),
            "unrated": sum(b["rating"] is None for b in books)}

@app.post("/sync/goodreads", dependencies=[Depends(require_key)])
def sync():
    if not USER_ID:
        raise HTTPException(503, "Set GOODREADS_USER_ID before RSS sync")
    synced, errors = {}, {}
    with connect() as db:
        for shelf in SHELVES:
            try:
                books = fetch_public_shelf(USER_ID, shelf)
                synced[shelf] = upsert(db, books)
            except Exception as exc:
                errors[shelf] = str(exc)
    if errors and not synced:
        raise HTTPException(502, {"message": "RSS unavailable; use CSV import", "errors": errors})
    return {"profile_id": USER_ID, "synced": synced, "errors": errors}

@app.post("/import/csv", dependencies=[Depends(require_key)])
async def import_csv(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Upload a Goodreads .csv export")
    payload = await file.read(12_000_001)
    try:
        books = parse_csv(payload)
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    with connect() as db:
        imported = upsert(db, books)
    return {"imported": imported}
