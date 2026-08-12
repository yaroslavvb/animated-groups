"use strict";

const parameters = new URLSearchParams(window.location.search);
const title = document.querySelector("[data-excerpt-title]");
const context = document.querySelector("[data-excerpt-context]");
const media = document.querySelector("[data-excerpt-media]");
const image = document.querySelector("[data-excerpt-image]");
const status = document.querySelector("[data-excerpt-status]");
const source = document.querySelector("[data-excerpt-source]");
const zoom = document.querySelector("[data-zoom-toggle]");

if (window.opener) {
  window.opener.postMessage(
    { type: "clockwork:book-excerpt-ready" },
    window.location.origin,
  );
}

function validImagePath(value) {
  return /^output\/book-excerpts\/[a-z0-9-]+\.webp$/i.test(value || "");
}

function validSource(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "books.google.com";
  } catch (_error) {
    return false;
  }
}

const imagePath = parameters.get("image") || "";
const excerptTitle = parameters.get("title") || "Annotated book excerpt";
const excerptContext = parameters.get("context") || "Highlighted evidence from the cited page.";
const excerptAlt = parameters.get("alt") || "Annotated excerpt from The Symmetries of Things.";
const sourceUrl = parameters.get("source") || "";

title.textContent = excerptTitle;
context.textContent = excerptContext;
document.title = `${excerptTitle} · annotated excerpt`;
image.alt = excerptAlt;

if (validSource(sourceUrl)) source.href = sourceUrl;
else source.hidden = true;

if (validImagePath(imagePath)) {
  image.src = `${imagePath}?v=whole-tables`;
} else {
  media.dataset.state = "error";
  status.textContent = "This excerpt link is incomplete. Return to the correspondence page and open it again.";
}

image.addEventListener("load", () => {
  media.dataset.state = "ready";
  status.hidden = true;
});

image.addEventListener("error", () => {
  media.dataset.state = "error";
  status.hidden = false;
  status.textContent = "The local excerpt could not be loaded. Use the Google Books link above.";
});

zoom.addEventListener("click", () => {
  const actual = media.dataset.zoom !== "actual";
  media.dataset.zoom = actual ? "actual" : "fit";
  zoom.setAttribute("aria-pressed", String(actual));
  zoom.textContent = actual ? "Fit excerpt" : "Actual size";
  media.scrollTop = 0;
  media.scrollLeft = 0;
});
