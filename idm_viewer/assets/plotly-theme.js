// ====================================================================
//  Fully reliable Plotly auto-theme hook for Dash
//  Works on initial render, every update, and theme toggle
// ====================================================================

function applyPlotlyTheme() {
  const isDark = document.documentElement.classList.contains("dark");
  const template = isDark ? "plotly_dark" : "plotly_white";
  window.PLOTLY_TEMPLATE = template;

    console.log('Update plotly theme')
    
    // Update all graphs currently in DOM
    var n = 0;
  document.querySelectorAll(".js-plotly-plot").forEach((g) => {
    const data = g.data;
      const layout = g.layout || {};
      console.log(layout)
    layout.template = template;
      Plotly.react(g, data, layout);
      n += 1;
      console.log(layout)
  });
    console.log('Updated ' + n + ' plots')
}

// ---------------------------------------------------------------
// 1) RUN THEME ON ANY PLOTLY RENDER EVENT
// ---------------------------------------------------------------
document.addEventListener("plotly_afterplot", () => {
  setTimeout(applyPlotlyTheme, 0);
});

// ---------------------------------------------------------------
// 2) RUN WHEN THE THEME CHANGES (.dark class toggled)
// ---------------------------------------------------------------
const observer = new MutationObserver(() => {
  setTimeout(applyPlotlyTheme, 0);
});
observer.observe(document.documentElement, {
  attributes: true,
  attributeFilter: ["class"],
});

// ---------------------------------------------------------------
// 3) RUN AFTER DOM CONTENT LOAD (fallback)
// ---------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  // Delay to allow Dash to finish initial graph rendering
  setTimeout(applyPlotlyTheme, 150);
});
