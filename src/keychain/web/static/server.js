// Talking to the server: a spinner over the preview while it works, then its answer or its
// error in the status line.

const element = (id) => document.getElementById(id);
let requestsInFlight = 0;
let onBusyChange = () => {};

/** Tells the page when the server starts or stops working, such as to switch buttons. */
export function whenBusyChanges(callback) {
  onBusyChange = callback;
}

export function isBusy() {
  return requestsInFlight > 0;
}

/** POSTs JSON with the spinner showing; on an error it shows the server's message and returns null. */
export async function call(path, body, waitingText) {
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

export function setStatus(text, kind = "") {
  const status = element("status");
  status.textContent = text;
  status.className = kind;
}

/** The spinner stays until every request has answered, also ones a newer change made stale. */
function showWorking(text, change) {
  requestsInFlight += change;
  element("working").hidden = !isBusy();
  element("preview").setAttribute("aria-busy", String(isBusy()));
  if (change > 0) {
    element("working-text").textContent = text;
    setStatus(text, "busy");
  }
  onBusyChange();
}
