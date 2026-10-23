// The canvases drawn over the picture, such as lines and curves, follow its size on screen, not
// the picture's, so they stay thin and sharp however far it is zoomed. They draw in picture pixels,
// with the lines and dots here.

const SHARPEST_OVERLAY_PX = 4096; // drawn this sharp at most, along the longest side

/** Sizes the canvases over the picture to the screen; what they show must be drawn again. */
export function sizeOverlays(canvases, picture, canvasPxPerScreenPx) {
  const { width, height } = picture;
  const screenPxPerPicturePx = devicePixelRatio / canvasPxPerScreenPx;
  const sharpness = Math.min(screenPxPerPicturePx, SHARPEST_OVERLAY_PX / Math.max(width, height));
  for (const canvas of canvases) {
    canvas.width = Math.round(width * sharpness);
    canvas.height = Math.round(height * sharpness);
    canvas.getContext("2d").setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
  }
}

/** A line through the samples, in picture pixels, closed back to the first when asked. */
export function strokeLine(context, samples, colour, closed) {
  context.strokeStyle = colour;
  context.beginPath();
  samples.forEach(([x, y], index) => (index ? context.lineTo(x, y) : context.moveTo(x, y)));
  if (closed) context.closePath();
  context.stroke();
}

/** A filled dot, with an outline when given one. */
export function dot(context, x, y, radius, fill, outline = null) {
  context.fillStyle = fill;
  context.beginPath();
  context.arc(x, y, radius, 0, 2 * Math.PI);
  context.fill();
  if (!outline) return;
  context.strokeStyle = outline;
  context.stroke();
}
