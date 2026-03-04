(function(){
  function setTheme(mode) {
    document.documentElement.classList.toggle("dark", mode === "dark");
      try { localStorage.setItem("theme", mode); } catch(e) {
          console.log(e)
      }
  }
  function getMode() {
    return document.documentElement.classList.contains("dark") ? "dark" : "light";
  }
  function toggle() { setTheme(getMode() === "dark" ? "light" : "dark"); }

  function placeButton() {
    if (document.getElementById("theme-toggle")) return;
    const btn = document.createElement("button");
    btn.id = "theme-toggle";
    btn.innerHTML = `
      <span class="icon-light">🌙</span>
      <span class="icon-dark">☀️</span>
    `;
    btn.onclick = toggle;
    document.body.appendChild(btn);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", placeButton);
  } else {
    placeButton();
  }
})();
