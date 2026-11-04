(function () {
  "use strict";

  function iconClass(value) {
    const icon = String(value || "grid").replace(/[^a-z0-9-]/gi, "");
    return `bi bi-${icon || "grid"}`;
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const grid = document.getElementById("categoryGrid");
    if (!grid) return;
    try {
      const categories = await KC.get("/categories");
      if (!categories.length) {
        grid.innerHTML = `<div class="col-12">${KC.emptyState(
          "bi-grid",
          "No categories yet",
          "An administrator can add categories from the admin panel."
        )}</div>`;
        return;
      }
      grid.innerHTML = categories
        .map(
          (category) => `<div class="col-sm-6 col-lg-4">
            <a class="category-card" href="/search?category=${encodeURIComponent(category.slug)}">
              <div class="d-flex justify-content-between align-items-start">
                <span class="category-icon"><i class="${iconClass(category.icon)}"></i></span>
                <span class="chip">${Number(category.provider_count) || 0} provider${Number(category.provider_count) === 1 ? "" : "s"}</span>
              </div>
              <h2 class="h5 mt-1">${KC.escapeHtml(category.name)}</h2>
              <p class="text-muted small mb-3">${KC.escapeHtml(category.description || "Browse local providers in this category.")}</p>
              <span class="text-brand fw-semibold small">Browse providers <i class="bi bi-arrow-right"></i></span>
            </a>
          </div>`
        )
        .join("");
    } catch (error) {
      grid.innerHTML = `<div class="col-12 alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
    }
  });
})();
