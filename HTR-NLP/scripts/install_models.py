"""Install every model the HTR service needs into models/. Safe to run again.

  models/bullinger_public_trocr      handwriting model (~2.2 GB, from Hugging Face)
  models/bullinger_mbert_20261022    place finder (~680 MB, from the GitHub release)

Anything already installed is skipped, so after the first run this finishes in a
second. Used by the `htr-models` service in docker-compose.yml; it also works by hand:

  python scripts/install_models.py
"""
import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import download_public_trocr as trocr  # noqa: E402

MODELS = ROOT / "models"
MBERT_DIR = MODELS / "bullinger_mbert_20261022"
MBERT_URL = (
    "https://github.com/sssstong55t-sudo/Bullinger_htr/releases/download/"
    "v1.0.0-mbert-20261022/bullinger_mbert_20261022.zip"
)
MBERT_ZIP_SHA256 = "92cd0da3f00234a9045831ed5ca70c6c7b43d8b310fc681b1df104ed12a88683"


def install_trocr() -> None:
    ready = (trocr.MODEL_DIR / "pytorch_model.bin").is_file() and (
        trocr.TOKENIZER_DIR / "vocab.json"
    ).is_file()
    if ready:
        print("TrOCR: already installed")
        return
    print("TrOCR: downloading (about 2.2 GB) ...", flush=True)
    trocr.main()


def install_mbert() -> None:
    if (MBERT_DIR / "model.safetensors").is_file():
        print("mBERT: already installed")
        return
    MODELS.mkdir(parents=True, exist_ok=True)
    archive = MODELS / "bullinger_mbert_20261022.zip"
    print("mBERT: downloading (about 680 MB) ...", flush=True)
    urllib.request.urlretrieve(MBERT_URL, archive)
    digest = hashlib.sha256()
    with archive.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != MBERT_ZIP_SHA256:
        archive.unlink()
        raise SystemExit("mBERT download is corrupt (SHA-256 mismatch); run again")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(MODELS)
    archive.unlink()
    if not (MBERT_DIR / "model.safetensors").is_file():
        raise SystemExit(f"Expected {MBERT_DIR}/model.safetensors after unzipping")
    print("mBERT: installed")


if __name__ == "__main__":
    install_trocr()
    install_mbert()
    print("All models ready.")
