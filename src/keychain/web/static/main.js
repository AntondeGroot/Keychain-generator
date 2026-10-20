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

const painter = new Painter(
  element("painter"),
  element("picture-canvas"),
  { mask: element("mask-canvas"), detail: element("detail-canvas") },
  schedulePreview,
);
const colours = new ColourList(element("colours"), schedulePreview);
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
  setStatus("Finding the colours…", "busy");
  const found = await call("/api/colours", { image: state.image });
  if (!found) return;
  colours.set((await found.json()).colours);
  schedulePreview();
}

function schedulePreview() {
  if (!state.image) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(updatePreview, PREVIEW_DELAY_MS);
}

async function updatePreview() {
  const request = ++latestRequest;
  setStatus("Making the keychain…", "busy");
  const response = await call("/api/preview", designRequest());
  if (!response || request !== latestRequest) return; // a newer change is already on its way
  const { svg, hole } = await response.json();
  preview.show(svg);
  element("download").disabled = false;
  const ring = state.hole ? "where you placed it" : "placed automatically";
  setStatus(`Ready. Keyring ${ring} at ${hole.map((mm) => mm.toFixed(1)).join(", ")} mm.`);
}

async function download() {
  setStatus("Making the files…", "busy");
  const response = await call("/api/download", designRequest());
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
    colours: colours.get(),
    spec,
    hole: state.hole,
    name: state.name,
  };
}

/** POSTs JSON; on an error it shows the server's message and returns null. */
async function call(path, body) {
  try {
    const response = await fetch(path, { method: "POST", body: JSON.stringify(body) });
    if (response.ok) return response;
    setStatus((await response.json()).error, "error");
  } catch (error) {
    setStatus(`The server did not answer; is 'keychain web' still running? (${error.message})`, "error");
  }
  return null;
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
