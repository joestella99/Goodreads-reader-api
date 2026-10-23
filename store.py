"""Import Goodreads CSV and public RSS into local SQLite; no Goodreads credentials needed."""
import csv
import io
import json
import os
import re
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

USER_ID = os.environ.get("GOODREADS_USER_ID", "").strip()
SHELVES = ("read", "currently-reading", "to-read")
DB_FILE = Path(os.environ.get("READING_DB_PATH", str(Path(__file__).resolve().parent / "books.sqlite3")))

def connect(db_path=DB_FILE):
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS books (
        book_id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL DEFAULT '',
        rating INTEGER, date_read TEXT, date_added TEXT, review TEXT,
        isbn TEXT, url TEXT, shelves TEXT NOT NULL DEFAULT '[]',
        source TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    db.commit()
    return db

def clean(value):
    return (value or "").strip()

def parse_rss(payload: bytes, shelf: str):
    root = ET.fromstring(payload)
    if root.tag != "rss":
        raise ValueError("Not an RSS feed")
    result = []
    for item in root.findall("./channel/item"):
        def get(key):
            return clean(item.findtext(key))
        book_id = get("book_id")
        if not book_id.isdigit() or not get("title"):
            continue
        rating = get("user_rating")
        tags = [v.strip() for v in get("user_shelves").split(",") if v.strip()]
        result.append(dict(book_id=book_id, title=get("title"), author=get("author_name"),
            rating=int(rating) if rating.isdigit() and 1 <= int(rating) <= 5 else None,
            date_read=get("user_read_at"), date_added=get("user_date_added"),
            review=get("user_review"), isbn=get("isbn"),
            url=get("link") or f"https://www.goodreads.com/book/show/{book_id}",
            shelves=list(dict.fromkeys([shelf] + tags)), source="rss"))
    return result

def parse_csv(payload: bytes):
    if len(payload) > 12_000_000:
        raise ValueError("CSV exceeds 12 MB maximum")
    rows = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    if not rows.fieldnames or "Book Id" not in rows.fieldnames or "Title" not in rows.fieldnames:
        raise ValueError("Expected a Goodreads export with Book Id and Title columns")
    result = []
    for row in rows:
        book_id, title = clean(row.get("Book Id")), clean(row.get("Title"))
        if not book_id.isdigit() or not title:
            continue
        rating = clean(row.get("My Rating"))
        shelves = [s.strip() for s in clean(row.get("Bookshelves")).split(",") if s.strip()]
        if clean(row.get("Exclusive Shelf")):
            shelves.insert(0, clean(row["Exclusive Shelf"]))
        result.append(dict(book_id=book_id, title=title, author=clean(row.get("Author")),
            rating=int(rating) if rating.isdigit() and 1 <= int(rating) <= 5 else None,
            date_read=clean(row.get("Date Read")), date_added=clean(row.get("Date Added")),
            review=clean(row.get("My Review")), isbn=clean(row.get("ISBN")).strip('="'),
            url=f"https://www.goodreads.com/book/show/{book_id}",
            shelves=list(dict.fromkeys(shelves)), source="csv"))
    return result

def upsert(db, books):
    now = datetime.now(timezone.utc).isoformat()
    for book in books:
        old = db.execute("SELECT * FROM books WHERE book_id=?", (book["book_id"],)).fetchone()
        shelves = book["shelves"]
        if old and book["source"] == "rss":
            shelves = list(dict.fromkeys(json.loads(old["shelves"]) + shelves))
        values = {key: book.get(key) or (old[key] if old else None) for key in
            ("title", "author", "rating", "date_read", "date_added", "review", "isbn", "url")}
        db.execute("""INSERT INTO books
            (book_id,title,author,rating,date_read,date_added,review,isbn,url,shelves,source,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(book_id) DO UPDATE SET
            title=excluded.title,author=excluded.author,rating=excluded.rating,
            date_read=excluded.date_read,date_added=excluded.date_added,
            review=excluded.review,isbn=excluded.isbn,url=excluded.url,
            shelves=excluded.shelves,source=excluded.source,updated_at=excluded.updated_at""",
            (book["book_id"], values["title"], values["author"] or "", values["rating"],
            values["date_read"], values["date_added"], values["review"], values["isbn"],
            values["url"], json.dumps(shelves), book["source"], now))
    db.commit()
    return len(books)

def fetch_public_shelf(user_id, shelf, max_pages=20, per_page=50):
    if not re.fullmatch(r"\d{1,20}", user_id):
        raise ValueError("Invalid Goodreads user ID")
    if shelf not in SHELVES:
        raise ValueError("Invalid Goodreads shelf")
    books, seen = [], set()
    for page in range(1, max_pages + 1):
        query = urlencode(dict(shelf=shelf, page=page, per_page=per_page))
        url = f"https://www.goodreads.com/review/list_rss/{user_id}?{query}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "PersonalReadingSync/0.1 (read-only)",
            "Accept": "application/rss+xml, application/xml, text/xml"})
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError("RSS response too large")
        batch = parse_rss(payload, shelf)
        unseen = [book for book in batch if book["book_id"] not in seen]
        if not unseen:
            break
        books.extend(unseen)
        seen.update(book["book_id"] for book in unseen)
        if len(batch) < per_page:
            break
    return books

def public_book(row):
    result = dict(row)
    result["shelves"] = json.loads(result["shelves"])
    return result
