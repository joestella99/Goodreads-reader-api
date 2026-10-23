import tempfile
import unittest
from pathlib import Path
from store import connect, parse_csv, parse_rss, upsert, public_book

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><item>
<book_id>123</book_id><title>Example Book</title><author_name>A. Writer</author_name>
<user_rating>5</user_rating><user_shelves>favorite, sci-fi</user_shelves>
</item></channel></rss>"""
CSV = b"""Book Id,Title,Author,My Rating,Exclusive Shelf,Bookshelves,Date Read,Date Added,My Review,ISBN
123,Example Book,A. Writer,5,read,favorite,2026/10/23,2026/10/22,Great,1234567890
"""

class ParserTests(unittest.TestCase):
    def test_rss(self):
        books = parse_rss(RSS, "read")
        self.assertEqual(books[0]["rating"], 5)
        self.assertEqual(books[0]["shelves"], ["read", "favorite", "sci-fi"])

    def test_csv(self):
        books = parse_csv(CSV)
        self.assertEqual(books[0]["book_id"], "123")
        self.assertIn("read", books[0]["shelves"])

    def test_merge(self):
        with tempfile.TemporaryDirectory() as directory:
            with connect(Path(directory) / "test.db") as db:
                upsert(db, parse_csv(CSV))
                upsert(db, parse_rss(RSS, "read"))
                row = db.execute("SELECT * FROM books WHERE book_id='123'").fetchone()
                self.assertEqual(public_book(row)["rating"], 5)
                self.assertIn("sci-fi", public_book(row)["shelves"])

    def test_invalid_csv(self):
        with self.assertRaises(ValueError):
            parse_csv(b"a,b\n1,2\n")

if __name__ == "__main__":
    unittest.main()
