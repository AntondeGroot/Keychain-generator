// Closed curves drawn round areas of the picture, such as text to turn or a shape on the mask.

/** Whether the point is inside the closed curve, given as samples: a ray to the right crosses it
 * an odd number of times. */
export function insideCurve(samples, [x, y]) {
  let crossings = 0;
  samples.forEach(([x1, y1], index) => {
    const [x2, y2] = samples[(index + 1) % samples.length];
    if (y1 > y !== y2 > y && x < x1 + ((y - y1) * (x2 - x1)) / (y2 - y1)) crossings += 1;
  });
  return crossings % 2 === 1;
}

/** How far the point is from the closed curve's line, given as samples. */
export function distanceToCurve(samples, [x, y]) {
  return Math.min(
    ...samples.map(([x1, y1], index) => {
      const [x2, y2] = samples[(index + 1) % samples.length];
      const length2 = (x2 - x1) ** 2 + (y2 - y1) ** 2;
      const along = length2 ? Math.min(1, Math.max(0, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / length2)) : 0;
      return Math.hypot(x - (x1 + along * (x2 - x1)), y - (y1 + along * (y2 - y1)));
    }),
  );
}
