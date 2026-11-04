(function () {
  "use strict";

  function setStat(name, value) {
    document.querySelectorAll(`[data-stat="${name}"]`).forEach((el) => {
      el.textContent = value == null ? "—" : String(value);
    });
  }

  function reviewRow(review) {
    return `<div class="review-item py-3">
      <div class="d-flex justify-content-between gap-3">
        <div class="min-w-0">
          <div class="small">${KC.stars(review.rating)}</div>
          <strong class="small">${KC.escapeHtml(review.provider_name || "Provider")}</strong>
          <p class="small text-muted mb-0 mt-1">${KC.escapeHtml((review.comment || "No comment").slice(0, 140))}</p>
        </div>
        <span class="badge ${review.status === "approved" ? "badge-verified" : review.status === "pending" ? "badge-pending" : "badge-rejected"} align-self-start">${KC.escapeHtml(review.status)}</span>
      </div>
    </div>`;
  }

  function complaintRow(complaint) {
    const badge =
      complaint.status === "resolved"
        ? "badge-verified"
        : complaint.status === "rejected"
          ? "badge-rejected"
          : complaint.status === "in_review"
            ? "badge-pending"
            : "badge-neutral";
    return `<div class="border-bottom py-3">
      <div class="d-flex flex-wrap justify-content-between gap-2">
        <div>
          <strong class="small">${KC.escapeHtml(complaint.subject)}</strong>
          <div class="small text-muted">${KC.escapeHtml(complaint.provider_name || "General complaint")} · ${KC.formatDate(complaint.created_at)}</div>
        </div>
        <span class="badge ${badge} align-self-start">${KC.escapeHtml(complaint.status.replace("_", " "))}</span>
      </div>
      ${complaint.admin_response ? `<p class="small mb-0 mt-2 p-2 bg-brand-soft rounded"><strong>Staff response:</strong> ${KC.escapeHtml(complaint.admin_response)}</p>` : ""}
    </div>`;
  }

  async function customerDashboard() {
    const user = await KC.requireAuth(["customer"]);
    if (!user) return;
    const name = document.getElementById("dashboardName");
    if (name) name.textContent = user.full_name.split(" ")[0];
    try {
      const summary = await KC.get("/users/me/summary");
      ["favorite_count", "review_count", "complaint_count", "open_complaint_count"].forEach((key) => {
        setStat(key, summary[key]);
      });
    } catch (error) {
      KC.toast(error.message, "error");
    }

    const favorites = document.getElementById("customerFavorites");
    try {
      const items = await KC.get("/favorites/me");
      if (!items.length) {
        favorites.innerHTML = `<div class="col-12">${KC.emptyState(
          "bi-heart",
          "No saved providers",
          "When you find a provider you like, save them here for later.",
          '<a class="btn btn-brand btn-sm" href="/search">Browse providers</a>'
        )}</div>`;
      } else {
        favorites.innerHTML = items
          .slice(0, 2)
          .map(
            (item) => `<div class="col-md-6"><div class="service-item h-100">
              <div class="d-flex gap-2">
                <img class="provider-avatar" src="${KC.avatarUrl(item)}" alt="">
                <div class="min-w-0">
                  <a class="fw-semibold text-decoration-none" href="/providers/${Number(item.id)}">${KC.escapeHtml(item.business_name)}</a>
                  <div class="small text-muted">${KC.escapeHtml([item.area, item.city].filter(Boolean).join(", "))}</div>
                  ${KC.ratingBadge(item.average_rating, item.review_count)}
                </div>
              </div>
            </div></div>`
          )
          .join("");
      }
    } catch (error) {
      favorites.innerHTML = `<div class="col-12 text-danger small">${KC.escapeHtml(error.message)}</div>`;
    }

    const reviews = document.getElementById("customerReviews");
    try {
      const data = await KC.get("/reviews/me?page_size=3");
      reviews.innerHTML = data.items.length
        ? data.items.map(reviewRow).join("")
        : KC.emptyState("bi-star", "No reviews yet", "After working with a verified provider, share your experience.");
    } catch (error) {
      reviews.innerHTML = `<div class="text-danger small">${KC.escapeHtml(error.message)}</div>`;
    }

    const complaints = document.getElementById("customerComplaints");
    try {
      const items = await KC.get("/complaints/me");
      complaints.innerHTML = items.length
        ? items.slice(0, 4).map(complaintRow).join("")
        : KC.emptyState("bi-flag", "No complaints filed", "If something goes wrong, you can report it to the moderation team.");
    } catch (error) {
      complaints.innerHTML = `<div class="text-danger small">${KC.escapeHtml(error.message)}</div>`;
    }
  }

  function statusBadge(status) {
    if (status === "verified") return '<span class="badge badge-verified"><i class="bi bi-patch-check-fill me-1"></i>Verified provider</span>';
    if (status === "rejected") return '<span class="badge badge-rejected"><i class="bi bi-x-circle me-1"></i>Verification rejected</span>';
    return '<span class="badge badge-pending"><i class="bi bi-hourglass-split me-1"></i>Pending verification</span>';
  }

  async function providerDashboard() {
    const user = await KC.requireAuth(["provider"]);
    if (!user) return;
    const alertBox = document.getElementById("providerAlert");

    let summary = null;
    try {
      summary = await KC.get("/users/me/summary");
      const providerSummary = summary.provider || {};
      const business = document.getElementById("providerBusinessName");
      if (business) business.textContent = providerSummary.business_name || "Your business";
      const status = document.getElementById("providerStatus");
      if (status) status.innerHTML = statusBadge(providerSummary.verification_status);
      setStat("verification", providerSummary.verification_status || "—");
      setStat("service_count", providerSummary.service_count || 0);
      setStat("pending_ad_count", providerSummary.pending_ad_count || 0);
      const rating = summary.rating || {};
      setStat("rating", `${(Number(rating.average_rating) || 0).toFixed(1)} (${Number(rating.review_count) || 0})`);
    } catch (error) {
      if (alertBox) alertBox.innerHTML = `<div class="alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
    }

    let profile = null;
    const profileSummary = document.getElementById("providerProfileSummary");
    try {
      profile = await KC.get("/providers/me");
      profileSummary.innerHTML = `<div class="d-flex align-items-center gap-3 mb-3">
        <img class="provider-avatar" src="${KC.avatarUrl(profile)}" alt="">
        <div>
          <strong>${KC.escapeHtml(profile.business_name)}</strong>
          <div class="small text-muted">${KC.escapeHtml([profile.area, profile.city].filter(Boolean).join(", ") || "No location set")}</div>
        </div>
      </div>
      <dl class="detail-list small">
        <dt>Public phone</dt><dd>${KC.escapeHtml(profile.contact_phone || "Not set")}</dd>
        <dt>WhatsApp</dt><dd>${KC.escapeHtml(profile.whatsapp_number || "Not set")}</dd>
        <dt>Experience</dt><dd>${Number(profile.experience_years) || 0} years</dd>
        <dt>Description</dt><dd>${profile.description ? "Added" : "Not added"}</dd>
      </dl>
      <a class="btn btn-sm btn-outline-brand mt-3" href="/profile/edit">Update profile</a>`;
      const missing = [];
      if (!profile.description) missing.push("add a description");
      if (!profile.contact_phone && !profile.whatsapp_number) missing.push("add a public contact number");
      if (!profile.profile_image) missing.push("upload a profile image");
      if (!summary || !summary.provider || !summary.provider.service_count) missing.push("add at least one service");
      if (missing.length && alertBox) {
        alertBox.innerHTML = `<div class="alert alert-warning"><strong>Complete your profile:</strong> ${KC.escapeHtml(missing.join(", "))}. A complete profile helps customers decide.</div>`;
      }
    } catch (error) {
      profileSummary.innerHTML = `<div class="text-danger small">${KC.escapeHtml(error.message)}</div>`;
    }

    const reviews = document.getElementById("providerReviews");
    try {
      const data = await KC.get("/reviews/provider/me?page_size=4");
      if (!data.items.length) {
        reviews.innerHTML = KC.emptyState("bi-chat-square-text", "No reviews yet", "Approved customer reviews will appear here. Build trust by completing jobs and asking customers to review.");
      } else {
        reviews.innerHTML = data.items
          .map(
            (review) => `<div class="review-item py-3">
              <div class="d-flex justify-content-between gap-2">
                <div class="min-w-0">
                  <div class="small">${KC.stars(review.rating)}</div>
                  <strong class="small">${KC.escapeHtml(review.customer_name)}</strong>
                  <p class="small text-muted mb-0 mt-1">${KC.escapeHtml((review.comment || "No comment").slice(0, 160))}</p>
                </div>
                <span class="badge ${review.status === "approved" ? "badge-verified" : review.status === "pending" ? "badge-pending" : "badge-rejected"} align-self-start">${KC.escapeHtml(review.status)}</span>
              </div>
            </div>`
          )
          .join("");
      }
    } catch (error) {
      reviews.innerHTML = `<div class="text-danger small">${KC.escapeHtml(error.message)}</div>`;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.dataset.page;
    if (page === "customer-dashboard") customerDashboard();
    if (page === "provider-dashboard") providerDashboard();
  });
})();
