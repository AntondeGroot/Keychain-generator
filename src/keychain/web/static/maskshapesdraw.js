// Drawing the mask's shapes over the picture: their outlines dashed, the chosen one in blue, the
// shape being drawn as it is so far, the handles to drag, the corners chosen with the fillet and
// the dimensions. In picture pixels, with lines as thin on screen as at any zoom.

import { drawDimensions } from "./dimensions.js";
import { spline } from "./handdrawn.js";
import { dot, strokeLine } from "./overlays.js";
import { cornerAt, dragged, handles, outline } from "./shapekinds.js";

const LINE_SCREEN_PX = 2;
const DASH_SCREEN_PX = [6, 4];
const POINT_SCREEN_PX = 3;
const HANDLE_SCREEN_PX = 5;
const OUTLINE = "#1d1d1b";
const CHOSEN = "#00a3e0";
const HANDLE_FILL = "#ffffff";

/** shapes: the mask's shapes; the rest as MaskShapes keeps them. Only clears when not shown. */
export function drawMaskShapes(canvas, scale, { shown, shapes, chosen, filleted, drawing, pointer, pixelMm }) {
  const context = canvas.getContext("2d");
  const toPicture = context.getTransform(); // the canvas can be sharper than the picture
  context.resetTransform();
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.setTransform(toPicture);
  if (!shown) return;
  context.lineWidth = LINE_SCREEN_PX * scale;
  context.setLineDash(DASH_SCREEN_PX.map((length) => length * scale));
  for (const shape of shapes) strokeLine(context, outline(shape), shape === chosen ? CHOSEN : OUTLINE, true);
  if (drawing) strokeLine(context, drawnSoFar(drawing, pointer), OUTLINE, !drawing.points);
  context.setLineDash([]);
  for (const [x, y] of drawing?.points ?? []) dot(context, x, y, POINT_SCREEN_PX * scale, OUTLINE);
  if (drawing) return;
  for (const { at: [x, y] } of shapes.flatMap(handles)) dot(context, x, y, HANDLE_SCREEN_PX * scale, HANDLE_FILL, OUTLINE);
  for (const { step, corner } of filleted) dot(context, ...cornerAt(step, corner), HANDLE_SCREEN_PX * scale, CHOSEN, OUTLINE);
  if (pixelMm) drawDimensions(context, shapes, pixelMm, scale);
}

/** The shape being drawn as it is so far: a spline runs on to the pointer. */
function drawnSoFar({ kind, points, from, to }, pointer) {
  if (points) return spline([...points, ...(pointer ? [pointer] : [])], false);
  return outline(dragged(kind, from, to));
}
