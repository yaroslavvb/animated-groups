/* Progressive tab controller for the space-group correspondence atlas. */

"use strict";

function initializeTabs() {
  const initialHash = location.hash;
  if (initialHash) history.replaceState(null, "", `${location.pathname}${location.search}`);
  const controllers = new Map();
  const defaults = [];

  for (const host of document.querySelectorAll("[data-space-tabs]")) {
    const tablist = host.querySelector("[data-space-tablist]");
    const tabs = [...host.querySelectorAll("[data-space-tab]")];
    const items = tabs.map((tab) => {
      const panel = document.getElementById(tab.dataset.panelId || "");
      return panel ? { tab, panel } : null;
    }).filter(Boolean);
    if (!tablist || items.length !== tabs.length || items.length === 0) continue;

    tablist.setAttribute("role", "tablist");
    for (const { tab, panel } of items) {
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", panel.id);
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", tab.id);
    }

    let activeId = "";
    const activate = (groupId, options = {}) => {
      const selected = items.find(({ panel }) => panel.id === groupId);
      if (!selected) return false;
      activeId = groupId;
      for (const { tab, panel } of items) {
        const active = panel.id === groupId;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
        panel.hidden = !active;
      }
      if (options.focus) selected.tab.focus();
      if (options.history) {
        history[options.history === "push" ? "pushState" : "replaceState"](null, "", `#${groupId}`);
      }
      if (options.scroll) requestAnimationFrame(() => selected.panel.scrollIntoView({ block: "start" }));
      return true;
    };

    items.forEach(({ tab, panel }, index) => {
      tab.addEventListener("click", (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        activate(panel.id, { history: location.hash === `#${panel.id}` ? null : "push" });
      });
      tab.addEventListener("keydown", (event) => {
        let next = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % items.length;
        else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index - 1 + items.length) % items.length;
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = items.length - 1;
        if (next === null) return;
        event.preventDefault();
        activate(items[next].panel.id, { focus: true, history: "replace" });
      });
      controllers.set(panel.id, { activate });
    });
    const defaultId = items[0].panel.id;
    defaults.push({ activate, groupId: defaultId });
    activate(defaultId);
  }

  const openFromHash = (scroll = true) => {
    const rawId = location.hash.replace(/^#/, "");
    if (!rawId) {
      for (const entry of defaults) entry.activate(entry.groupId);
      return;
    }
    let id;
    try {
      id = decodeURIComponent(rawId);
    } catch {
      return;
    }
    const controller = controllers.get(id);
    if (controller) controller.activate(id, { scroll });
    else if (scroll) document.getElementById(id)?.scrollIntoView({ block: "start" });
  };

  if (initialHash) history.replaceState(null, "", initialHash);
  openFromHash(true);
  window.addEventListener("load", () => openFromHash(true), { once: true });
  window.addEventListener("hashchange", () => openFromHash(true));
  window.addEventListener("popstate", () => openFromHash(true));
}

initializeTabs();
