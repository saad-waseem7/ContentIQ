import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from features.baselines import compute_and_store_baselines


def main():
    db = SessionLocal()
    try:
        count = compute_and_store_baselines(db)
        db.commit()
        print(f"Computed and stored {count} user_baseline rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()