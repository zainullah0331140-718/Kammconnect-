(function () {
  "use strict";

  const API_BASE = "/api/v1";
  const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

  class ApiError extends Error {
    constructor(status, message, errors) {
      super(message || "Request failed");
      this.status = status;
      this.errors = errors || [];
    }
  }

  function getCookie(name) {
    const parts = document.cookie ? document.cookie.split("; ") : [];
    for (const part of parts) {
      const index = part.indexOf("=");
      if (index === -1) continue;
      if (part.slice(0, index) === name) {
        return decodeURIComponent(part.slice(index + 1));
      }
    }
    return null;
  }

  async function ensureCsrf(force) {
    let token = getCookie("kc_csrf");
    if (token && !force) return token;
    const response = await fetch(`${API_BASE}/auth/csrf`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (response.ok) {
      const data = await response.json().catch(() => ({}));
      return data.csrf_token || getCookie("kc_csrf");
    }
    return getCookie("kc_csrf");
  }

  async function parseResponse(response) {
    if (response.status === 204) return null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json().catch(() => null);
    }
    const text = await response.text().catch(() => "");
    return text ? { detail: text.slice(0, 500) } : null;
  }

  async function tryRefresh() {
    try {
      const token = getCookie("kc_csrf");
      const headers = { Accept: "application/json" };
      if (token) headers["X-CSRF-Token"] = token;
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "same-origin",
        headers,
      });
      return response.ok;
    } catch (_error) {
      return false;
    }
  }

  async function request(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    const init = {
      method,
      credentials: "same-origin",
      headers,
    };
    if (options.formData) {
      init.body = options.formData;
    } else if (options.body !== undefined) {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(options.body);
    }
    if (!SAFE_METHODS.has(method)) {
      const csrf = await ensureCsrf();
      if (csrf) headers.set("X-CSRF-Token", csrf);
    }

    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, init);
    } catch (_error) {
      throw new ApiError(0, "Network error. Check your connection and try again.");
    }

    if (
      response.status === 401 &&
      options.retry !== false &&
      !path.startsWith("/auth/login") &&
      !path.startsWith("/auth/refresh") &&
      !path.startsWith("/auth/register") &&
      !path.startsWith("/auth/me")
    ) {
      const refreshed = await tryRefresh();
      if (refreshed) {
        return request(path, { ...options, retry: false });
      }
    }

    const data = await parseResponse(response);
    if (!response.ok) {
      let detail =
        (data && (data.detail || data.message)) ||
        (response.status === 403
          ? "You do not have permission to do that."
          : "Request failed. Please try again.");
      let fieldErrors = data && data.errors;
      if (Array.isArray(detail)) {
        fieldErrors = detail.map((item) => ({
          field: Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null,
          message: item.msg || "Invalid value",
        }));
        detail = "Please check the highlighted fields and try again.";
      } else if (detail && typeof detail === "object") {
        detail = "Request failed. Please try again.";
      }
      throw new ApiError(response.status, String(detail), fieldErrors);
    }
    return data;
  }

  const KC = {
    ApiError,
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body }),
    patch: (path, body) => request(path, { method: "PATCH", body }),
    del: (path, body) => request(path, { method: "DELETE", body }),
    upload: (path, formData, method) =>
      request(path, { method: method || "POST", formData }),
    csrf: ensureCsrf,
  };

  let mePromise = null;

  KC.me = function (force) {
    if (!mePromise || force) {
      mePromise = request("/auth/me").catch((error) => {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      });
    }
    return mePromise;
  };

  KC.logout = async function () {
    try {
      await request("/auth/logout", { method: "POST" });
    } catch (_error) {
      // Clear the local session view even if the server token was already gone.
    }
    mePromise = null;
    window.location.href = "/";
  };

  KC.dashboardPath = function (role) {
    if (role === "admin") return "/admin";
    if (role === "provider") return "/dashboard/provider";
    return "/dashboard/customer";
  };

  KC.safeNext = function (value) {
    if (!value) return null;
    if (!value.startsWith("/") || value.startsWith("//")) return null;
    return value;
  };

  KC.requireAuth = async function (roles) {
    let user = null;
    try {
      user = await KC.me();
    } catch (_error) {
      user = null;
    }
    if (!user) {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?next=${next}`;
      return null;
    }
    if (roles && roles.length && !roles.includes(user.role)) {
      window.location.href = "/unauthorized";
      return null;
    }
    return user;
  };

  KC.redirectAfterLogin = function (user) {
    const params = new URLSearchParams(window.location.search);
    const next = KC.safeNext(params.get("next"));
    window.location.href = next || KC.dashboardPath(user.role);
  };

  KC.escapeHtml = function (value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  };

  KC.formatDate = function (value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    }).format(date);
  };

  KC.formatDateTime = function (value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  KC.formatMoney = function (value) {
    if (value == null || value === "") return "";
    const number = Number(value);
    if (Number.isNaN(number)) return "";
    return `Rs ${new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(number)}`;
  };

  KC.priceRange = function (min, max) {
    if (min == null && max == null) return "Price on request";
    if (min != null && max != null) {
      if (Number(min) === Number(max)) return KC.formatMoney(min);
      return `${KC.formatMoney(min)} – ${KC.formatMoney(max)}`;
    }
    if (min != null) return `From ${KC.formatMoney(min)}`;
    return `Up to ${KC.formatMoney(max)}`;
  };

  KC.stars = function (rating) {
    const numeric = Number(rating) || 0;
    let html = '<span class="rating-stars" aria-hidden="true">';
    for (let i = 1; i <= 5; i += 1) {
      if (numeric >= i) html += '<i class="bi bi-star-fill"></i>';
      else if (numeric >= i - 0.5) html += '<i class="bi bi-star-half"></i>';
      else html += '<i class="bi bi-star"></i>';
    }
    html += "</span>";
    return html;
  };

  KC.ratingBadge = function (average, count) {
    const value = Number(average) || 0;
    return `<span class="rating-badge">${KC.stars(value)} <strong>${value.toFixed(
      1
    )}</strong> <span class="text-muted">(${Number(count) || 0})</span></span>`;
  };

  KC.verificationBadge = function (status) {
    if (status === "verified") {
      return '<span class="badge badge-verified"><i class="bi bi-patch-check-fill"></i> Verified</span>';
    }
    if (status === "pending") {
      return '<span class="badge badge-pending"><i class="bi bi-hourglass-split"></i> Pending verification</span>';
    }
    if (status === "rejected") {
      return '<span class="badge badge-rejected"><i class="bi bi-x-circle"></i> Verification rejected</span>';
    }
    return "";
  };

  KC.initials = function (name) {
    return String(name || "?")
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0] || "")
      .join("")
      .toUpperCase();
  };

  KC.avatarUrl = function (profile) {
    const image = profile && profile.profile_image;
    if (image && image.startsWith("/uploads/")) return image;
    return "/static/images/avatar.svg";
  };

  KC.providerCard = function (provider) {
    const categories = (provider.services || [])
      .map((service) => service.category_name)
      .filter(Boolean);
    const uniqueCategories = [...new Set(categories)].slice(0, 3);
    const chips = uniqueCategories.length
      ? uniqueCategories
      .map((name) => `<span class="chip">${KC.escapeHtml(name)}</span>`)
          .join("")
      : '<span class="chip">Service provider</span>';
    return `
      <article class="provider-card card h-100 border-0">
        <div class="card-body">
          <div class="d-flex gap-3 align-items-start">
            <img class="provider-avatar" src="${KC.avatarUrl(provider)}" alt="" loading="lazy">
            <div class="flex-grow-1 min-w-0">
              <div class="d-flex justify-content-between gap-2 align-items-start">
                <h3 class="h6 mb-1"><a class="stretched-link-title" href="/providers/${Number(
                  provider.id
                )}">${KC.escapeHtml(provider.business_name)}</a></h3>
                ${KC.verificationBadge(provider.verification_status)}
              </div>
              <div class="small text-muted mb-1">${KC.escapeHtml(
                provider.provider_name || ""
              )}</div>
              <div class="small mb-2"><i class="bi bi-geo-alt"></i> ${KC.escapeHtml(
                [provider.area, provider.city].filter(Boolean).join(", ") || "Location not provided"
              )}</div>
              <div class="d-flex flex-wrap gap-2 align-items-center">
                ${KC.ratingBadge(provider.average_rating, provider.review_count)}
                <span class="small text-muted">${Number(provider.experience_years) || 0} yrs experience</span>
              </div>
            </div>
          </div>
          <div class="d-flex flex-wrap gap-1 mt-3">${chips}</div>
          <p class="small text-muted mt-3 mb-0 provider-card-description">${KC.escapeHtml(
            (provider.description || "This provider has not added a description yet.").slice(0, 150)
          )}</p>
        </div>
        <div class="card-footer bg-transparent border-0 pt-0 pb-3 px-3">
          <a class="btn btn-sm btn-outline-brand w-100" href="/providers/${Number(
            provider.id
          )}">View profile <i class="bi bi-arrow-right"></i></a>
        </div>
      </article>`;
  };

  KC.emptyState = function (icon, title, text, actionHtml) {
    return `<div class="empty-state text-center py-5">
      <div class="empty-icon"><i class="bi ${KC.escapeHtml(icon)}"></i></div>
      <h3 class="h5 mt-3">${KC.escapeHtml(title)}</h3>
      <p class="text-muted mb-3">${KC.escapeHtml(text)}</p>
      ${actionHtml || ""}
    </div>`;
  };

  KC.toast = function (message, type) {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const tone = type === "error" ? "danger" : type === "warning" ? "warning" : "success";
    const icon =
      tone === "danger"
        ? "bi-exclamation-octagon"
        : tone === "warning"
          ? "bi-exclamation-triangle"
          : "bi-check-circle";
    const wrapper = document.createElement("div");
    wrapper.className = `toast align-items-center text-bg-${tone} border-0`;
    wrapper.setAttribute("role", "alert");
    wrapper.innerHTML = `<div class="d-flex"><div class="toast-body"><i class="bi ${icon} me-1"></i>${KC.escapeHtml(
      message
    )}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
    container.appendChild(wrapper);
    const toast = new bootstrap.Toast(wrapper, { delay: 5000 });
    toast.show();
    wrapper.addEventListener("hidden.bs.toast", () => wrapper.remove());
  };

  KC.showError = function (element, error) {
    if (!element) {
      KC.toast(error && error.message ? error.message : "Something went wrong", "error");
      return;
    }
    let message = error && error.message ? error.message : "Something went wrong";
    if (error && error.errors && error.errors.length) {
      message += " " + error.errors.map((item) => item.message).join(" ");
    }
    element.textContent = message;
    element.classList.remove("d-none");
  };

  KC.clearErrors = function (form) {
    if (!form) return;
    form.querySelectorAll(".is-invalid").forEach((el) => el.classList.remove("is-invalid"));
    form.querySelectorAll(".invalid-feedback.js-error").forEach((el) => {
      el.textContent = "";
      el.classList.add("d-none");
    });
    const alert = form.querySelector(".form-error");
    if (alert) {
      alert.textContent = "";
      alert.classList.add("d-none");
    }
  };

  KC.applyFieldErrors = function (form, errors) {
    if (!form || !errors) return;
    for (const item of errors) {
      if (!item.field) continue;
      const field = form.querySelector(`[name="${CSS.escape(item.field)}"]`);
      if (!field) continue;
      field.classList.add("is-invalid");
      const feedback = field.parentElement.querySelector(".invalid-feedback.js-error");
      if (feedback) {
        feedback.textContent = item.message;
        feedback.classList.remove("d-none");
      }
    }
  };

  KC.setBusy = function (button, busy, busyText) {
    if (!button) return;
    if (busy) {
      button.dataset.originalHtml = button.innerHTML;
      button.disabled = true;
      button.innerHTML = `<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>${KC.escapeHtml(
        busyText || "Please wait…"
      )}`;
    } else {
      button.disabled = false;
      if (button.dataset.originalHtml) button.innerHTML = button.dataset.originalHtml;
    }
  };

  KC.confirm = function (message, title) {
    return new Promise((resolve) => {
      const modalEl = document.getElementById("confirmModal");
      if (!modalEl || !window.bootstrap) {
        resolve(window.confirm(message));
        return;
      }
      modalEl.querySelector(".confirm-message").textContent = message;
      if (title) modalEl.querySelector(".modal-title").textContent = title;
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      let settled = false;
      const yes = modalEl.querySelector(".confirm-yes");
      const handler = () => {
        settled = true;
        resolve(true);
      };
      const hiddenHandler = () => {
        yes.removeEventListener("click", handler);
        modalEl.removeEventListener("hidden.bs.modal", hiddenHandler);
        if (!settled) resolve(false);
      };
      yes.addEventListener("click", handler, { once: true });
      modalEl.addEventListener("hidden.bs.modal", hiddenHandler, { once: true });
      modal.show();
    });
  };

  KC.pagination = function (container, data, onPage) {
    if (!container) return;
    const totalPages = Number(data.pages) || 0;
    if (totalPages <= 1) {
      container.innerHTML = "";
      return;
    }
    const page = Number(data.page) || 1;
    const items = [];
    items.push(
      `<li class="page-item ${page <= 1 ? "disabled" : ""}"><button class="page-link" data-page="${
        page - 1
      }" aria-label="Previous">&laquo;</button></li>`
    );
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, page + 2);
    if (start > 1) {
      items.push(
        `<li class="page-item"><button class="page-link" data-page="1">1</button></li>`
      );
      if (start > 2) items.push('<li class="page-item disabled"><span class="page-link">…</span></li>');
    }
    for (let i = start; i <= end; i += 1) {
      items.push(
        `<li class="page-item ${i === page ? "active" : ""}"><button class="page-link" data-page="${i}">${i}</button></li>`
      );
    }
    if (end < totalPages) {
      if (end < totalPages - 1)
        items.push('<li class="page-item disabled"><span class="page-link">…</span></li>');
      items.push(
        `<li class="page-item"><button class="page-link" data-page="${totalPages}">${totalPages}</button></li>`
      );
    }
    items.push(
      `<li class="page-item ${page >= totalPages ? "disabled" : ""}"><button class="page-link" data-page="${
        page + 1
      }" aria-label="Next">&raquo;</button></li>`
    );
    container.innerHTML = `<ul class="pagination justify-content-center mb-0">${items.join(
      ""
    )}</ul>`;
    container.querySelectorAll("button[data-page]").forEach((button) => {
      button.addEventListener("click", () => {
        const target = Number(button.dataset.page);
        if (target >= 1 && target <= totalPages) onPage(target);
      });
    });
  };

  KC.initNav = async function () {
    const guest = document.getElementById("navGuest");
    const userArea = document.getElementById("navUser");
    const logoutButtons = document.querySelectorAll("[data-action='logout']");
    logoutButtons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        KC.logout();
      });
    });
    let user = null;
    try {
      user = await KC.me();
    } catch (_error) {
      user = null;
    }
    if (!user) {
      if (guest) guest.classList.remove("d-none");
      document.querySelectorAll("[data-auth-only]").forEach((el) => el.classList.add("d-none"));
      return;
    }
    if (guest) guest.classList.add("d-none");
    if (userArea) userArea.classList.remove("d-none");
    document.querySelectorAll("[data-user-avatar]").forEach((avatar) => {
      avatar.innerHTML = `<img src="${KC.escapeHtml(KC.avatarUrl(user))}" alt="">`;
    });
    document.querySelectorAll("[data-user-name]").forEach((el) => {
      el.textContent = user.full_name;
    });
    document.querySelectorAll("[data-user-role]").forEach((el) => {
      el.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
    });
    document.querySelectorAll("[data-dashboard-link]").forEach((el) => {
      el.href = KC.dashboardPath(user.role);
    });
    document.querySelectorAll("[data-role-only]").forEach((el) => {
      const roles = (el.dataset.roleOnly || "").split(",").map((r) => r.trim());
      el.classList.toggle("d-none", !roles.includes(user.role));
    });
    document.querySelectorAll("[data-role-not]").forEach((el) => {
      const roles = (el.dataset.roleNot || "").split(",").map((r) => r.trim());
      el.classList.toggle("d-none", roles.includes(user.role));
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    KC.initNav();
    document.querySelectorAll("[data-action='reload']").forEach((button) => {
      button.addEventListener("click", () => window.location.reload());
    });
  });

  window.KC = KC;
})();
