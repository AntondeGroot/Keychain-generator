// The Save, Save as and Open project buttons: they turn the page into a project file and back,
// and say which file Save writes over.

import { fromFileInput, projectBlob, projectName, readProject } from "./project.js";
import { ProjectFile } from "./projectfile.js";
import { setStatus } from "./server.js";

const element = (id) => document.getElementById(id);

export class ProjectMenu {
  /** request gives the page as it would be saved; restore puts a saved project back on it;
   * rename hears the name of the file saved to, which the keychain's files take. */
  constructor(request, restore, rename) {
    this.request = request;
    this.restore = restore;
    this.rename = rename;
    this.file = new ProjectFile(showFile);
    element("save-project").addEventListener("click", () => this.#save("save"));
    element("save-project-as").addEventListener("click", () => this.#save("saveAs"));
    element("open-project").addEventListener("click", () => this.file.open(element("open-project-file"), (file) => this.#open(file)));
    element("open-project-file").addEventListener("change", (event) => fromFileInput(event.target, (file) => this.#openFromInput(file)));
  }

  /** A new picture is a new project: it can be saved, and the first save asks where. */
  startNew() {
    this.file.forget();
    enableSaving();
  }

  /** Save writes over the project's file, Save as asks for another name or folder. */
  async #save(how) {
    const request = this.request();
    try {
      const saved = await this.file[how](projectBlob(request), `${request.name}.keychain.json`);
      if (!saved) return;
      this.rename(projectName(saved));
      setStatus(`Saved as ${saved}.`);
    } catch (error) {
      setStatus(`Could not save the project: ${error.message}`, "error");
    }
  }

  /** Puts the project in the file on the page; says whether the file was a project. */
  async #open(file) {
    try {
      await this.restore(await readProject(file));
      enableSaving();
      return true;
    } catch (error) {
      setStatus(error.message, "error");
      return false;
    }
  }

  /** A project chosen without file access, so its file cannot be written over. */
  async #openFromInput(file) {
    if (await this.#open(file)) this.file.forget();
  }
}

function showFile(name) {
  element("project-file").textContent = name ? `Save writes over ${name}.` : "";
}

function enableSaving() {
  element("save-project").disabled = false;
  element("save-project-as").disabled = false;
}
