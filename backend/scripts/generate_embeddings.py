import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from features.embeddings import embed_missing_content


def main():
    db = SessionLocal()
    try:
        result = embed_missing_content(db)
        db.commit()
        print(f"Embedded {result['embedded']} content rows. Skipped {result['skipped_empty_text']} with no title/caption text.")
    finally:
        db.close()


if __name__ == "__main__":
    main()