from pathlib import Path

from document_generator import save_sample


if __name__ == "__main__":
    out = save_sample(Path(__file__).resolve().parent / "outputs")
    print(out)
