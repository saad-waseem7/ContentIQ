import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from features.builder import build_feature_table
from ml.artifact_io import atomic_path

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "features.parquet"


def main():
    db = SessionLocal()
    try:
        df = build_feature_table(db)
    finally:
        db.close()

    df["content_id"] = df["content_id"].astype(str)
    df["user_id"] = df["user_id"].astype(str)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with atomic_path(OUTPUT_PATH) as tmp_path:
        df.to_parquet(tmp_path, index=False)
    print(f"Feature table built: {len(df)} rows, {len(df.columns)} columns. Saved to {OUTPUT_PATH}")
    print(f"Rows with valid label_overperformer: {df['label_overperformer'].notna().sum()}")


if __name__ == "__main__":
    main()