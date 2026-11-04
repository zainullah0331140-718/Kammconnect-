(function () {
  "use strict";

  const container = document.getElementById("adsContainer");
  const form = document.getElementById("adForm");
  const modalEl = document.getElementById("adModal");

  function badge(ad) {
    if (ad.is_live) return '<span class="badge badge-verified">Live</span>';
    const map = {
      pending: "badge-pending",
      approved: "badge-verified",
      rejected: "badge-rejected",
      expired: "badge-neutral",
    };
    return `<span class="badge ${map[ad.status] || "badge-neutral"}">${KC.escapeHtml(ad.status)}</span>`;
  }

  function card(ad) {
    return `<article class="card-soft overflow-hidden mb-3">
      <div class="row g-0">
        <div class="col-md-3">
          <img class="ad-image h-100" src="${KC.escapeHtml(ad.image_path)}" alt="" loading="lazy">
        </div>
        <div class="col-md-9">
          <div class="p-4">
            <div class="d-flex flex-wrap justify-content-between gap-2">
              <div>
                <div class="d-flex align-items-center gap-2 flex-wrap">
                  <h2 class="h5 mb-0">${KC.escapeHtml(ad.title)}</h2>
                  ${badge(ad)}
                </div>
                <p class="small text-muted mt-1 mb-2">${KC.formatDate(ad.start_date)} – ${KC.formatDate(ad.end_date)}</p>
              </div>
              <div class="d-flex gap-2">
                ${ad.is_live ? `<a class="btn btn-sm btn-outline-brand" href="${KC.escapeHtml(ad.destination_url)}" target="_blank" rel="noopener noreferrer">Open <i class="bi bi-box-arrow-up-right"></i></a>` : ""}
                <button class="btn btn-sm btn-outline-danger" type="button" data-delete-ad="${Number(ad.id)}">Delete</button>
              </div>
            </div>
            <p class="small text-muted mb-2">${KC.escapeHtml(ad.description)}</p>
            <p class="small mb-0 text-truncate"><i class="bi bi-link-45deg"></i> ${KC.escapeHtml(ad.destination_url)}</p>
            ${ad.admin_note ? `<div class="alert alert-warning small mt-3 mb-0"><strong>Moderator note:</strong> ${KC.escapeHtml(ad.admin_note)}</div>` : ""}
          </div>
        </div>
      </div>
    </article>`;
  }

  async function load() {
    try {
      const ads = await KC.get("/advertisements/me");
      if (!ads.length) {
        container.innerHTML = KC.emptyState(
          "bi-megaphone",
          "No advertisements yet",
          "Create an advertisement to promote a service on the home page.",
          '<button class="btn btn-brand" type="button" data-bs-toggle="modal" data-bs-target="#adModal">Create advertisement</button>'
        );
        return;
      }
      container.innerHTML = ads.map(card).join("");
      container.querySelectorAll("[data-delete-ad]").forEach((button) => {
        button.addEventListener("click", () => remove(Number(button.dataset.deleteAd)));
      });
    } catch (error) {
      if (error.status === 404) {
        container.innerHTML = KC.emptyState("bi-person-vcard", "Provider profile required", "Create your business profile before advertising.", '<a class="btn btn-brand" href="/profile/edit">Create profile</a>');
      } else {
        container.innerHTML = `<div class="alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
      }
    }
  }

  function setDefaultDates() {
    const start = document.getElementById("adStartDate");
    const end = document.getElementById("adEndDate");
    const today = new Date();
    const later = new Date();
    later.setDate(today.getDate() + 14);
    const iso = (date) => date.toISOString().slice(0, 10);
    start.value = iso(today);
    end.value = iso(later);
  }

  async function submit(event) {
    event.preventDefault();
    KC.clearErrors(form);
    const submitButton = form.querySelector("[type='submit']");
    const data = new FormData(form);
    KC.setBusy(submitButton, true, "Submitting…");
    try {
      await KC.upload("/advertisements", data);
      form.reset();
      setDefaultDates();
      bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      KC.toast("Advertisement submitted for moderation");
      await load();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submitButton, false);
    }
  }

  async function remove(id) {
    const confirmed = await KC.confirm("Delete this advertisement? This cannot be undone.", "Delete advertisement");
    if (!confirmed) return;
    try {
      await KC.del(`/advertisements/${id}`);
      KC.toast("Advertisement deleted");
      await load();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const me = await KC.requireAuth(["provider"]);
    if (!me) return;
    setDefaultDates();
    form.addEventListener("submit", submit);
    await load();
  });
})();
