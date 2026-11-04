(function () {
  "use strict";

  const grid = document.getElementById("favoritesGrid");

  function card(provider) {
    const categories = [...new Set((provider.services || []).map((service) => service.category_name).filter(Boolean))];
    return `<div class="col-md-6 col-xl-4" data-favorite-card="${Number(provider.id)}">
      <article class="provider-card card h-100 border-0">
        <div class="card-body">
          <div class="d-flex gap-3 align-items-start">
            <img class="provider-avatar" src="${KC.avatarUrl(provider)}" alt="" loading="lazy">
            <div class="flex-grow-1 min-w-0">
              <div class="d-flex justify-content-between gap-2 align-items-start">
                <h2 class="h6 mb-1"><a class="text-decoration-none text-dark" href="/providers/${Number(provider.id)}">${KC.escapeHtml(provider.business_name)}</a></h2>
                ${KC.verificationBadge(provider.verification_status)}
              </div>
              <div class="small text-muted mb-1">${KC.escapeHtml(provider.provider_name || "")}</div>
              <div class="small mb-2"><i class="bi bi-geo-alt"></i> ${KC.escapeHtml([provider.area, provider.city].filter(Boolean).join(", ") || "Location not provided")}</div>
              ${KC.ratingBadge(provider.average_rating, provider.review_count)}
            </div>
          </div>
          <div class="d-flex flex-wrap gap-1 mt-3">
            ${(categories.length ? categories.slice(0, 3) : ["Service provider"]).map((name) => `<span class="chip">${KC.escapeHtml(name)}</span>`).join("")}
          </div>
        </div>
        <div class="card-footer bg-transparent border-0 pt-0 pb-3 px-3 d-flex gap-2">
          <a class="btn btn-sm btn-brand flex-grow-1" href="/providers/${Number(provider.id)}">View profile</a>
          <button class="btn btn-sm btn-outline-danger" type="button" data-remove="${Number(provider.id)}" aria-label="Remove ${KC.escapeHtml(provider.business_name)} from favorites"><i class="bi bi-heart-fill"></i></button>
        </div>
      </article>
    </div>`;
  }

  async function load() {
    try {
      const items = await KC.get("/favorites/me");
      if (!items.length) {
        grid.innerHTML = `<div class="col-12">${KC.emptyState(
          "bi-heart",
          "Your shortlist is empty",
          "Save providers from their profile page to compare them later.",
          '<a class="btn btn-brand" href="/search">Browse providers</a>'
        )}</div>`;
        return;
      }
      grid.innerHTML = items.map(card).join("");
      grid.querySelectorAll("[data-remove]").forEach((button) => {
        button.addEventListener("click", () => remove(Number(button.dataset.remove)));
      });
    } catch (error) {
      grid.innerHTML = `<div class="col-12 alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
    }
  }

  async function remove(id) {
    const confirmed = await KC.confirm("Remove this provider from your saved list?", "Remove favorite");
    if (!confirmed) return;
    try {
      await KC.del(`/favorites/${id}`);
      KC.toast("Removed from favorites");
      const card = document.querySelector(`[data-favorite-card="${id}"]`);
      if (card) card.remove();
      const remaining = grid.querySelectorAll("[data-favorite-card]").length;
      if (!remaining) load();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const me = await KC.requireAuth(["customer"]);
    if (!me) return;
    await load();
  });
})();
