(() => {
  const esc = value => {
    const element = document.createElement("div");
    element.textContent = value ?? "";
    return element.innerHTML;
  };
  const render = data => {
    const target = document.getElementById("sceneGallery");
    if (!target) return;
    const scenes = data.scene_gallery || [];
    target.innerHTML = scenes.map(scene => `
      <a class="scene-card" href="${esc(scene.url)}" target="_blank" rel="noopener">
        <img loading="lazy" src="${esc(scene.url)}" alt="ฉาก ${esc(scene.number)} ${esc(scene.beat)}">
        <div><b>ฉาก ${esc(scene.number)} · ${esc(scene.beat)}</b><span>${esc(scene.visual)}</span></div>
      </a>`).join("") || '<div class="empty">ตอนนี้ยังไม่มีภาพฉากที่สร้างเสร็จ</div>';
  };
  const wireAccountingRoom = () => {
    const nav = document.querySelector(".jumpbar");
    if (nav && !nav.querySelector('[href="/finance"]')) {
      nav.insertAdjacentHTML("beforeend", '<a class="jump" href="/finance">ห้องบัญชี</a>');
    }
  };
  document.addEventListener("click", event => {
    if (!event.target.closest('[data-room="finance"]')) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    window.location.assign("/finance");
  }, true);
  fetch("/api/studio", {cache: "no-store"}).then(response => response.json()).then(render)
    .catch(() => { const target = document.getElementById("sceneGallery"); if (target) target.textContent = "เปิดคลังภาพไม่สำเร็จ"; });
  wireAccountingRoom();
})();
