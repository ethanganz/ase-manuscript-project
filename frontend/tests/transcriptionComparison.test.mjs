import test from "node:test";
import assert from "node:assert/strict";
import { compareTranscriptions } from "../src/tools/transcriptionComparison.js";

test("Bullinger date difference has two character errors", () => {
  const result = compareTranscriptions(
    "Basileę ultimo iulii 1549.",
    "Basileę ultimo iulii 1554.",
  );
  assert.equal(result.characterErrors, 2);
  assert.equal(
    result.referenceParts
      .filter((part) => part.changed)
      .map((part) => part.text)
      .join(""),
    "49",
  );
  assert.equal(
    result.predictionParts
      .filter((part) => part.changed)
      .map((part) => part.text)
      .join(""),
    "54",
  );
});

test("alignment preserves both strings with insertions, deletions and Unicode", () => {
  for (const [reference, prediction, errors] of [
    ["", "a", 1],
    ["ab", "a", 1],
    ["a", "ab", 1],
    ["ę😀", "ę😀", 0],
    ["Basel", "basel", 1],
  ]) {
    const result = compareTranscriptions(reference, prediction);
    assert.equal(result.characterErrors, errors);
    assert.equal(
      result.referenceParts.map((part) => part.text).join(""),
      reference,
    );
    assert.equal(
      result.predictionParts.map((part) => part.text).join(""),
      prediction,
    );
  }
  assert.equal(compareTranscriptions("", "a").cer, null);
});
