"""Explicit online setup; runtime never downloads model artifacts."""
import argparse
from pathlib import Path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", default="data/models/all-MiniLM-L6-v2")
    args = parser.parse_args()
    from sentence_transformers import SentenceTransformer
    path = Path(args.destination)
    path.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", cache_folder=str(path.parent / "cache"), device="cpu", trust_remote_code=False)
    model.save(str(path))
    print(f"Model saved locally to {path.resolve()}. Set NAVYLINK_MODEL_PATH to this directory.")
