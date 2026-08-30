/* Lazy external WebGL viewers for the 68 real-crystal examples.
 *
 * The HTML starts with local project-generated preview images and no iframes.
 * A user click creates one public Sketchfab or 3Dmol.js viewer. Opening another
 * crystal removes the previous iframe first, so the atlas never accumulates
 * dozens of WebGL contexts while the user moves between cards and tabs.
 */

"use strict";

const roots = [...document.querySelectorAll("[data-crystal-viewer]")];
let activeRoot = null;

function parts(root) {
  return {
    stage: root.querySelector("[data-crystal-stage]"),
    prompt: root.querySelector("[data-crystal-prompt]"),
    frameHost: root.querySelector("[data-crystal-frame]"),
    loadButton: root.querySelector("[data-crystal-load]"),
    closeButton: root.querySelector("[data-crystal-close]"),
    status: root.querySelector("[data-crystal-status]"),
  };
}

function setStatus(root, message) {
  const status = parts(root).status;
  if (status) status.textContent = message;
}

function unload(root, { restoreFocus = false } = {}) {
  if (!root) return;
  const {
    stage, prompt, frameHost, loadButton, closeButton,
  } = parts(root);
  frameHost.replaceChildren();
  stage.dataset.state = "idle";
  stage.removeAttribute("aria-busy");
  prompt.hidden = false;
  loadButton.hidden = false;
  closeButton.hidden = true;
  setStatus(root, "Interactive 3D viewer not loaded.");
  if (activeRoot === root) activeRoot = null;
  if (restoreFocus) loadButton.focus();
}

function load(root) {
  if (activeRoot === root) return;
  if (activeRoot) unload(activeRoot);

  const {
    stage, prompt, frameHost, loadButton, closeButton,
  } = parts(root);
  const iframe = document.createElement("iframe");
  iframe.className = "crystal-viewer-iframe";
  iframe.src = root.dataset.crystalEmbed;
  iframe.title = `Interactive 3D crystal viewer for ${root.dataset.crystalName}`;
  iframe.loading = "eager";
  iframe.referrerPolicy = "no-referrer";
  iframe.allow = "autoplay; fullscreen; xr-spatial-tracking";
  iframe.setAttribute("allowfullscreen", "");
  iframe.setAttribute(
    "sandbox",
    "allow-forms allow-popups allow-presentation allow-same-origin allow-scripts",
  );
  iframe.addEventListener("load", () => {
    if (activeRoot !== root || !iframe.isConnected) return;
    stage.dataset.state = "ready";
    stage.removeAttribute("aria-busy");
    setStatus(root, `External 3D viewer document loaded for ${root.dataset.crystalName}.`);
  });
  iframe.addEventListener("error", () => {
    if (activeRoot !== root) return;
    unload(root);
    setStatus(root, "The external 3D viewer could not be loaded; use the source link below.");
  });

  activeRoot = root;
  stage.dataset.state = "loading";
  stage.setAttribute("aria-busy", "true");
  prompt.hidden = true;
  loadButton.hidden = true;
  closeButton.hidden = false;
  setStatus(root, `Loading the interactive 3D viewer for ${root.dataset.crystalName}.`);
  frameHost.replaceChildren(iframe);
  closeButton.focus();
}

for (const root of roots) {
  const { loadButton, closeButton } = parts(root);
  loadButton.addEventListener("click", () => load(root));
  closeButton.addEventListener("click", () => unload(root, { restoreFocus: true }));
}

document.addEventListener("clockwork:tab-change", (event) => {
  if (activeRoot?.dataset.groupId === event.detail?.inactiveId) unload(activeRoot);
});

window.addEventListener("pagehide", () => {
  if (activeRoot) unload(activeRoot);
});
