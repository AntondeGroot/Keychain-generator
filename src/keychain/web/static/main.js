// Wires the page together: picture, colours, mask, sizes and ring go to the server, the preview comes back.

import { ColourList } from "./colours.js";
import { Painter } from "./painter.js";
import { Preview } from "./preview.js";
import { asDataUrl, loadedImage, projectBlob, readProject, saveFile } from "./project.js";
import { call, isBusy, setStatus, whenBusyChanges } from "./server.js";
import { PictureZoom } from "./zoom.js";

const PREVIEW_DELAY_MS = 600; // waits for a pause in typing or painting before asking the server
const NEW_COLOUR = "#888888";

const element = (id) => document.getElementById(id);
const state = { image: null, name: "keychain", hole: null };
let previewTimer = null;
let latestRequest = 0;

const painter = new Painter(
  element("painter"),
  element("picture-canvas"),
  { paint: element("paint-canvas"), mask: element("mask-canvas"), detail: element("detail-canvas") },
  { curves: element("curves-canvas"), lines: element("lines-canvas") },
  schedulePreview,
);
painter.onGuide = showGuide;
const zoom = new PictureZoom(element("zoom-viewport"), element("painter"), zoomChanged);
const colours = new ColourList(element("colours"), coloursChanged, choosePaintColour);
const preview = new Preview(element("preview"), placeRing);

element("picture").addEventListener("change", (event) => fromFileInput(event.target, loadPicture));
element("add-colour").addEventListener("click", () => colours.add(NEW_COLOUR));
element("pick-colour").addEventListener("click", togglePicking);
element("clear-mask").addEventListener("click", () => {
  painter.clear();
  schedulePreview();
});
element("brush").addEventListener("input", (event) => painter.setBrushSize(Number(event.target.value)));
element("zoom").addEventListener("input", (event) => zoom.set(Number(event.target.value) / 100));
element("zoom-reset").addEventListener("click", () => zoom.set(1));
element("place-ring").addEventListener("click", () => setPlacing(!preview.placing));
element("auto-ring").addEventListener("click", () => placeRing(null));
element("download").addEventListener("click", download);
element("save-project").addEventListener("click", () => saveFile(projectBlob(designRequest()), `${state.name}.keychain.json`));
element("open-project").addEventListener("change", (event) => fromFileInput(event.target, openProject));
for (const input of document.querySelectorAll("[data-spec]")) input.addEventListener("change", schedulePreview);
element("rim").addEventListener("change", schedulePreview);
for (const button of document.querySelectorAll(".tool")) button.addEventListener("click", () => chooseTool(button));
whenBusyChanges(updateDownloadButton);

/** Reads the chosen file, then empties the input so choosing the same file again still works. */
async function fromFileInput(input, read) {
  const [file] = input.files;
  input.value = "";
  if (file) await read(file);
}

async function loadPicture(file) {
  state.image = await asDataUrl(file);
  state.name = file.name.replace(/\.[^.]+$/, "");
  state.hole = null;
  showPicture(await loadedImage(state.image));
  element("save-project").disabled = false;
  const found = await call("/api/colours", { image: state.image }, "Finding the colours…");
  if (!found) return;
  colours.set((await found.json()).colours);
  coloursChanged();
}

function schedulePreview() {
  if (!state.image) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(updatePreview, PREVIEW_DELAY_MS);
}

async function updatePreview() {
  const request = ++latestRequest;
  const response = await call("/api/preview", designRequest(), "Making the keychain…");
  if (!response || request !== latestRequest) return; // a newer change is already on its way
  const { svg, hole } = await response.json();
  preview.show(svg);
  updateDownloadButton();
  const ring = state.hole ? "where you placed it" : "placed automatically";
  setStatus(`Ready. Keyring ${ring} at ${hole.map((mm) => mm.toFixed(1)).join(", ")} mm.`);
}

async function download() {
  const response = await call("/api/download", designRequest(), "Making the 3MF and STL files…");
  if (!response) return;
  saveFile(await response.blob(), `${state.name}.zip`);
  setStatus("Downloaded. Open the 3MF in your slicer and give each part its filament.");
}

/** Everything as it was saved: picture, paint, lines, colours, sizes, rim and ring. */
async function openProject(file) {
  try {
    const project = await readProject(file);
    Object.assign(state, { image: project.image, name: project.name, hole: project.hole ?? null });
    showPicture(await loadedImage(project.image));
    await painter.restore({ mask: project.mask, detail: project.detail, paint: project.paint }, project);
    colours.set(project.colours);
    for (const input of document.querySelectorAll("[data-spec]")) {
      if (input.dataset.spec in project.spec) input.value = project.spec[input.dataset.spec];
    }
    coloursChanged();
    element("rim").value = project.rim ?? "";
    element("save-project").disabled = false;
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function designRequest() {
  const spec = {};
  for (const input of document.querySelectorAll("[data-spec]")) spec[input.dataset.spec] = Number(input.value);
  return {
    image: state.image,
    mask: painter.dataUrl("mask"),
    detail: painter.dataUrl("detail"),
    paint: painter.dataUrl("paint"),
    ...painter.drawing,
    rim: element("rim").value || null,
    colours: colours.get(),
    spec,
    hole: state.hole,
    name: state.name,
  };
}

/** Downloading needs a preview to download, and waits while the server is busy. */
function updateDownloadButton() {
  const hasPreview = element("preview").querySelector("svg") !== null;
  element("download").disabled = isBusy() || !hasPreview;
}

function placeRing(hole) {
  state.hole = hole;
  setPlacing(false);
  schedulePreview();
}

function setPlacing(placing) {
  preview.setPlacing(placing);
  element("place-ring").setAttribute("aria-pressed", String(placing));
  if (placing) setStatus("Click in the preview where the keyring hole should go.");
}

function togglePicking() {
  const button = element("pick-colour");
  const picking = button.getAttribute("aria-pressed") !== "true";
  button.setAttribute("aria-pressed", String(picking));
  painter.pickColours(picking ? (hex) => { colours.add(hex); togglePicking(); } : null);
  if (picking) setStatus("Click on the picture to add the colour there.");
}

function chooseTool(chosen) {
  for (const button of document.querySelectorAll(".tool")) button.setAttribute("aria-pressed", String(button === chosen));
  painter.setTool(chosen.dataset.tool);
}

function choosePaintColour(button, hex) {
  const name = colours.get().find((colour) => colour.hex === hex)?.name;
  painter.setPaintColour(hex, name);
  chooseTool(button);
}

/** A new picture to paint on, seen whole. */
function showPicture(image) {
  painter.load(image);
  zoom.fit(image.naturalWidth, image.naturalHeight);
}

/** The scale above the picture follows the zoom, however it was zoomed. */
function zoomChanged(level) {
  const percent = Math.round(level * 100);
  element("zoom").value = String(percent);
  element("zoom-level").textContent = `${percent}%`;
  painter.redrawOverlays();
}

/** The guide above the picture: what to do next with the drawing tools, hidden otherwise. While
 * shown it grows to fit but never shrinks, so the picture stays put under the pointer. */
function showGuide(text) {
  const guide = element("tool-guide");
  const before = text ? guide.offsetHeight : 0;
  guide.style.minHeight = "";
  guide.textContent = text;
  guide.hidden = !text;
  if (text) guide.style.minHeight = `${Math.max(before, guide.offsetHeight)}px`;
}

/** The rim can take any named colour; the list follows the colours, keeping the choice. */
function coloursChanged() {
  const rim = element("rim");
  const chosen = rim.value;
  const choices = colours.names().map((name) => new Option(name, name, false, name === chosen));
  rim.replaceChildren(new Option("ink (darkest)", ""), ...choices);
  schedulePreview();
}
