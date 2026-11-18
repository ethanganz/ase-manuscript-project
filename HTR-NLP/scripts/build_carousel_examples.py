"""Bundle saved predictions and references for the frontend manuscript carousel."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT.parent / "frontend/src/data/bullinger"


def main():
    references = [json.loads(line) for line in (ROOT / "examples/carousel_references.jsonl").read_text(encoding="utf-8").splitlines()]
    predictions = {}
    for language in ("la", "de"):
        for line in (ROOT / f"examples/carousel_{language}_predictions.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            row["line_id"] = row["line_id"].replace("\\", "/")
            if row["line_id"] in predictions:
                raise ValueError("Duplicate prediction")
            predictions[row["line_id"]] = row
    if set(predictions) != {r["line_id"] for r in references}:
        raise ValueError("Prediction/reference IDs differ")
    records = []
    for reference in references:
        prediction = predictions[reference["line_id"]]
        image = ROOT / reference["line_id"]
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest != prediction["image_sha256"]:
            raise ValueError("Image/prediction hash mismatch")
        letter, page, line = image.stem.split("_")
        language = reference["language"]
        shutil.copyfile(image, FRONTEND / image.name)
        records.append({
            "lineId": reference["line_id"],
            "language": language,
            "reference": reference["reference"],
            "prediction": prediction["text"],
            "imageFile": image.name,
            "imageSha256": digest,
            "title": f"Letter {letter} / {'Latin' if language == 'la' else 'German'} / {line}",
            "sourceUrl": f"https://www.bullinger-digital.ch/letter/{letter}",
            "sourcePath": f"sample-train/{language}/{image.name}",
            "generation": prediction["generation"],
            "reranking": prediction["reranking"],
        })
    (FRONTEND / "additionalExamples.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Bundled {len(records)} additional real manuscript comparisons")


if __name__ == "__main__":
    main()
