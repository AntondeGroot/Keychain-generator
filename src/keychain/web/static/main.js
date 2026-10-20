// Wires the page together: picture, colours, mask, sizes and ring go to the server, the preview comes back.

import { ColourList } from "./colours.js";
import { Painter } from "./painter.js";
import { Preview } from "./preview.js";

const PREVIEW_DELAY_MS = 600; // waits for a pause in typing or painting before asking the server
const NEW_COLOUR = "#888888";

const element = (id) => document.getElementById(id);
const state = { image: null, name: "keychain", hole: null };
let previewTimer = null;
let latestRequest = 0;
let requestsInFlight = 0;

const painter = new Painter(
  element("painter"),
  element("picture-canvas"),
  { paint: element("paint-canvas"), mask: element("mask-canvas"), detail: element("detail-canvas") },
  element("lines-canvas"),
  schedulePreview,
);
const colours = new ColourList(element("colours"), coloursChanged, choosePaintColour);
const preview = new Preview(element("preview"), placeRing);

element("picture").addEventListener("change", (event) => loadPicture(event.target.files[0]));
element("add-colour").addEventListener("click", () => colours.add(NEW_COLOUR));
element("pick-colour").addEventListener("click", togglePicking);
element("clear-mask").addEventListener("click", () => {
  painter.clear();
  schedulePreview();
});
element("brush").addEventListener("input", (event) => painter.setBrushSize(Number(event.target.value)));
element("place-ring").addEventListener("click", () => setPlacing(!preview.placing));
element("auto-ring").addEventListener("click", () => placeRing(null));
element("download").addEventListener("click", download);
for (const input of document.querySelectorAll("[data-spec]")) input.addEventListener("change", schedulePreview);
element("rim").addEventListener("change", schedulePreview);
for (const button of document.querySelectorAll(".tool")) button.addEventListener("click", () => chooseTool(button));

async function loadPicture(file) {
  if (!file) return;
  state.image = await asDataUrl(file);
  state.name = file.name.replace(/\.[^.]+$/, "");
  state.hole = null;
  const image = new Image();
  image.src = state.image;
  await image.decode();
  painter.load(image);
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
  const link = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(await response.blob()),
    download: `${state.name}.zip`,
  });
  link.click();
  URL.revokeObjectURL(link.href);
  setStatus("Downloaded. Open the 3MF in your slicer and give each part its filament.");
}

function designRequest() {
  const spec = {};
  for (const input of document.querySelectorAll("[data-spec]")) spec[input.dataset.spec] = Number(input.value);
  return {
    image: state.image,
    mask: painter.dataUrl("mask"),
    detail: painter.dataUrl("detail"),
    paint: painter.dataUrl("paint"),
    connections: painter.connections,
    rim: element("rim").value || null,
    colours: colours.get(),
    spec,
    hole: state.hole,
    name: state.name,
  };
}

/** POSTs JSON with the spinner showing; on an error it shows the server's message and returns null. */
async function call(path, body, waitingText) {
  showWorking(waitingText, +1);
  try {
    const response = await fetch(path, { method: "POST", body: JSON.stringify(body) });
    if (response.ok) return response;
    setStatus((await response.json()).error, "error");
  } catch (error) {
    setStatus(`The server did not answer; is 'keychain web' still running? (${error.message})`, "error");
  } finally {
    showWorking(waitingText, -1);
  }
  return null;
}

/** The spinner stays until every request has answered, also ones a newer change made stale. */
function showWorking(text, change) {
  requestsInFlight += change;
  const working = requestsInFlight > 0;
  element("working").hidden = !working;
  element("preview").setAttribute("aria-busy", String(working));
  updateDownloadButton();
  if (change > 0) {
    element("working-text").textContent = text;
    setStatus(text, "busy");
  }
}

/** Downloading needs a preview to download, and waits while the server is busy. */
function updateDownloadButton() {
  const hasPreview = element("preview").querySelector("svg") !== null;
  element("download").disabled = requestsInFlight > 0 || !hasPreview;
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
  painter.setPaintColour(hex);
  chooseTool(button);
}

/** The rim can take any named colour; the list follows the colours, keeping the choice. */
function coloursChanged() {
  const rim = element("rim");
  const chosen = rim.value;
  const choices = colours.names().map((name) => new Option(name, name, false, name === chosen));
  rim.replaceChildren(new Option("ink (darkest)", ""), ...choices);
  schedulePreview();
}

function setStatus(text, kind = "") {
  const status = element("status");
  status.textContent = text;
  status.className = kind;
}

function asDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
