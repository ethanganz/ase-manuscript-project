"""Whole-page recognition: split into lines -> TrOCR -> rerank (de/la) -> place spans.

Same models, configs and scoring as the scripts in ../scripts, but every model is
loaded once so the service can handle page after page.
"""
import json
import os
import sys
from pathlib import Path

from PIL import Image

from service.segment import find_lines

ROOT = Path(__file__).resolve().parents[1]
# The GLiNER snapshot is read from the local cache only, as in extract_places.py.
os.environ["HF_HOME"] = str(ROOT / ".cache/huggingface")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.path.insert(0, str(ROOT / "scripts"))

from extract_places import windows  # noqa: E402
from historical_aliases import HistoricalAliases  # noqa: E402
from rerank_htr import choose  # noqa: E402

LANGUAGES = ("de", "la")
CANDIDATES = 8  # beam candidates kept for reranking, as in transcribe_images.py


class Pipeline:
    def __init__(self, model_dir: Path, device: str = "auto", batch_size: int = 4):
        import torch
        from gliner import GLiNER
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        if not model_dir.is_dir():
            raise RuntimeError(f"Model directory {model_dir} is missing; see htr/README.md")
        htr_cfg = json.loads((ROOT / "configs/htr_inference.json").read_text(encoding="utf-8"))
        self.generation = {
            k: htr_cfg[k] for k in ["num_beams", "max_new_tokens", "do_sample", "use_cache"]
        }
        self.place_cfg = json.loads(
            (ROOT / "configs/place_inference.json").read_text(encoding="utf-8")
        )
        self.lm_stats = json.loads(
            (ROOT / "data/reranker_char3_word1.json").read_text(encoding="utf-8")
        )
        snapshot = (
            ROOT
            / ".cache/huggingface/hub"
            / ("models--" + self.place_cfg["model_id"].replace("/", "--"))
            / "snapshots"
            / self.place_cfg["revision"]
        )
        if not snapshot.is_dir():
            raise RuntimeError("GLiNER snapshot is missing; run scripts/download_model.py")
        # GLiNER also needs its backbone's tokenizer. On Windows the download can stop
        # half-way (no symlink permission); running the script again finishes it.
        backbone = ROOT / ".cache/huggingface/hub/models--microsoft--mdeberta-v3-base/snapshots"
        if not any(backbone.glob("*/config.json")):
            raise RuntimeError(
                "GLiNER tokenizer (mdeberta-v3-base) is incomplete; run scripts/download_model.py"
                " again"
            )

        self.torch = torch
        self.device = (
            ("cuda" if torch.cuda.is_available() else "cpu") if device == "auto" else device
        )
        self.batch_size = batch_size
        self.processor = TrOCRProcessor.from_pretrained(
            str(model_dir), local_files_only=True, use_fast=False
        )
        self.htr = (
            VisionEncoderDecoderModel.from_pretrained(str(model_dir), local_files_only=True)
            .to(self.device)
            .eval()
        )
        torch.manual_seed(42)
        self.gliner = GLiNER.from_pretrained(str(snapshot)).to("cpu").eval()
        self.matchers = [
            HistoricalAliases(json.loads((ROOT / path).read_text(encoding="utf-8")))
            for path in self.place_cfg["lexicons"]
        ]

    def _read_lines(self, crops: list[Image.Image], rerank: bool) -> list[list[dict]]:
        """Beam candidates per line image, best model score first."""
        per_line = CANDIDATES if rerank else 1
        results = []
        for i in range(0, len(crops), self.batch_size):
            batch = crops[i : i + self.batch_size]
            pixels = self.processor(images=batch, return_tensors="pt").pixel_values.to(self.device)
            generated = self.htr.generate(
                pixels,
                **self.generation,
                num_return_sequences=per_line,
                return_dict_in_generate=True,
                output_scores=rerank,
            )
            texts = [
                t.strip()
                for t in self.processor.batch_decode(generated.sequences, skip_special_tokens=True)
            ]
            scores = generated.sequences_scores.cpu().tolist() if rerank else [0.0] * len(texts)
            for j in range(len(batch)):
                chunk = slice(j * per_line, (j + 1) * per_line)
                results.append(
                    [{"text": t, "model_score": s} for t, s in zip(texts[chunk], scores[chunk])]
                )
        return results

    def _places(self, text: str, line_id: str) -> list[dict]:
        """Place spans in one line, as extract_places.py finds them."""
        mentions: dict[tuple[int, int], dict] = {}
        if not text.strip():
            return []
        cfg = self.place_cfg
        for start, end in windows(text, cfg["window_words"], cfg["overlap_words"]):
            chunk = text[start:end]
            for ent in self.gliner.predict_entities(chunk, cfg["labels"], threshold=cfg["threshold"]):
                if ent["label"] != "location":
                    continue
                x, y = ent["start"] + start, ent["end"] + start
                mentions[x, y] = {
                    "start": x,
                    "end": y,
                    "text": text[x:y],
                    "sources": ["gliner"],
                    "score": ent["score"],
                }
        for matcher in self.matchers:
            for alias in matcher.extract(text, line_id):
                identities = [
                    {
                        "official_place_id": c["official_place_id"],
                        "canonical_name": c["canonical_name"],
                        "latitude": c["latitude"],
                        "longitude": c["longitude"],
                    }
                    for c in alias["candidates"]
                ]
                for seg in alias["segments"]:
                    x, y = seg["start"], seg["end"]
                    mention = mentions.setdefault(
                        (x, y), {"start": x, "end": y, "text": text[x:y], "sources": []}
                    )
                    if "official_source_variant" not in mention["sources"]:
                        mention["sources"].append("official_source_variant")
                    known = {i["official_place_id"] for i in mention.setdefault("identities", [])}
                    mention["identities"] += [
                        i for i in identities if i["official_place_id"] not in known
                    ]
        return sorted(mentions.values(), key=lambda m: (m["start"], m["end"]))

    def recognize(self, page: Image.Image, language: str | None) -> dict:
        """Text and place candidates for every line found on the page."""
        page = page.convert("RGB")
        boxes = find_lines(page)
        rerank = language in LANGUAGES
        with self.torch.inference_mode():
            candidates = self._read_lines([page.crop(b) for b in boxes], rerank)
            lines = []
            for n, (box, cands) in enumerate(zip(boxes, candidates), 1):
                raw = cands[0]["text"]
                text = choose(cands, language, self.lm_stats)[0]["text"] if rerank else raw
                lines.append(
                    {
                        "bbox": list(box),
                        "text": text,
                        "raw_text": raw,
                        "places": self._places(text, f"line-{n}"),
                    }
                )
        return {
            "language": language if rerank else None,
            "reranked": rerank,
            "lines": lines,
            "verification_status": "Unverified HTR output",
            "geographic_identity_status": "Not resolved or verified",
        }
