"use strict";

const OS_NAMES = { windows: "Windows", macos: "macOS", linux: "Linux" };

function detectPlatform() {
  const ua = navigator.userAgent;
  const platform = navigator.userAgentData?.platform || navigator.platform || "";
  if (/Android|iPhone|iPad|iPod|CrOS/i.test(ua)) return null;
  if (/Win/i.test(platform) || /Windows/.test(ua)) return { os: "windows" };
  if (/Mac/i.test(platform) || /Mac OS X/.test(ua)) {
    // iPadOS Safari reports itself as a Mac; a Mac has no touch screen.
    return navigator.maxTouchPoints > 1 ? null : { os: "macos", arch: "aarch64" };
  }
  if (/Linux/i.test(platform) || /Linux/.test(ua)) {
    return { os: "linux", arch: /aarch64|arm64/i.test(platform + ua) ? "aarch64" : "x86_64" };
  }
  return null;
}

// Only Chromium browsers can tell; Safari and Firefox on Apple silicon report an Intel Mac.
async function refineArch(detected) {
  if (!detected.arch || !navigator.userAgentData?.getHighEntropyValues) return;
  try {
    const { architecture } = await navigator.userAgentData.getHighEntropyValues(["architecture"]);
    if (architecture === "arm") detected.arch = "aarch64";
    else if (architecture === "x86") detected.arch = "x86_64";
  } catch {
    // Keep the guess.
  }
}

function preferArch(panel, arch) {
  for (const link of panel.querySelectorAll(".files [data-arch]")) {
    link.classList.toggle("primary", link.dataset.arch === arch);
  }
  const primary = panel.querySelector(".files .primary");
  primary?.parentElement.prepend(primary);
}

function setUpTabs(detected) {
  const section = document.getElementById("download");
  const tablist = section.querySelector(".os-tabs");
  const tabs = [...tablist.querySelectorAll('[role="tab"]')];
  const panels = [...section.querySelectorAll(".os-panel")];

  function select(os, focus) {
    for (const tab of tabs) {
      const selected = tab.dataset.os === os;
      tab.setAttribute("aria-selected", selected);
      tab.tabIndex = selected ? 0 : -1;
      if (selected && focus) tab.focus();
    }
    for (const panel of panels) panel.classList.toggle("selected", panel.dataset.os === os);
  }

  tablist.addEventListener("click", (event) => {
    const tab = event.target.closest('[role="tab"]');
    if (tab) select(tab.dataset.os);
  });
  tablist.addEventListener("keydown", (event) => {
    const step = { ArrowLeft: -1, ArrowRight: 1 }[event.key];
    if (!step) return;
    const current = tabs.findIndex((tab) => tab.tabIndex === 0);
    select(tabs[(current + step + tabs.length) % tabs.length].dataset.os, true);
  });

  if (detected?.arch) preferArch(panels.find((panel) => panel.dataset.os === detected.os), detected.arch);
  select(detected?.os ?? "windows");
}

function setUpCopyButtons() {
  if (!navigator.clipboard) return;
  for (const button of document.querySelectorAll(".copy")) {
    button.hidden = false;
    button.addEventListener("click", async () => {
      const scope = button.classList.contains("copy-all") ? button.closest(".commands") : button.closest(".command");
      const text = [...scope.querySelectorAll("code")].map((code) => code.textContent).join("\n");
      try {
        await navigator.clipboard.writeText(text);
        button.classList.add("copied");
        setTimeout(() => button.classList.remove("copied"), 2000);
      } catch {
        button.title = "Copying failed";
      }
    });
  }
  for (const code of document.querySelectorAll(".command code")) {
    code.title = "Copy to clipboard";
    code.addEventListener("click", () => {
      // Leave a selection made by dragging alone.
      if (!getSelection().isCollapsed) return;
      code.parentElement.querySelector(".copy").click();
    });
  }
}

function createViewer() {
  const viewer = document.querySelector(".viewer");
  const image = viewer.querySelector("img");
  const caption = viewer.querySelector("figcaption");
  let shots = [];
  let current = 0;
  let onClose = null;

  function show(index) {
    current = (index + shots.length) % shots.length;
    const thumbnail = shots[current].querySelector("img");
    image.removeAttribute("src");
    image.src = shots[current].href;
    image.width = thumbnail.width;
    image.height = thumbnail.height;
    image.alt = thumbnail.alt;
    caption.textContent = thumbnail.alt;
  }

  viewer.querySelector(".viewer-prev").addEventListener("click", () => show(current - 1));
  viewer.querySelector(".viewer-next").addEventListener("click", () => show(current + 1));
  viewer.querySelector(".viewer-close").addEventListener("click", () => viewer.close());
  viewer.addEventListener("click", (event) => {
    if (event.target === viewer || event.target.tagName === "FIGURE") viewer.close();
  });
  viewer.addEventListener("keydown", (event) => {
    if (shots.length < 2) return;
    if (event.key === "ArrowLeft") show(current - 1);
    else if (event.key === "ArrowRight") show(current + 1);
  });
  viewer.addEventListener("close", () => onClose?.(current));

  return function open(group, index, closed) {
    shots = group;
    onClose = closed;
    viewer.classList.toggle("single", shots.length < 2);
    show(index);
    viewer.showModal();
  };
}

function setUpCarousel(carousel, openViewer) {
  const track = carousel.querySelector(".carousel-track");
  const slides = [...track.querySelectorAll(".slide")];
  const shots = slides.map((slide) => slide.querySelector("a.shot"));
  const dots = carousel.querySelector(".carousel-dots");
  let current = 0;

  function go(index) {
    const target = slides[(index + slides.length) % slides.length];
    track.scrollTo({ left: target.offsetLeft - slides[0].offsetLeft });
  }

  const dotButtons = slides.map((slide, index) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.setAttribute("aria-label", `Screenshot ${index + 1}: ${slide.querySelector("figcaption").textContent}`);
    dot.addEventListener("click", () => go(index));
    dots.append(dot);
    return dot;
  });

  function update() {
    const step = slides.length > 1 ? slides[1].offsetLeft - slides[0].offsetLeft : 1;
    current = Math.round(track.scrollLeft / step);
    dotButtons.forEach((dot, index) => dot.setAttribute("aria-current", index === current));
  }

  track.addEventListener("scroll", () => requestAnimationFrame(update), { passive: true });
  carousel.querySelector(".carousel-prev").addEventListener("click", () => go(current - 1));
  carousel.querySelector(".carousel-next").addEventListener("click", () => go(current + 1));
  carousel.querySelector(".carousel-full").addEventListener("click", () => openViewer(shots, current, go));
  shots.forEach((shot, index) => {
    shot.addEventListener("click", (event) => {
      event.preventDefault();
      openViewer(shots, index, go);
    });
  });

  update();
}

function setUpSingleShots(openViewer) {
  for (const group of document.querySelectorAll("[data-gallery]:not(.carousel)")) {
    const shots = [...group.querySelectorAll("a.shot")];
    shots.forEach((shot, index) => {
      shot.addEventListener("click", (event) => {
        event.preventDefault();
        openViewer(shots, index);
      });
    });
  }
}

async function main() {
  const openViewer = createViewer();
  for (const carousel of document.querySelectorAll(".carousel")) setUpCarousel(carousel, openViewer);
  setUpSingleShots(openViewer);
  setUpCopyButtons();

  const detected = detectPlatform();
  if (detected) await refineArch(detected);
  setUpTabs(detected);
  if (detected) {
    document.getElementById("hero-download").textContent = `Download for ${OS_NAMES[detected.os]}`;
  }
}

main();
