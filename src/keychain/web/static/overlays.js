// The canvases drawn over the picture, such as lines and curves, follow its size on screen, not
// the picture's, so they stay thin and sharp however far it is zoomed. They draw in picture pixels.

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
