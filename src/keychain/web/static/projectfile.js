// The file the project lives in: the one it was opened from or last saved to. Save writes over
// it; Save as asks for a name and a folder. Browsers that cannot write files (Firefox, Safari)
// ask for a name and download instead, so there every save is a Save as.

import { saveFile } from "./project.js";

const TYPES = [{ description: "Keychain project", accept: { "application/json": [".json"] } }];
const canWriteFiles = "showSaveFilePicker" in window;

export class ProjectFile {
  #handle = null;

  /** onChange hears the name of the file saved to, or null when there is none yet. */
  constructor(onChange) {
    this.onChange = onChange;
  }

  /** A new picture is a new project: the next save asks where. */
  forget() {
    this.#use(null);
  }

  /** Writes over the project's file, or asks where when it has none. Resolves to the name
   * saved as, or null when the person cancelled. */
  async save(blob, suggestedName) {
    if (!this.#handle) return this.saveAs(blob, suggestedName);
    await write(this.#handle, blob);
    return this.#handle.name;
  }

  async saveAs(blob, suggestedName) {
    if (!canWriteFiles) return downloadAs(blob, suggestedName);
    const handle = await unlessCancelled(() => window.showSaveFilePicker({ suggestedName, types: TYPES }));
    if (!handle) return null;
    await write(handle, blob);
    this.#use(handle);
    return handle.name;
  }

  /** Lets the person choose a project and gives it to read, which says whether it was one. Its
   * file becomes the one to save to. Without file access the input chooses it instead. */
  async open(input, read) {
    if (!canWriteFiles) return input.click();
    const [handle] = (await unlessCancelled(() => window.showOpenFilePicker({ types: TYPES }))) ?? [];
    if (handle && (await read(await handle.getFile()))) this.#use(handle);
  }

  #use(handle) {
    this.#handle = handle;
    this.onChange(handle?.name ?? null);
  }
}

async function write(handle, blob) {
  const writable = await handle.createWritable();
  await writable.write(blob);
  await writable.close();
}

/** What the picker chose, or null when it was closed without choosing. */
async function unlessCancelled(pick) {
  try {
    return await pick();
  } catch (error) {
    if (error.name === "AbortError") return null;
    throw error;
  }
}

function downloadAs(blob, suggestedName) {
  const name = window.prompt("Save the project as", suggestedName)?.trim();
  if (!name) return null;
  const fileName = name.endsWith(".json") ? name : `${name}.keychain.json`;
  saveFile(blob, fileName);
  return fileName;
}
