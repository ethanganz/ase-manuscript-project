# Small public-line example

Image and edition/provisional reference source: https://github.com/pstroe/bullinger-htr, original TRAIN 0–2000, Latin line 611_01_r1l31. Dataset terms in docs/DATASET_LICENSE apply. This previously inspected line is a functional example, not an independent validation sample. See docs/REPRODUCTION.md for runnable commands. Expected JSONL files are actual CPU smoke outputs with literal text and character offsets, not guaranteed predictions across every environment.

## Additional carousel examples

Three unchanged image/text pairs from the same dataset's public `sample-train`
folder are included: Latin `6_00_r1l12`, German `7_00_r1l11`, and German
`9_01_r1l10`. Selection was made before inference, using different letters;
these are illustrative training examples, not a test set or accuracy benchmark.
Language labels are supplied by the upstream dataset and may contain errors.
`carousel_references.jsonl` retains reference text with only surrounding whitespace stripped.

From `HTR-NLP/`, reproduce saved predictions with the released checkpoint:

```powershell
$env:PYTHONUTF8 = "1"
$py = ".venv/Scripts/python.exe"
& $py scripts/transcribe_images.py --model-dir .cache/carousel-model/bullinger_checkpoint --images examples/6_00_r1l12.png --save-candidates --language la --device cpu --output .cache/carousel_la_candidates.jsonl
& $py scripts/transcribe_images.py --model-dir .cache/carousel-model/bullinger_checkpoint --images examples/7_00_r1l11.png examples/9_01_r1l10.png --save-candidates --language de --device cpu --output .cache/carousel_de_candidates.jsonl
& $py scripts/rerank_htr.py --input .cache/carousel_la_candidates.jsonl --output examples/carousel_la_predictions.jsonl
& $py scripts/rerank_htr.py --input .cache/carousel_de_candidates.jsonl --output examples/carousel_de_predictions.jsonl
& $py scripts/build_carousel_examples.py
```

Use fresh output paths when rerunning. Predictions are actual model outputs, with
eight beam candidates and fixed training-text-only reranking. Reference text is
used for display/evaluation only and is never supplied to recognition or reranking.
The bundling script checks matching line identities and image SHA256 values
before producing `frontend/src/data/bullinger/additionalExamples.json`.
