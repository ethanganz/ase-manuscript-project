// Literal Unicode character comparison, matching the HTR evaluator's policy.
export function compareTranscriptions(reference, prediction) {
  const a = Array.from(reference);
  const b = Array.from(prediction);
  const costs = Array.from({ length: a.length + 1 }, () =>
    Array(b.length + 1).fill(0),
  );
  for (let i = 0; i <= a.length; i++) costs[i][0] = i;
  for (let j = 0; j <= b.length; j++) costs[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      costs[i][j] = Math.min(
        costs[i - 1][j] + 1,
        costs[i][j - 1] + 1,
        costs[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
  }
  const referenceParts = [];
  const predictionParts = [];
  let i = a.length;
  let j = b.length;
  while (i || j) {
    if (
      i &&
      j &&
      costs[i][j] === costs[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)
    ) {
      const changed = a[i - 1] !== b[j - 1];
      referenceParts.push({ text: a[--i], changed });
      predictionParts.push({ text: b[--j], changed });
    } else if (i && costs[i][j] === costs[i - 1][j] + 1) {
      referenceParts.push({ text: a[--i], changed: true });
    } else {
      predictionParts.push({ text: b[--j], changed: true });
    }
  }
  return {
    referenceParts: referenceParts.reverse(),
    predictionParts: predictionParts.reverse(),
    characterErrors: costs[a.length][b.length],
    cer: a.length ? costs[a.length][b.length] / a.length : null,
  };
}
