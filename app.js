"use strict";

const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#navigation");
function closeMenu() {
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.setAttribute("aria-label", "展开导航");
  navigation.classList.remove("is-open");
}
menuButton.addEventListener("click", () => {
  const open = menuButton.getAttribute("aria-expanded") !== "true";
  menuButton.setAttribute("aria-expanded", String(open));
  menuButton.setAttribute("aria-label", open ? "收起导航" : "展开导航");
  navigation.classList.toggle("is-open", open);
});
navigation
  .querySelectorAll("a")
  .forEach((link) => link.addEventListener("click", closeMenu));
document.addEventListener("keydown", (event) => {
  if (
    event.key === "Escape" &&
    menuButton.getAttribute("aria-expanded") === "true"
  ) {
    closeMenu();
    menuButton.focus();
  }
});

const tabs = [...document.querySelectorAll("[data-stage]")];
function selectStage(tab, focus = false) {
  tabs.forEach((item) => {
    const selected = item === tab;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute("aria-controls")).hidden =
      !selected;
  });
  if (focus) tab.focus();
}
tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => selectStage(tab));
  tab.addEventListener("keydown", (event) => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft")
      next = (index - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next !== undefined) {
      event.preventDefault();
      selectStage(tabs[next], true);
    }
  });
});

const video = document.getElementById("defense-video");
const videoButton = document.getElementById("video-play");
videoButton.addEventListener("click", async () => {
  try {
    await video.play();
  } catch {
    videoButton.hidden = true;
    video.focus();
  }
});
video.addEventListener("play", () => {
  videoButton.hidden = true;
});
video.addEventListener("ended", () => {
  videoButton.hidden = false;
});
video.addEventListener("error", () => {
  videoButton.hidden = true;
  const wrap = video.parentElement;
  if (!wrap.querySelector(".video-error")) {
    const note = document.createElement("p");
    note.className = "video-error";
    note.style.cssText =
      "position:absolute;left:20px;bottom:20px;right:20px;padding:15px;background:#111419;color:#f2ce87;font-size:12px";
    const link = document.createElement("a");
    link.href = "assets/defense-demo.mp4";
    link.textContent = "视频暂时无法播放，点击下载演示。";
    note.appendChild(link);
    wrap.appendChild(note);
  }
});

document.querySelectorAll("[data-copy]").forEach((button) => {
  let timer;
  button.addEventListener("click", async () => {
    const source = document.getElementById(button.dataset.copy);
    const text = source.textContent;
    const status = document.getElementById("copy-status");
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = "已复制 ✓";
      status.textContent = "快速开始命令已复制到剪贴板。";
    } catch {
      const range = document.createRange();
      range.selectNodeContents(source);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      button.textContent = "请手动复制";
      status.textContent = "命令已选中，请手动复制。";
    }
    clearTimeout(timer);
    timer = setTimeout(() => {
      button.textContent = "复制命令";
    }, 2500);
  });
});
