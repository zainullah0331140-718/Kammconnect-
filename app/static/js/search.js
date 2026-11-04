(function () {
  "use strict";

  const form = document.getElementById("searchForm");
  const results = document.getElementById("searchResults");
  const count = document.getElementById("resultCount");
  const pagination = document.getElementById("searchPagination");
  const citySelect = document.getElementById("filterCity");
  const areaSelect = document.getElementById("filterArea");
  const topSort = document.getElementById("topSort");
  let locations = [];
  let currentPage = 1;

  function params() {
    return new URLSearchParams(window.location.search);
  }

  function readFilters() {
    const data = new FormData(form);
    return {
      q: String(data.get("q") || "").trim(),
      category: String(data.get("category") || ""),
      city: String(data.get("city") || ""),
      area: String(data.get("area") || ""),
      min_rating: String(data.get("min_rating") || "0"),
      verified: data.get("verified") === "true",
      sort: topSort ? topSort.value : String(data.get("sort") || "rating"),
    };
  }

  function applyParamsToForm() {
    const query = params();
    ["q", "category", "city", "area", "min_rating", "sort"].forEach((name) => {
      const field = form.elements[name];
      if (field && query.get(name)) field.value = query.get(name);
    });
    const verified = form.elements.verified;
    if (verified) verified.checked = query.get("verified") === "true";
    if (topSort) topSort.value = query.get("sort") || "rating";
    currentPage = Math.max(1, Number(query.get("page")) || 1);
  }

  function updateUrl(filters) {
    const query = new URLSearchParams();
    if (filters.q) query.set("q", filters.q);
    if (filters.category) query.set("category", filters.category);
    if (filters.city) query.set("city", filters.city);
    if (filters.area) query.set("area", filters.area);
    if (filters.min_rating && filters.min_rating !== "0") query.set("min_rating", filters.min_rating);
    if (filters.verified) query.set("verified", "true");
    if (filters.sort && filters.sort !== "rating") query.set("sort", filters.sort);
    if (currentPage > 1) query.set("page", String(currentPage));
    const next = query.toString();
    window.history.replaceState({}, "", next ? `/search?${next}` : "/search");
  }

  function fillAreas() {
    if (!citySelect || !areaSelect) return;
    const selected = locations.find((item) => item.city === citySelect.value);
    if (!selected || !selected.areas.length) {
      areaSelect.innerHTML = '<option value="">All areas</option>';
      areaSelect.disabled = true;
      return;
    }
    areaSelect.innerHTML =
      '<option value="">All areas</option>' +
      selected.areas
        .map((area) => `<option value="${KC.escapeHtml(area)}">${KC.escapeHtml(area)}</option>`)
        .join("");
    areaSelect.disabled = false;
  }

  async function loadOptions() {
    const [categories, locationData] = await Promise.all([
      KC.get("/categories"),
      KC.get("/providers/locations").catch(() => []),
    ]);
    const categorySelect = document.getElementById("filterCategory");
    if (categorySelect) {
      categorySelect.innerHTML =
        '<option value="">All categories</option>' +
        categories
          .map((item) => `<option value="${KC.escapeHtml(item.slug)}">${KC.escapeHtml(item.name)}</option>`)
          .join("");
    }
    locations = locationData;
    if (citySelect) {
      citySelect.innerHTML =
        '<option value="">All cities</option>' +
        locations
          .map((item) => `<option value="${KC.escapeHtml(item.city)}">${KC.escapeHtml(item.city)}</option>`)
          .join("");
    }
    applyParamsToForm();
    fillAreas();
    const areaParam = params().get("area");
    if (areaParam && areaSelect) areaSelect.value = areaParam;
  }

  async function loadProviders() {
    if (!results) return;
    const filters = readFilters();
    updateUrl(filters);
    const query = new URLSearchParams({
      page: String(currentPage),
      page_size: "9",
      sort: filters.sort,
      min_rating: filters.min_rating || "0",
    });
    if (filters.q) query.set("q", filters.q);
    if (filters.category) query.set("category", filters.category);
    if (filters.city) query.set("city", filters.city);
    if (filters.area) query.set("area", filters.area);
    if (filters.verified) query.set("verified", "true");
    results.innerHTML = '<div class="col-12"><div class="text-muted">Loading providers…</div></div>';
    if (count) count.textContent = "Loading providers…";
    try {
      const data = await KC.get(`/providers?${query.toString()}`);
      if (count) {
        count.textContent = `${data.total} provider${data.total === 1 ? "" : "s"} found`;
      }
      if (!data.items.length) {
        results.innerHTML = `<div class="col-12">${KC.emptyState(
          "bi-search",
          "No providers match those filters",
          "Try a different category, city, or rating — or clear the filters to browse everyone.",
          '<button class="btn btn-brand" type="button" id="emptyClear">Clear filters</button>'
        )}</div>`;
        const emptyClear = document.getElementById("emptyClear");
        if (emptyClear) emptyClear.addEventListener("click", clearFilters);
      } else {
        results.innerHTML = data.items
          .map((provider) => `<div class="col-md-6">${KC.providerCard(provider)}</div>`)
          .join("");
      }
      KC.pagination(pagination, data, (page) => {
        currentPage = page;
        loadProviders();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    } catch (error) {
      if (count) count.textContent = "";
      results.innerHTML = `<div class="col-12 alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
    }
  }

  function clearFilters() {
    form.reset();
    currentPage = 1;
    if (topSort) topSort.value = "rating";
    fillAreas();
    loadProviders();
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!form) return;
    try {
      await loadOptions();
    } catch (error) {
      KC.showError(results, error);
    }
    loadProviders();

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      currentPage = 1;
      loadProviders();
    });
    if (topSort) {
      topSort.addEventListener("change", () => {
        const sortField = form.elements.sort;
        if (sortField) sortField.value = topSort.value;
        currentPage = 1;
        loadProviders();
      });
    }
    if (citySelect) {
      citySelect.addEventListener("change", () => {
        fillAreas();
        currentPage = 1;
        loadProviders();
      });
    }
    if (areaSelect) {
      areaSelect.addEventListener("change", () => {
        currentPage = 1;
        loadProviders();
      });
    }
    document.getElementById("clearFilters").addEventListener("click", clearFilters);
  });
})();
