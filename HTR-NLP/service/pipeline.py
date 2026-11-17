"""Whole-page recognition with every model loaded ONCE (for the web backend).

Same steps, models and settings as scripts/run_page_pipeline.py:
    contour line splitting -> public Bullinger TrOCR (one line at a time)
    -> mBERT place finder + historical place-name lists

run_page_pipeline.py starts a new Python program for every page and so loads
about 3 GB of models every time. This class keeps them in memory, so a page
costs only the time to read its lines.
"""
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('HF_HOME', str(ROOT / '.cache/huggingface'))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'outputs/bullinger_htr_delivery/scripts'))

from extract_places import add_alias_candidates, finalize_mentions, whole_word  # noqa: E402
from page_segmentation_loose import _polygon_crop, find_line_polygons  # noqa: E402

TROCR_DIR = ROOT / 'models/bullinger_public_trocr'
MBERT_DIR = ROOT / 'models/bullinger_mbert_20261022'
COORDINATE_SYSTEM = 'EXIF-oriented pixels; left, top, right, bottom; right/bottom exclusive'


class NoLinesFound(Exception):
    """The page has no detectable lines of handwriting."""


def assemble_places(text, line_id, neural_spans, matchers):
    """Place mentions of one line: mBERT spans plus historical-name matches.

    Identical to what scripts/extract_places.py does in its default (mBERT) mode,
    including the whole-word filter and the candidate / ambiguous / unmatched status.
    """
    mentions = {}
    for span in neural_spans:
        key = (span['start'], span['end'])
        mentions[key] = dict(start=key[0], end=key[1], text=span['text'],
                             sources=['mbert'], score=span['score'])
    if text.strip():
        for matcher in matchers:
            for alias in matcher.extract(text, line_id):
                for seg in alias['segments']:
                    start, end = seg['start'], seg['end']
                    mention = mentions.setdefault(
                        (start, end), {'start': start, 'end': end, 'text': text[start:end], 'sources': []})
                    add_alias_candidates(mention, alias['candidates'])
    mentions = {key: m for key, m in mentions.items() if whole_word(text, *key)}
    return finalize_mentions(mentions)


def upright_page(image):
    """Rotate by EXIF and put transparent pixels on white, as the page script does."""
    oriented = ImageOps.exif_transpose(image).convert('RGBA')
    return Image.alpha_composite(Image.new('RGBA', oriented.size, 'white'), oriented).convert('RGB')


class Pipeline:
    def __init__(self, device='auto', batch_size=1):
        import torch
        from transformers import (AutoConfig, AutoModelForTokenClassification, AutoTokenizer,
                                  RobertaTokenizerFast, TrOCRProcessor, ViTImageProcessor,
                                  VisionEncoderDecoderModel)
        from historical_aliases import HistoricalAliases
        from mbert_inference import LABELS

        missing = [str(p) for p in (TROCR_DIR / 'pytorch_model.bin', TROCR_DIR / 'tokenizer/vocab.json',
                                    MBERT_DIR / 'model.safetensors') if not p.is_file()]
        if missing:
            raise RuntimeError('Install the models first (see README). Missing: ' + ', '.join(missing))

        htr_cfg = json.loads((ROOT / 'configs/htr_inference.json').read_text(encoding='utf-8'))
        self.generation = {k: htr_cfg[k] for k in ['num_beams', 'max_new_tokens', 'do_sample', 'use_cache']}
        self.generation['use_cache'] = True  # same as the public-checkpoint default
        place_cfg = json.loads((ROOT / 'configs/place_inference.json').read_text(encoding='utf-8'))

        self.torch = torch
        self.device = ('cuda' if torch.cuda.is_available() else 'cpu') if device == 'auto' else device
        self.batch_size = max(1, batch_size)

        tokenizer = RobertaTokenizerFast.from_pretrained(TROCR_DIR / 'tokenizer', local_files_only=True)
        image_processor = ViTImageProcessor.from_pretrained(TROCR_DIR, local_files_only=True)
        self.processor = TrOCRProcessor(image_processor=image_processor, tokenizer=tokenizer)
        self.htr = VisionEncoderDecoderModel.from_pretrained(str(TROCR_DIR), local_files_only=True).to(self.device).eval()
        self.htr.generation_config.decoder_start_token_id = self.htr.config.decoder_start_token_id
        self.htr.generation_config.pad_token_id = tokenizer.pad_token_id
        self.htr.generation_config.eos_token_id = tokenizer.sep_token_id

        config = AutoConfig.from_pretrained(MBERT_DIR, local_files_only=True)
        if config.model_type != 'bert' or config.id2label != dict(enumerate(LABELS)):
            raise RuntimeError('Expected a BERT token classifier with O, B-LOC, and I-LOC labels')
        self.ner_tokenizer = AutoTokenizer.from_pretrained(MBERT_DIR, local_files_only=True, use_fast=True)
        if not self.ner_tokenizer.is_fast:
            raise RuntimeError('mBERT requires a fast tokenizer for character offsets')
        self.ner = AutoModelForTokenClassification.from_pretrained(MBERT_DIR, local_files_only=True).eval()
        torch.manual_seed(42)

        self.matchers = [HistoricalAliases(json.loads((ROOT / path).read_text(encoding='utf-8')))
                         for path in place_cfg['lexicons']]

    def _read_lines(self, crops):
        texts = []
        with self.torch.inference_mode():
            for start in range(0, len(crops), self.batch_size):
                batch = crops[start:start + self.batch_size]
                pixels = self.processor(images=batch, return_tensors='pt').pixel_values.to(self.device)
                generated = self.htr.generate(pixels, **self.generation, num_return_sequences=1,
                                              return_dict_in_generate=True, output_scores=False)
                texts += [t.strip() for t in self.processor.batch_decode(
                    generated.sequences, skip_special_tokens=True)]
        return texts

    def _find_spans(self, texts):
        from mbert_inference import predict
        spans = [[] for _ in texts]
        filled = [i for i, text in enumerate(texts) if text.strip()]
        for start in range(0, len(filled), 32):
            chunk = filled[start:start + 32]
            rows = [{'text': texts[i]} for i in chunk]
            for i, result in zip(chunk, predict(self.ner, self.ner_tokenizer, rows)):
                spans[i] = result['mentions']
        return spans

    def recognize(self, image):
        """Read one page image. Returns the same lines/places as page_response.json."""
        page = upright_page(image)
        polygons = find_line_polygons(page)
        if not polygons:
            raise NoLinesFound('No text lines found on this page')
        cropped = [_polygon_crop(page, polygon) for polygon in polygons]
        texts = self._read_lines([crop for _, crop in cropped])
        with self.torch.inference_mode():
            spans = self._find_spans(texts)
        lines = []
        for number, ((box, _), polygon, text, found) in enumerate(zip(cropped, polygons, texts, spans), 1):
            line_id = f'line_{number:04d}'
            lines.append({
                'line_id': line_id,
                'bbox': [int(v) for v in box],
                'polygon': [[int(x), int(y)] for x, y in polygon],
                'text': text,
                'places': assemble_places(text, line_id, found, self.matchers),
            })
        return {
            'page': {'width': page.width, 'height': page.height, 'coordinate_system': COORDINATE_SYSTEM,
                     'reading_order': 'top-to-bottom, single column'},
            'pipeline': {'htr_model': 'pstroe/bullinger-general-model', 'segmentation': 'contours',
                         'place_extraction_mode': 'mbert_with_aliases'},
            'lines': lines,
        }
