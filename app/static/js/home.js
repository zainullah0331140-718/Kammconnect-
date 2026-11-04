(function () {
  "use strict";

  function iconClass(value) {
    const icon = String(value || "grid").replace(/[^a-z0-9-]/gi, "");
    return `bi bi-${icon || "grid"}`;
  }

  function categoryCard(category) {
    return `<div class="col-6 col-md-4 col-xl-3">
      <a class="category-card" href="/search?category=${encodeURIComponent(category.slug)}">
        <span class="category-icon"><i class="${iconClass(category.icon)}"></i></span>
        <h3 class="h6 mb-1">${KC.escapeHtml(category.name)}</h3>
        <p class="small text-muted mb-2">${KC.escapeHtml((category.description || "Explore local professionals.").slice(0, 72))}</p>
        <span class="small text-brand fw-semibold">${Number(category.provider_count) || 0} provider${Number(category.provider_count) === 1 ? "" : "s"} <i class="bi bi-arrow-right"></i></span>
      </a>
    </div>`;
  }

  function providerGrid(container, providers, emptyMessage) {
    if (!container) return;
    if (!providers.length) {
      container.innerHTML = `<div class="col-12">${KC.emptyState(
        "bi-people",
        "No providers to show yet",
        emptyMessage,
        '<a class="btn btn-brand" href="/register/provider">Become the first provider</a>'
      )}</div>`;
      return;
    }
    container.innerHTML = providers
      .map((provider) => `<div class="col-md-6 col-xl-3">${KC.providerCard(provider)}</div>`)
      .join("");
  }

  function adCard(ad) {
    return `<div class="col-md-6 col-xl-3">
      <a class="card h-100 border-0 overflow-hidden text-decoration-none hover-lift" href="${KC.escapeHtml(
        ad.destination_url
      )}" target="_blank" rel="noopener noreferrer sponsored">
        <img class="ad-image" src="${KC.escapeHtml(ad.image_path)}" alt="" loading="lazy">
        <div class="card-body">
          <span class="badge badge-neutral mb-2">Sponsored</span>
          <h3 class="h6">${KC.escapeHtml(ad.title)}</h3>
          <p class="small text-muted mb-1">${KC.escapeHtml((ad.description || "").slice(0, 100))}</p>
          <span class="small text-brand fw-semibold">${KC.escapeHtml(ad.provider_name)} <i class="bi bi-box-arrow-up-right"></i></span>
        </div>
      </a>
    </div>`;
  }

  async function loadCategories() {
    const container = document.getElementById("homeCategories");
    const select = document.getElementById("heroCategory");
    try {
      const categories = await KC.get("/categories");
      if (container) {
        container.innerHTML = categories.length
          ? categories.slice(0, 8).map(categoryCard).join("")
          : `<div class="col-12">${KC.emptyState("bi-grid", "No categories yet", "An administrator can add service categories from the admin panel.")}</div>`;
      }
      if (select) {
        select.innerHTML =
          '<option value="">All categories</option>' +
          categories
          .map((category) => `<option value="${KC.escapeHtml(category.slug)}">${KC.escapeHtml(category.name)}</option>`)
            .join("");
      }
    } catch (error) {
      if (container) container.innerHTML = `<div class="col-12 text-muted">Categories are temporarily unavailable.</div>`;
    }
  }

  async function loadLocations() {
    const select = document.getElementById("heroCity");
    if (!select) return;
    try {
      const locations = await KC.get("/providers/locations");
      select.innerHTML =
        '<option value="">All cities</option>' +
        locations
          .map((location) => `<option value="${KC.escapeHtml(location.city)}">${KC.escapeHtml(location.city)}</option>`)
          .join("");
    } catch (_error) {
      // The city filter still works as a free-text field via the search page.
    }
  }

  async function loadFeatured() {
    const container = document.getElementById("featuredProviders");
    try {
      const providers = await KC.get("/providers/featured?limit=4");
      providerGrid(container, providers, "Verified providers will appear here once they are approved.");
    } catch (error) {
      if (container) container.innerHTML = `<div class="col-12 text-muted">Providers are temporarily unavailable.</div>`;
    }
  }

  async function loadRecent() {
    const container = document.getElementById("recentProviders");
    try {
      const providers = await KC.get("/providers/recent?limit=4");
      providerGrid(container, providers, "New provider profiles will appear here as they join.");
    } catch (error) {
      if (container) container.innerHTML = `<div class="col-12 text-muted">Providers are temporarily unavailable.</div>`;
    }
  }

  async function loadAds() {
    const section = document.getElementById("adSection");
    const container = document.getElementById("homeAds");
    try {
      const ads = await KC.get("/advertisements/public?limit=4");
      if (!ads.length || !section || !container) return;
      container.innerHTML = ads.map(adCard).join("");
      section.hidden = false;
    } catch (_error) {
      // Ads are optional; do not disrupt the home page.
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadCategories();
    loadLocations();
    loadFeatured();
    loadRecent();
    loadAds();
  });
})();
