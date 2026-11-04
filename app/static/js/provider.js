(function () {
  "use strict";

  const root = document.getElementById("providerDetail");
  if (!root) return;
  const providerId = Number(root.dataset.providerId);
  const content = document.getElementById("providerContent");
  const reviewList = document.getElementById("reviewList");
  const reviewPagination = document.getElementById("reviewPagination");
  const writeButton = document.getElementById("writeReviewButton");
  let me = null;
  let provider = null;
  let reviewPage = 1;

  function safeUrl(value, fallback) {
    if (!value) return fallback;
    return String(value).startsWith("http://") || String(value).startsWith("https://")
      ? value
      : fallback;
  }

  function serviceCard(service) {
    return `<div class="col-md-6">
      <div class="service-item">
        <div class="d-flex justify-content-between gap-2">
          <h3 class="h6 mb-1">${KC.escapeHtml(service.title)}</h3>
          <span class="chip">${KC.escapeHtml(service.category_name || "Service")}</span>
        </div>
        <p class="small text-muted mb-2">${KC.escapeHtml(service.description || "Contact the provider for details about this service.")}</p>
        <span class="price small">${KC.escapeHtml(KC.priceRange(service.price_min, service.price_max))}</span>
      </div>
    </div>`;
  }

  function distribution(summary) {
    const distributionData = (summary && summary.distribution) || {};
    const total = Number(summary && summary.review_count) || 0;
    let rows = "";
    for (let star = 5; star >= 1; star -= 1) {
      const value = Number(distributionData[star] || distributionData[String(star)] || 0);
      const width = total ? Math.round((value / total) * 100) : 0;
      rows += `<div class="d-flex align-items-center gap-2 mb-1 small">
        <span class="text-muted rating-bar-label">${star}★</span>
        <div class="progress flex-grow-1" role="progressbar" aria-label="${star} star reviews" aria-valuenow="${width}" aria-valuemin="0" aria-valuemax="100" data-bar-width="${width}">
          <div class="progress-bar bg-warning" data-width="${width}"></div>
        </div>
        <span class="text-muted rating-bar-count">${value}</span>
      </div>`;
    }
    return rows;
  }

  function paintBars() {
    document.querySelectorAll("[data-bar-width]").forEach((bar) => {
      const inner = bar.querySelector("[data-width]");
      if (inner) inner.style.width = `${Number(bar.dataset.barWidth) || 0}%`;
    });
  }

  function renderProvider(data) {
    provider = data;
    const categories = [...new Set((data.services || []).map((service) => service.category_name).filter(Boolean))];
    const isCustomer = me && me.role === "customer";
    const canContact = Boolean(data.contact_phone || data.whatsapp_link);
    const favoriteHtml = me && me.role !== "customer"
      ? ""
      : `<button class="btn ${data.is_favorite ? "btn-brand" : "btn-outline-brand"}" type="button" id="favoriteButton">
          <i class="bi ${data.is_favorite ? "bi-heart-fill" : "bi-heart"} me-1"></i>
          ${data.is_favorite ? "Saved" : "Save provider"}
        </button>`;
    const reviewAction = isCustomer
      ? '<button class="btn btn-outline-brand" type="button" id="inlineReviewButton"><i class="bi bi-star me-1"></i> Write a review</button>'
      : !me
        ? '<a class="btn btn-outline-brand" href="/login">Log in to review</a>'
        : "";
    content.innerHTML = `
      <div class="card-soft overflow-hidden">
        <div class="profile-cover"></div>
        <div class="p-4 p-lg-5 pt-0">
          <div class="d-flex flex-column flex-lg-row gap-4 align-items-lg-end mt-n4 mb-4">
            <img class="profile-avatar" src="${KC.avatarUrl(data)}" alt="">
            <div class="flex-grow-1">
              <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
                <h1 class="h2 mb-0">${KC.escapeHtml(data.business_name)}</h1>
                ${KC.verificationBadge(data.verification_status)}
              </div>
              <p class="text-muted mb-1">${KC.escapeHtml(data.provider_name || "Local service provider")} · ${Number(data.experience_years) || 0} years experience</p>
              <div class="d-flex flex-wrap align-items-center gap-2">
                ${KC.ratingBadge(data.average_rating, data.review_count)}
                <span class="small text-muted"><i class="bi bi-geo-alt"></i> ${KC.escapeHtml([data.area, data.city].filter(Boolean).join(", ") || "Location not provided")}</span>
              </div>
            </div>
            <div class="d-flex flex-wrap gap-2">
              ${favoriteHtml}
              ${reviewAction}
            </div>
          </div>
          ${data.verification_status === "pending" ? '<div class="alert alert-warning small">This provider’s verification is still pending. Review their details and agree on expectations before hiring.</div>' : ""}
          <div class="row g-4">
            <div class="col-lg-7">
              <h2 class="h5 mb-2">About this provider</h2>
              <p class="text-muted">${KC.escapeHtml(data.description || "This provider has not added a description yet. Contact them to ask about their services and availability.")}</p>
              <div class="d-flex flex-wrap gap-1 mt-3">
                ${(categories.length ? categories : ["Local services"]).map((name) => `<span class="chip">${KC.escapeHtml(name)}</span>`).join("")}
              </div>
            </div>
            <div class="col-lg-5">
              <div class="card-soft p-3">
                <h2 class="h6 mb-3">Contact &amp; details</h2>
                <dl class="detail-list small">
                  <dt>Location</dt><dd>${KC.escapeHtml([data.area, data.city].filter(Boolean).join(", ") || "Not provided")}</dd>
                  ${data.address ? `<dt>Address</dt><dd>${KC.escapeHtml(data.address)}</dd>` : ""}
                  <dt>Experience</dt><dd>${Number(data.experience_years) || 0} years</dd>
                  <dt>Member since</dt><dd>${KC.formatDate(data.created_at)}</dd>
                  ${data.contact_phone ? `<dt>Phone</dt><dd>${KC.escapeHtml(data.contact_phone)}</dd>` : ""}
                </dl>
                ${canContact ? `<div class="d-grid gap-2 mt-3">
                  ${data.call_link ? `<a class="btn btn-brand" href="${KC.escapeHtml(data.call_link)}"><i class="bi bi-telephone me-1"></i> Call provider</a>` : ""}
                  ${data.whatsapp_link ? `<a class="btn btn-outline-brand" href="${KC.escapeHtml(data.whatsapp_link)}" target="_blank" rel="noopener noreferrer"><i class="bi bi-whatsapp me-1"></i> Message on WhatsApp</a>` : ""}
                </div>` : '<p class="small text-muted mb-0 mt-3">This provider has not added public contact details.</p>'}
              </div>
            </div>
          </div>
          ${(data.work_images || []).length ? `<hr class="my-4">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <h2 class="h4 mb-0">Work photos</h2>
            <span class="small text-muted">${data.work_images.length} photo${data.work_images.length === 1 ? "" : "s"}</span>
          </div>
          <div class="work-gallery">
            ${data.work_images.map((image) => `<a class="work-photo" href="${KC.escapeHtml(image.image_path)}" target="_blank" rel="noopener noreferrer">
              <img src="${KC.escapeHtml(image.image_path)}" alt="Work photo from ${KC.escapeHtml(data.business_name)}" loading="lazy">
            </a>`).join("")}
          </div>` : ""}
          <hr class="my-4">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <h2 class="h4 mb-0">Services</h2>
            <span class="small text-muted">${(data.services || []).length} active service${(data.services || []).length === 1 ? "" : "s"}</span>
          </div>
          <div class="row g-3">
            ${(data.services || []).length ? data.services.map(serviceCard).join("") : '<div class="col-12 text-muted small">No active services listed yet.</div>'}
          </div>
        </div>
      </div>`;
    paintBars();

    const favoriteButton = document.getElementById("favoriteButton");
    if (favoriteButton) favoriteButton.addEventListener("click", toggleFavorite);
    const inlineReview = document.getElementById("inlineReviewButton");
    if (inlineReview) {
      inlineReview.addEventListener("click", () => {
        bootstrap.Modal.getOrCreateInstance(document.getElementById("reviewModal")).show();
      });
    }
    if (isCustomer && writeButton) writeButton.classList.remove("d-none");
    document.title = `${data.business_name} | KaamConnect`;
    loadReviews(1);
  }

  async function loadProvider() {
    try {
      const data = await KC.get(`/providers/${providerId}`);
      renderProvider(data);
    } catch (error) {
      content.innerHTML = `<div class="card-soft p-5 text-center">
        <h1 class="h3">Provider not available</h1>
        <p class="text-muted">${KC.escapeHtml(error.status === 404 ? "This provider profile could not be found or is not publicly visible." : error.message)}</p>
        <a class="btn btn-brand" href="/search">Browse providers</a>
      </div>`;
      document.getElementById("reviewSection").hidden = true;
    }
  }

  function reviewCard(review) {
    return `<article class="review-item">
      <div class="d-flex gap-3">
        <span class="review-avatar">${KC.escapeHtml(KC.initials(review.customer_name))}</span>
        <div class="flex-grow-1 min-w-0">
          <div class="d-flex flex-wrap justify-content-between gap-2">
            <div>
              <strong>${KC.escapeHtml(review.customer_name)}</strong>
              <div class="small">${KC.stars(review.rating)}</div>
            </div>
            <time class="small text-muted" datetime="${KC.escapeHtml(review.created_at)}">${KC.formatDate(review.created_at)}</time>
          </div>
          <p class="mb-0 mt-2 text-muted">${KC.escapeHtml(review.comment || "No written comment.")}</p>
        </div>
      </div>
    </article>`;
  }

  async function loadReviews(page) {
    if (!reviewList) return;
    reviewPage = page || 1;
    try {
      const data = await KC.get(`/reviews?provider_id=${providerId}&page=${reviewPage}&page_size=5`);
      const summary = provider && provider.review_summary ? provider.review_summary : {};
      if (!data.items.length) {
        reviewList.innerHTML = `<div class="row g-4 align-items-start">
          <div class="col-lg-4">
            <div class="text-center">
              <div class="rating-large">${(Number(summary.average_rating) || 0).toFixed(1)}</div>
              ${KC.stars(Number(summary.average_rating) || 0)}
              <p class="small text-muted mt-1 mb-0">${Number(summary.review_count) || 0} approved review${Number(summary.review_count) === 1 ? "" : "s"}</p>
            </div>
          </div>
          <div class="col-lg-8">${KC.emptyState("bi-chat-square-text", "No reviews yet", "Be the first customer to share an experience after working with this provider.")}</div>
        </div>`;
      } else {
        reviewList.innerHTML = `<div class="row g-4">
          <div class="col-lg-4">
            <div class="text-center">
              <div class="rating-large">${(Number(summary.average_rating) || 0).toFixed(1)}</div>
              ${KC.stars(Number(summary.average_rating) || 0)}
              <p class="small text-muted mt-1 mb-3">${Number(summary.review_count) || data.total} approved review${Number(summary.review_count || data.total) === 1 ? "" : "s"}</p>
            </div>
            <div class="mt-2">${distribution(summary)}</div>
          </div>
          <div class="col-lg-8">${data.items.map(reviewCard).join("")}</div>
        </div>`;
        paintBars();
      }
      KC.pagination(reviewPagination, data, (nextPage) => {
        loadReviews(nextPage);
        document.getElementById("reviewSection").scrollIntoView({ behavior: "smooth" });
      });
    } catch (error) {
      reviewList.innerHTML = `<div class="alert alert-danger mb-0">${KC.escapeHtml(error.message)}</div>`;
    }
  }

  async function toggleFavorite() {
    if (!me) {
      window.location.href = `/login?next=${encodeURIComponent(`/providers/${providerId}`)}`;
      return;
    }
    const button = document.getElementById("favoriteButton");
    if (!button) return;
    KC.setBusy(button, true, "Saving…");
    try {
      if (provider.is_favorite) {
        await KC.del(`/favorites/${providerId}`);
        provider.is_favorite = false;
        KC.toast("Removed from favorites");
      } else {
        await KC.post(`/favorites/${providerId}`);
        provider.is_favorite = true;
        KC.toast("Provider saved to favorites");
      }
      renderProvider(provider);
    } catch (error) {
      KC.setBusy(button, false);
      KC.toast(error.message, "error");
    }
  }

  function initReviewForm() {
    const form = document.getElementById("reviewForm");
    if (!form) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      KC.clearErrors(form);
      const submit = form.querySelector("[type='submit']");
      const payload = {
        provider_id: providerId,
        rating: Number(form.elements.rating.value),
        comment: form.elements.comment.value.trim() || null,
      };
      if (!payload.rating) {
        form.elements.rating.classList.add("is-invalid");
        return;
      }
      KC.setBusy(submit, true, "Submitting…");
      try {
        const review = await KC.post("/reviews", payload);
        form.reset();
        bootstrap.Modal.getOrCreateInstance(document.getElementById("reviewModal")).hide();
        KC.toast(review.status === "pending" ? "Review submitted and awaiting moderation" : "Thank you — your review is published");
        await loadProvider();
      } catch (error) {
        KC.showError(form.querySelector(".form-error"), error);
        if (error.errors) KC.applyFieldErrors(form, error.errors);
      } finally {
        KC.setBusy(submit, false);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    initReviewForm();
    try {
      me = await KC.me();
    } catch (_error) {
      me = null;
    }
    await loadProvider();
  });
})();
