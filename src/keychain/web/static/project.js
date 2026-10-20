// A project file: the picture with everything painted, drawn and set on it, to carry on later.
// It holds exactly what the page sends the server for a preview, so nothing can be left out.

const FORMAT = "keychain-project";
const VERSION = 1;

export function projectBlob(request) {
  return new Blob([JSON.stringify({ format: FORMAT, version: VERSION, ...request })], { type: "application/json" });
}

/** The project in a file; throws with a readable message for anything else. */
export async function readProject(file) {
  let project;
  try {
    project = JSON.parse(await file.text());
  } catch {
    throw new Error(`${file.name} is not a keychain project`);
  }
  if (project.format !== FORMAT) throw new Error(`${file.name} is not a keychain project`);
  if (project.version > VERSION) throw new Error(`${file.name} was saved by a newer version of this page`);
  return project;
}

export function saveFile(blob, fileName) {
  const link = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: fileName });
  link.click();
  URL.revokeObjectURL(link.href);
}

/** An image element with the picture loaded, from a data URL. */
export async function loadedImage(dataUrl) {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  return image;
}

export function asDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
