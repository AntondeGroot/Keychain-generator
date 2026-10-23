// The guide above the picture: what to do next with the drawing tools, hidden otherwise. While
// shown it grows to fit but never shrinks, so the picture stays put under the pointer.

export function showGuide(guide, text) {
  const before = text ? guide.offsetHeight : 0;
  guide.style.minHeight = "";
  guide.textContent = text;
  guide.hidden = !text;
  if (text) guide.style.minHeight = `${Math.max(before, guide.offsetHeight)}px`;
}
