(function () {
  "use strict";

  const container = document.getElementById("reviewsContainer");
  const pagination = document.getElementById("reviewsPagination");
  const statusSelect = document.getElementById("providerReviewStatus");
  let me = null;
  let page = 1;
  let currentItems = [];

  function statusBadge(status) {
    const map = {
      approved: "badge-verified",
      pending: "badge-pending",
      rejected: "badge-rejected",
    };
    return `<span class="badge ${map[status] || "badge-neutral"}">${KC.escapeHtml(status || "unknown")}</span>`;
  }

  function customerCard(review) {
    return `<article class="card-soft p-4 mb-3">
      <div class="d-flex flex-wrap justify-content-between gap-3">
        <div class="min-w-0">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <a class="fw-semibold text-decoration-none" href="/providers/${Number(review.provider_id)}">${KC.escapeHtml(review.provider_name)}</a>
            ${statusBadge(review.status)}
          </div>
          <div>${KC.stars(review.rating)} <span class="small text-muted">${KC.formatDate(review.created_at)}</span></div>
          <p class="text-muted mb-0 mt-2">${KC.escapeHtml(review.comment || "No written comment.")}</p>
        </div>
        <div class="d-flex gap-2 align-self-start">
          <button class="btn btn-sm btn-outline-brand" type="button" data-edit-review="${Number(review.id)}">Edit</button>
          <button class="btn btn-sm btn-outline-danger" type="button" data-delete-review="${Number(review.id)}">Delete</button>
        </div>
      </div>
    </article>`;
  }

  function providerCard(review) {
    return `<article class="card-soft p-4 mb-3">
      <div class="d-flex flex-wrap justify-content-between gap-3">
        <div class="d-flex gap-3 min-w-0">
          <span class="review-avatar">${KC.escapeHtml(KC.initials(review.customer_name))}</span>
          <div class="min-w-0">
            <div class="d-flex align-items-center gap-2 flex-wrap">
              <strong>${KC.escapeHtml(review.customer_name)}</strong>
              ${statusBadge(review.status)}
            </div>
            <div>${KC.stars(review.rating)} <span class="small text-muted">${KC.formatDate(review.created_at)}</span></div>
            <p class="text-muted mb-0 mt-2">${KC.escapeHtml(review.comment || "No written comment.")}</p>
          </div>
        </div>
        <span class="small text-muted">Customer review</span>
      </div>
    </article>`;
  }

  async function load() {
    if (!container) return;
    container.innerHTML = '<div class="card-soft p-4 text-muted">Loading reviews…</div>';
    try {
      let path;
      if (me.role === "provider") {
        const query = new URLSearchParams({ page: String(page), page_size: "10" });
        if (statusSelect && statusSelect.value) query.set("status", statusSelect.value);
        path = `/reviews/provider/me?${query.toString()}`;
      } else {
        path = `/reviews/me?page=${page}&page_size=10`;
      }
      const data = await KC.get(path);
      currentItems = data.items;
      if (!data.items.length) {
        container.innerHTML = KC.emptyState(
          me.role === "provider" ? "bi-chat-square-text" : "bi-star",
          "No reviews to show",
          me.role === "provider"
            ? "Customer reviews will appear here after they are submitted."
            : "Once you work with a verified provider, you can share a review from their profile."
        );
        pagination.innerHTML = "";
        return;
      }
      container.innerHTML = data.items.map(me.role === "provider" ? providerCard : customerCard).join("");
      if (me.role === "customer") {
        container.querySelectorAll("[data-edit-review]").forEach((button) => {
          button.addEventListener("click", () => openEdit(Number(button.dataset.editReview)));
        });
        container.querySelectorAll("[data-delete-review]").forEach((button) => {
          button.addEventListener("click", () => remove(Number(button.dataset.deleteReview)));
        });
      }
      KC.pagination(pagination, data, (next) => {
        page = next;
        load();
      });
    } catch (error) {
      if (error.status === 404) {
        container.innerHTML = KC.emptyState("bi-person-vcard", "Provider profile required", "Create your provider profile before viewing business reviews.", '<a class="btn btn-brand" href="/profile/edit">Create profile</a>');
      } else {
        container.innerHTML = `<div class="alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
      }
    }
  }

  function openEdit(id) {
    const review = currentItems.find((item) => item.id === id);
    if (!review) return;
    const form = document.getElementById("editReviewForm");
    KC.clearErrors(form);
    form.elements.review_id.value = String(review.id);
    form.elements.rating.value = String(review.rating);
    form.elements.comment.value = review.comment || "";
    bootstrap.Modal.getOrCreateInstance(document.getElementById("editReviewModal")).show();
  }

  async function saveEdit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const id = form.elements.review_id.value;
    const submit = form.querySelector("[type='submit']");
    KC.clearErrors(form);
    KC.setBusy(submit, true, "Saving…");
    try {
      await KC.patch(`/reviews/${id}`, {
        rating: Number(form.elements.rating.value),
        comment: form.elements.comment.value.trim() || null,
      });
      bootstrap.Modal.getOrCreateInstance(document.getElementById("editReviewModal")).hide();
      KC.toast("Review updated");
      await load();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function remove(id) {
    const confirmed = await KC.confirm("Delete this review permanently?", "Delete review");
    if (!confirmed) return;
    try {
      await KC.del(`/reviews/${id}`);
      KC.toast("Review deleted");
      await load();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    me = await KC.requireAuth(["customer", "provider"]);
    if (!me) return;
    const title = document.getElementById("reviewsTitle");
    const subtitle = document.getElementById("reviewsSubtitle");
    if (me.role === "provider") {
      if (title) title.textContent = "Reviews for your business";
      if (subtitle) subtitle.textContent = "Read customer feedback and check moderation status.";
      if (statusSelect) statusSelect.classList.remove("d-none");
      statusSelect.addEventListener("change", () => {
        page = 1;
        load();
      });
    }
    document.getElementById("editReviewForm").addEventListener("submit", saveEdit);
    await load();
  });
})();
