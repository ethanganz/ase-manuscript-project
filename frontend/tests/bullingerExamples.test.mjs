import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { compareTranscriptions } from "../src/tools/transcriptionComparison.js";

const dataDirectory = new URL("../src/data/bullinger/", import.meta.url);
const additional = JSON.parse(
  readFileSync(new URL("additionalExamples.json", dataDirectory), "utf8"),
);

test("three additional examples use distinct manuscripts and matching real source artifacts", () => {
  assert.equal(additional.length, 3);
  assert.equal(new Set(additional.map((item) => item.sourceUrl)).size, 3);
  for (const item of additional) {
    const image = readFileSync(new URL(item.imageFile, dataDirectory));
    assert.equal(image.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
    assert.equal(
      createHash("sha256").update(image).digest("hex"),
      item.imageSha256,
    );
    const references = readFileSync(
      new URL(
        "../../HTR-NLP/examples/carousel_references.jsonl",
        import.meta.url,
      ),
      "utf8",
    )
      .trim()
      .split("\n")
      .map(JSON.parse);
    const reference = references.find((row) => row.line_id === item.lineId);
    assert.equal(item.reference, reference.reference);
    const predictions = readFileSync(
      new URL(
        `../../HTR-NLP/examples/carousel_${item.language}_predictions.jsonl`,
        import.meta.url,
      ),
      "utf8",
    )
      .trim()
      .split("\n")
      .map(JSON.parse);
    const prediction = predictions.find((row) => row.line_id === item.lineId);
    assert.equal(item.prediction, prediction.text);
    assert.equal(item.imageSha256, prediction.image_sha256);
    assert.ok(
      Number.isFinite(
        compareTranscriptions(item.reference, item.prediction).cer,
      ),
    );
  }
});
