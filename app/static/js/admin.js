(function () {
  "use strict";

  let me = null;
  const page = document.body.dataset.page;

  function urlParam(name) {
    return new URLSearchParams(window.location.search).get(name) || "";
  }

  function replaceQuery(values) {
    const query = new URLSearchParams();
    Object.entries(values).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const text = query.toString();
    window.history.replaceState({}, "", text ? `${window.location.pathname}?${text}` : window.location.pathname);
  }

  function empty(text) {
    return `<div class="text-muted small py-3">${KC.escapeHtml(text)}</div>`;
  }

  function roleBadge(role) {
    const classes = { admin: "badge-rejected", provider: "badge-verified", customer: "badge-neutral" };
    return `<span class="badge ${classes[role] || "badge-neutral"}">${KC.escapeHtml(role)}</span>`;
  }

  function statusBadge(status) {
    const classes = {
      approved: "badge-verified",
      verified: "badge-verified",
      resolved: "badge-verified",
      live: "badge-verified",
      pending: "badge-pending",
      in_review: "badge-pending",
      rejected: "badge-rejected",
      expired: "badge-neutral",
      open: "badge-neutral",
    };
    return `<span class="badge ${classes[status] || "badge-neutral"}">${KC.escapeHtml(String(status).replace("_", " "))}</span>`;
  }

  const ACTION_LABELS = {
    "auth.login": "Logged in",
    "auth.register": "Registered",
    "auth.password_reset_requested": "Password reset requested",
    "auth.password_reset": "Password reset completed",
    "auth.password_changed": "Password changed",
    "admin.password_reset": "Admin sent password reset",
    "user.update": "Updated profile",
    "user.delete_self": "Deleted own account",
    "admin.user.update": "Admin updated user",
    "admin.user.delete": "Admin deleted user",
    "provider.verification": "Provider verification",
    "review.moderate": "Review moderation",
    "review.delete": "Review deleted",
    "complaint.update": "Complaint updated",
    "complaint.delete": "Complaint deleted",
    "advertisement.moderate": "Advertisement moderation",
    "category.create": "Category created",
    "category.update": "Category updated",
    "category.delete": "Category deleted",
  };

  function actionLabel(action) {
    return ACTION_LABELS[action] || String(action || "").replace(/[._]/g, " ");
  }

  function setStat(name, value) {
    document.querySelectorAll(`[data-stat="${name}"]`).forEach((el) => {
      el.textContent = value == null ? "—" : String(value);
    });
  }

  function errorAlert(element, error) {
    if (element) element.innerHTML = `<div class="alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
    KC.toast(error.message, "error");
  }

  async function dashboard() {
    const alert = document.getElementById("adminDashboardAlert");
    try {
      const stats = await KC.get("/admin/stats");
      [
        "total_users",
        "total_customers",
        "total_providers",
        "total_admins",
        "verified_providers",
        "pending_providers",
        "rejected_providers",
        "pending_reviews",
        "open_complaints",
        "pending_ads",
        "active_categories",
        "total_favorites",
      ].forEach((key) => setStat(key, stats[key]));
      const audit = document.getElementById("recentAudit");
      if (audit) {
        audit.innerHTML = (stats.recent_audit || []).length
          ? `<div class="table-responsive"><table class="table table-sm align-middle mb-0">
              <thead><tr><th>Action</th><th>Actor</th><th>Entity</th><th>When</th></tr></thead>
              <tbody>${stats.recent_audit
                .map(
                  (item) => `<tr>
                    <td class="small">${KC.escapeHtml(actionLabel(item.action))}</td>
                    <td class="small">${KC.escapeHtml(item.actor_name || "System")}</td>
                    <td class="small">${KC.escapeHtml(item.entity_type)}${item.entity_id ? ` #${KC.escapeHtml(item.entity_id)}` : ""}</td>
                    <td class="small text-muted">${KC.formatDateTime(item.created_at)}</td>
                  </tr>`
                )
                .join("")}</tbody>
            </table></div>`
          : empty("No audit activity recorded yet.");
      }
    } catch (error) {
      errorAlert(alert, error);
    }

    const logins = document.getElementById("recentLogins");
    if (logins) {
      KC.get("/admin/audit-logs?action=auth.login&page_size=5")
        .then((data) => {
          logins.innerHTML = data.items.length
            ? data.items
                .map(
                  (item) => `<div class="d-flex justify-content-between gap-2 border-bottom py-2">
                    <div class="min-w-0">
                      <div class="small fw-semibold text-truncate">${KC.escapeHtml(item.actor_name || "Unknown")}</div>
                      <div class="small text-muted text-truncate">${KC.escapeHtml(item.actor_email || "")}${item.ip_address ? ` · ${KC.escapeHtml(item.ip_address)}` : ""}</div>
                    </div>
                    <div class="small text-muted text-nowrap">${KC.formatDateTime(item.created_at)}</div>
                  </div>`
                )
                .join("")
            : empty("No logins recorded yet.");
        })
        .catch((error) => { logins.innerHTML = empty(error.message); });
    }

    const providers = document.getElementById("pendingProviders");
    KC.get("/admin/providers?status=pending&page_size=5")
      .then((data) => {
        if (!providers) return;
        providers.innerHTML = data.items.length
          ? data.items
              .map(
                (item) => `<div class="d-flex justify-content-between gap-2 border-bottom py-2">
                  <div class="min-w-0">
                    <a class="small fw-semibold text-decoration-none" href="/providers/${Number(item.id)}">${KC.escapeHtml(item.business_name)}</a>
                    <div class="small text-muted">${KC.escapeHtml(item.provider_name)} · ${KC.escapeHtml([item.area, item.city].filter(Boolean).join(", "))}</div>
                  </div>
                  <a class="btn btn-sm btn-outline-brand align-self-start" href="/admin/verification?status=pending">Review</a>
                </div>`
              )
              .join("")
          : empty("No providers waiting for verification.");
      })
      .catch((error) => { if (providers) providers.innerHTML = empty(error.message); });

    const complaints = document.getElementById("openComplaints");
    KC.get("/admin/complaints?status=open&page_size=5")
      .then((data) => {
        if (!complaints) return;
        complaints.innerHTML = data.items.length
          ? data.items
              .map(
                (item) => `<div class="d-flex justify-content-between gap-2 border-bottom py-2">
                  <div class="min-w-0">
                    <div class="small fw-semibold text-truncate">${KC.escapeHtml(item.subject)}</div>
                    <div class="small text-muted">${KC.escapeHtml(item.user_name)} · ${KC.formatDate(item.created_at)}</div>
                  </div>
                  <a class="btn btn-sm btn-outline-brand align-self-start" href="/admin/complaints?status=open">Review</a>
                </div>`
              )
              .join("")
          : empty("No open complaints.");
      })
      .catch((error) => { if (complaints) complaints.innerHTML = empty(error.message); });

    const reviews = document.getElementById("pendingReviews");
    KC.get("/admin/reviews?status=pending&page_size=5")
      .then((data) => {
        if (!reviews) return;
        reviews.innerHTML = data.items.length
          ? data.items
              .map(
                (item) => `<div class="d-flex justify-content-between gap-2 border-bottom py-2">
                  <div class="min-w-0">
                    <div class="small">${KC.stars(item.rating)} <span class="fw-semibold">${KC.escapeHtml(item.provider_name)}</span></div>
                    <div class="small text-muted text-truncate">${KC.escapeHtml((item.comment || "No comment").slice(0, 90))}</div>
                  </div>
                  <a class="btn btn-sm btn-outline-brand align-self-start" href="/admin/reviews?status=pending">Review</a>
                </div>`
              )
              .join("")
          : empty("No reviews waiting for moderation.");
      })
      .catch((error) => { if (reviews) reviews.innerHTML = empty(error.message); });

    const ads = document.getElementById("pendingAds");
    KC.get("/admin/advertisements?status=pending&page_size=5")
      .then((data) => {
        if (!ads) return;
        ads.innerHTML = data.items.length
          ? data.items
              .map(
                (item) => `<div class="d-flex justify-content-between gap-2 border-bottom py-2">
                  <div class="min-w-0">
                    <div class="small fw-semibold text-truncate">${KC.escapeHtml(item.title)}</div>
                    <div class="small text-muted">${KC.escapeHtml(item.provider_name)}</div>
                  </div>
                  <a class="btn btn-sm btn-outline-brand align-self-start" href="/admin/advertisements?status=pending">Review</a>
                </div>`
              )
              .join("")
          : empty("No advertisements waiting for review.");
      })
      .catch((error) => { if (ads) ads.innerHTML = empty(error.message); });
  }

  let usersPage = 1;
  async function loadUsers() {
    const body = document.getElementById("adminUsersBody");
    const alert = document.getElementById("adminUsersAlert");
    if (!body) return;
    const q = document.getElementById("userSearch").value.trim();
    const role = document.getElementById("userRoleFilter").value;
    replaceQuery({ q, role, page: usersPage > 1 ? usersPage : "" });
    body.innerHTML = '<tr><td colspan="7" class="text-muted p-4">Loading users…</td></tr>';
    try {
      const query = new URLSearchParams({ page: String(usersPage), page_size: "20" });
      if (q) query.set("q", q);
      if (role) query.set("role", role);
      const data = await KC.get(`/admin/users?${query.toString()}`);
      if (!data.items.length) {
        body.innerHTML = '<tr><td colspan="7" class="text-muted p-4">No users match these filters.</td></tr>';
      } else {
        body.innerHTML = data.items
          .map((user) => {
            const self = user.id === me.id;
            return `<tr>
              <td>
                <div class="fw-semibold">${KC.escapeHtml(user.full_name)} ${self ? '<span class="badge badge-neutral ms-1">You</span>' : ""}</div>
                <div class="small text-muted">${KC.escapeHtml(user.email)}</div>
                <div class="small text-muted">${KC.escapeHtml(user.phone || "")}</div>
              </td>
              <td>
                ${self
                  ? roleBadge(user.role)
                  : `<select class="form-select form-select-sm" data-role-select="${Number(user.id)}" aria-label="Role for ${KC.escapeHtml(user.full_name)}">
                      ${["customer", "provider", "admin"].map((option) => `<option value="${option}" ${option === user.role ? "selected" : ""}>${option}</option>`).join("")}
                    </select>`}
              </td>
              <td class="small">${user.provider_id ? `<a href="/providers/${Number(user.provider_id)}">${KC.escapeHtml(user.business_name || "View profile")}</a><div>${KC.verificationBadge(user.verification_status)}</div>` : '<span class="text-muted">—</span>'}</td>
              <td>${user.is_active ? '<span class="badge badge-verified">Active</span>' : '<span class="badge badge-rejected">Inactive</span>'}</td>
              <td class="small text-muted">${KC.formatDate(user.created_at)}</td>
              <td class="small text-muted">${user.last_login_at ? `${KC.formatDateTime(user.last_login_at)}<div>${Number(user.login_count) || 0} login${Number(user.login_count) === 1 ? "" : "s"}</div>` : "Never"}</td>
              <td class="text-end">
                ${self
                  ? '<span class="small text-muted">Manage in settings</span>'
                  : `<div class="btn-group btn-group-sm flex-wrap">
                      <button class="btn btn-outline-secondary" type="button" data-reset-user="${Number(user.id)}" data-user-name="${KC.escapeHtml(user.full_name)}" data-user-email="${KC.escapeHtml(user.email)}">Reset password</button>
                      <button class="btn ${user.is_active ? "btn-outline-danger" : "btn-outline-brand"}" type="button" data-toggle-user="${Number(user.id)}" data-active="${user.is_active ? "1" : "0"}">${user.is_active ? "Deactivate" : "Activate"}</button>
                      <button class="btn btn-outline-danger" type="button" data-delete-user="${Number(user.id)}" data-user-name="${KC.escapeHtml(user.full_name)}" data-user-role="${KC.escapeHtml(user.role)}">Delete</button>
                    </div>`}
              </td>
            </tr>`;
          })
          .join("");
      }
      const count = document.getElementById("adminUsersCount");
      if (count) count.textContent = `${data.total} user${data.total === 1 ? "" : "s"} found`;
      KC.pagination(document.getElementById("adminUsersPagination"), data, (next) => {
        usersPage = next;
        loadUsers();
      });
      bindUserActions();
    } catch (error) {
      body.innerHTML = `<tr><td colspan="7" class="text-danger p-4">${KC.escapeHtml(error.message)}</td></tr>`;
      if (alert) alert.innerHTML = "";
    }
  }

  async function deleteManagedUser(id, label, kind) {
    const noun = kind === "provider" ? "provider" : "user";
    const confirmed = await KC.confirm(
      `Delete ${noun} “${label}”? This permanently removes the account and all related data${kind === "provider" ? ", including services, reviews, favorites, complaints, and advertisements" : ""}.`,
      `Delete ${noun}`
    );
    if (!confirmed) return false;
    try {
      await KC.del(`/admin/users/${id}`);
      KC.toast(`${noun.charAt(0).toUpperCase() + noun.slice(1)} deleted`);
      return true;
    } catch (error) {
      KC.toast(error.message, "error");
      return false;
    }
  }

  async function resetManagedUser(id, name, email) {
    const confirmed = await KC.confirm(
      `Send a single-use password reset link to ${email}?`,
      "Reset password"
    );
    if (!confirmed) return;
    try {
      const data = await KC.post(`/admin/users/${id}/password-reset`, {});
      if (data.reset_url) {
        document.getElementById("resetLinkMessage").textContent =
          `Share this single-use link with ${name} (${email}).`;
        document.getElementById("resetLinkInput").value = data.reset_url;
        bootstrap.Modal.getOrCreateInstance(document.getElementById("resetLinkModal")).show();
      } else {
        KC.toast(data.message || "Password reset link sent");
      }
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  function bindUserActions() {
    document.querySelectorAll("[data-role-select]").forEach((select) => {
      select.addEventListener("change", async () => {
        const id = Number(select.dataset.roleSelect);
        const confirmed = await KC.confirm(`Change this account's role to “${select.value}”?`, "Change role");
        if (!confirmed) {
          loadUsers();
          return;
        }
        try {
          await KC.patch(`/admin/users/${id}`, { role: select.value });
          KC.toast("User role updated");
          loadUsers();
        } catch (error) {
          KC.toast(error.message, "error");
          loadUsers();
        }
      });
    });
    document.querySelectorAll("[data-toggle-user]").forEach((button) => {
      button.addEventListener("click", async () => {
        const id = Number(button.dataset.toggleUser);
        const activate = button.dataset.active !== "1";
        const confirmed = await KC.confirm(
          activate ? "Activate this account?" : "Deactivate this account? Their sessions will be revoked.",
          activate ? "Activate user" : "Deactivate user"
        );
        if (!confirmed) return;
        try {
          await KC.patch(`/admin/users/${id}`, { is_active: activate });
          KC.toast(activate ? "User activated" : "User deactivated");
          loadUsers();
        } catch (error) {
          KC.toast(error.message, "error");
        }
      });
    });
    document.querySelectorAll("[data-delete-user]").forEach((button) => {
      button.addEventListener("click", async () => {
        const deleted = await deleteManagedUser(
          Number(button.dataset.deleteUser),
          button.dataset.userName,
          button.dataset.userRole
        );
        if (deleted) loadUsers();
      });
    });
    document.querySelectorAll("[data-reset-user]").forEach((button) => {
      button.addEventListener("click", () => {
        resetManagedUser(
          Number(button.dataset.resetUser),
          button.dataset.userName,
          button.dataset.userEmail
        );
      });
    });
  }

  let verificationPage = 1;
  async function loadVerification() {
    const body = document.getElementById("verificationBody");
    if (!body) return;
    const q = document.getElementById("verificationSearch").value.trim();
    const status = document.getElementById("verificationStatusFilter").value;
    replaceQuery({ q, status, page: verificationPage > 1 ? verificationPage : "" });
    body.innerHTML = '<tr><td colspan="5" class="text-muted p-4">Loading providers…</td></tr>';
    try {
      const query = new URLSearchParams({ page: String(verificationPage), page_size: "20" });
      if (q) query.set("q", q);
      if (status) query.set("status", status);
      const data = await KC.get(`/admin/providers?${query.toString()}`);
      body.innerHTML = data.items.length
        ? data.items
            .map(
              (provider) => `<tr>
                <td>
                  <div class="fw-semibold"><a class="text-decoration-none" href="/providers/${Number(provider.id)}">${KC.escapeHtml(provider.business_name)}</a></div>
                  <div class="small text-muted">${KC.escapeHtml(provider.provider_name)} · ${KC.escapeHtml(provider.provider_email)}</div>
                  ${provider.verification_note ? `<div class="small text-muted">Note: ${KC.escapeHtml(provider.verification_note)}</div>` : ""}
                </td>
                <td class="small">${KC.escapeHtml([provider.area, provider.city].filter(Boolean).join(", ") || "—")}</td>
                <td>${KC.verificationBadge(provider.verification_status)}</td>
                <td>${Number(provider.pending_reviews) || 0}</td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-success" type="button" data-verify="${Number(provider.id)}" data-business="${KC.escapeHtml(provider.business_name)}">Verify</button>
                    <button class="btn btn-outline-danger" type="button" data-reject="${Number(provider.id)}" data-business="${KC.escapeHtml(provider.business_name)}">Reject</button>
                    <button class="btn btn-outline-danger" type="button" data-delete-provider="${Number(provider.user_id)}" data-business="${KC.escapeHtml(provider.business_name)}">Delete</button>
                  </div>
                </td>
              </tr>`
            )
            .join("")
        : '<tr><td colspan="5" class="text-muted p-4">No providers match these filters.</td></tr>';
      const count = document.getElementById("verificationCount");
      if (count) count.textContent = `${data.total} provider${data.total === 1 ? "" : "s"} found`;
      KC.pagination(document.getElementById("verificationPagination"), data, (next) => {
        verificationPage = next;
        loadVerification();
      });
      body.querySelectorAll("[data-verify]").forEach((button) => {
        button.addEventListener("click", () => openVerification(button.dataset.verify, "verified", button.dataset.business));
      });
      body.querySelectorAll("[data-reject]").forEach((button) => {
        button.addEventListener("click", () => openVerification(button.dataset.reject, "rejected", button.dataset.business));
      });
      body.querySelectorAll("[data-delete-provider]").forEach((button) => {
        button.addEventListener("click", async () => {
          const deleted = await deleteManagedUser(
            Number(button.dataset.deleteProvider),
            button.dataset.business,
            "provider"
          );
          if (deleted) loadVerification();
        });
      });
    } catch (error) {
      body.innerHTML = `<tr><td colspan="5" class="text-danger p-4">${KC.escapeHtml(error.message)}</td></tr>`;
    }
  }

  function openVerification(id, status, business) {
    const form = document.getElementById("verificationForm");
    KC.clearErrors(form);
    form.elements.provider_id.value = id;
    form.elements.status.value = status;
    form.elements.note.value = "";
    document.getElementById("verificationActionText").textContent =
      `${status === "verified" ? "Approve verification for" : "Reject verification for"} ${business}.`;
    bootstrap.Modal.getOrCreateInstance(document.getElementById("verificationModal")).show();
  }

  async function saveVerification(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const submit = form.querySelector("[type='submit']");
    const id = form.elements.provider_id.value;
    const status = form.elements.status.value;
    const note = form.elements.note.value.trim();
    KC.clearErrors(form);
    if (status === "rejected" && !note) {
      form.elements.note.classList.add("is-invalid");
      const feedback = form.elements.note.parentElement.querySelector(".js-error");
      if (feedback) {
        feedback.textContent = "Add a clear reason for rejecting verification.";
        feedback.classList.remove("d-none");
      }
      return;
    }
    KC.setBusy(submit, true, "Saving…");
    try {
      await KC.patch(`/admin/providers/${id}/verification`, { status, note: note || null });
      bootstrap.Modal.getOrCreateInstance(document.getElementById("verificationModal")).hide();
      KC.toast(`Provider ${status}`);
      loadVerification();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  let categories = [];
  async function loadCategories() {
    const body = document.getElementById("categoriesBody");
    if (!body) return;
    try {
      categories = await KC.get("/admin/categories");
      body.innerHTML = categories.length
        ? categories
            .map(
              (category) => `<tr>
                <td>
                  <div class="d-flex align-items-center gap-2">
                    <span class="category-icon category-icon-sm"><i class="bi bi-${KC.escapeHtml(category.icon || "grid")}"></i></span>
                    <div>
                      <div class="fw-semibold">${KC.escapeHtml(category.name)}</div>
                      <div class="small text-muted">${KC.escapeHtml(category.description || "")}</div>
                    </div>
                  </div>
                </td>
                <td><code>${KC.escapeHtml(category.slug)}</code></td>
                <td>${Number(category.provider_count) || 0}</td>
                <td>${category.is_active ? '<span class="badge badge-verified">Active</span>' : '<span class="badge badge-neutral">Inactive</span>'}</td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-brand" type="button" data-edit-category="${Number(category.id)}">Edit</button>
                    <button class="btn btn-outline-secondary" type="button" data-toggle-category="${Number(category.id)}">${category.is_active ? "Deactivate" : "Activate"}</button>
                    <button class="btn btn-outline-danger" type="button" data-delete-category="${Number(category.id)}">Delete</button>
                  </div>
                </td>
              </tr>`
            )
            .join("")
        : '<tr><td colspan="5" class="text-muted p-4">No categories yet.</td></tr>';
      body.querySelectorAll("[data-edit-category]").forEach((button) => {
        button.addEventListener("click", () => openCategory(Number(button.dataset.editCategory)));
      });
      body.querySelectorAll("[data-toggle-category]").forEach((button) => {
        button.addEventListener("click", () => toggleCategory(Number(button.dataset.toggleCategory)));
      });
      body.querySelectorAll("[data-delete-category]").forEach((button) => {
        button.addEventListener("click", () => deleteCategory(Number(button.dataset.deleteCategory)));
      });
    } catch (error) {
      body.innerHTML = `<tr><td colspan="5" class="text-danger p-4">${KC.escapeHtml(error.message)}</td></tr>`;
    }
  }

  function openCategory(id) {
    const form = document.getElementById("categoryForm");
    KC.clearErrors(form);
    form.reset();
    form.elements.is_active.checked = true;
    const item = categories.find((category) => category.id === id);
    form.elements.category_id.value = item ? String(item.id) : "";
    form.elements.name.value = item ? item.name : "";
    form.elements.slug.value = item ? item.slug : "";
    form.elements.description.value = item ? item.description || "" : "";
    form.elements.icon.value = item ? item.icon || "" : "";
    form.elements.is_active.checked = item ? item.is_active : true;
    document.getElementById("categoryModalTitle").textContent = item ? "Edit category" : "Add category";
    bootstrap.Modal.getOrCreateInstance(document.getElementById("categoryModal")).show();
  }

  async function saveCategory(event) {
    event.preventDefault();
    const form = event.currentTarget;
    KC.clearErrors(form);
    const id = form.elements.category_id.value;
    const payload = {
      name: form.elements.name.value.trim(),
      slug: form.elements.slug.value.trim() || null,
      description: form.elements.description.value.trim() || null,
      icon: form.elements.icon.value.trim() || null,
      is_active: form.elements.is_active.checked,
    };
    const submit = form.querySelector("[type='submit']");
    KC.setBusy(submit, true, "Saving…");
    try {
      if (id) await KC.patch(`/admin/categories/${id}`, payload);
      else await KC.post("/admin/categories", payload);
      bootstrap.Modal.getOrCreateInstance(document.getElementById("categoryModal")).hide();
      KC.toast(id ? "Category updated" : "Category created");
      loadCategories();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function toggleCategory(id) {
    const item = categories.find((category) => category.id === id);
    if (!item) return;
    try {
      await KC.patch(`/admin/categories/${id}`, { is_active: !item.is_active });
      KC.toast(item.is_active ? "Category deactivated" : "Category activated");
      loadCategories();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  async function deleteCategory(id) {
    const item = categories.find((category) => category.id === id);
    if (!item) return;
    const confirmed = await KC.confirm(`Delete “${item.name}”? Categories in use cannot be deleted.`, "Delete category");
    if (!confirmed) return;
    try {
      await KC.del(`/admin/categories/${id}`);
      KC.toast("Category deleted");
      loadCategories();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  let reviewsPage = 1;
  async function loadAdminReviews() {
    const body = document.getElementById("adminReviewsBody");
    if (!body) return;
    const q = document.getElementById("reviewSearch").value.trim();
    const status = document.getElementById("reviewStatusFilter").value;
    replaceQuery({ q, status, page: reviewsPage > 1 ? reviewsPage : "" });
    body.innerHTML = '<tr><td colspan="5" class="text-muted p-4">Loading reviews…</td></tr>';
    try {
      const query = new URLSearchParams({ page: String(reviewsPage), page_size: "20" });
      if (q) query.set("q", q);
      if (status) query.set("status", status);
      const data = await KC.get(`/admin/reviews?${query.toString()}`);
      body.innerHTML = data.items.length
        ? data.items
            .map(
              (review) => `<tr>
                <td class="review-comment-cell">
                  <div>${KC.stars(review.rating)} <span class="small text-muted">#${Number(review.id)}</span></div>
                  <div class="small text-muted">${KC.escapeHtml((review.comment || "No comment").slice(0, 180))}</div>
                </td>
                <td><a class="small text-decoration-none" href="/providers/${Number(review.provider_id)}">${KC.escapeHtml(review.provider_name)}</a></td>
                <td class="small">${KC.escapeHtml(review.customer_name)}<div class="text-muted">${KC.escapeHtml(review.customer_email)}</div></td>
                <td>${statusBadge(review.status)}</td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    ${review.status !== "approved" ? `<button class="btn btn-outline-success" type="button" data-review-status="approved" data-review-id="${Number(review.id)}">Approve</button>` : ""}
                    ${review.status !== "rejected" ? `<button class="btn btn-outline-warning" type="button" data-review-status="rejected" data-review-id="${Number(review.id)}">Reject</button>` : ""}
                    <button class="btn btn-outline-danger" type="button" data-delete-admin-review="${Number(review.id)}">Delete</button>
                  </div>
                </td>
              </tr>`
            )
            .join("")
        : '<tr><td colspan="5" class="text-muted p-4">No reviews match these filters.</td></tr>';
      const count = document.getElementById("adminReviewsCount");
      if (count) count.textContent = `${data.total} review${data.total === 1 ? "" : "s"} found`;
      KC.pagination(document.getElementById("adminReviewsPagination"), data, (next) => {
        reviewsPage = next;
        loadAdminReviews();
      });
      body.querySelectorAll("[data-review-status]").forEach((button) => {
        button.addEventListener("click", () => openReviewModeration(Number(button.dataset.reviewId), button.dataset.reviewStatus));
      });
      body.querySelectorAll("[data-delete-admin-review]").forEach((button) => {
        button.addEventListener("click", () => deleteAdminReview(Number(button.dataset.deleteAdminReview)));
      });
    } catch (error) {
      body.innerHTML = `<tr><td colspan="5" class="text-danger p-4">${KC.escapeHtml(error.message)}</td></tr>`;
    }
  }

  function openReviewModeration(id, status) {
    const form = document.getElementById("reviewModerationForm");
    KC.clearErrors(form);
    form.elements.review_id.value = id;
    form.elements.status.value = status;
    form.elements.note.value = "";
    document.getElementById("reviewActionText").textContent =
      status === "approved" ? `Approve review #${id} for public display.` : `Reject review #${id}; it will not display publicly.`;
    bootstrap.Modal.getOrCreateInstance(document.getElementById("reviewModerationModal")).show();
  }

  async function saveReviewModeration(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const id = form.elements.review_id.value;
    const submit = form.querySelector("[type='submit']");
    KC.clearErrors(form);
    KC.setBusy(submit, true, "Saving…");
    try {
      await KC.patch(`/admin/reviews/${id}`, {
        status: form.elements.status.value,
        note: form.elements.note.value.trim() || null,
      });
      bootstrap.Modal.getOrCreateInstance(document.getElementById("reviewModerationModal")).hide();
      KC.toast("Review decision saved");
      loadAdminReviews();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function deleteAdminReview(id) {
    const confirmed = await KC.confirm("Delete this review permanently? This cannot be undone.", "Delete review");
    if (!confirmed) return;
    try {
      await KC.del(`/admin/reviews/${id}`);
      KC.toast("Review deleted");
      loadAdminReviews();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  let complaintsPage = 1;
  let complaintItems = [];
  async function loadAdminComplaints() {
    const container = document.getElementById("adminComplaintsList");
    if (!container) return;
    const status = document.getElementById("complaintStatusFilter").value;
    replaceQuery({ status, page: complaintsPage > 1 ? complaintsPage : "" });
    container.innerHTML = '<div class="card-soft p-4 text-muted">Loading complaints…</div>';
    try {
      const query = new URLSearchParams({ page: String(complaintsPage), page_size: "15" });
      if (status) query.set("status", status);
      const data = await KC.get(`/admin/complaints?${query.toString()}`);
      complaintItems = data.items;
      container.innerHTML = data.items.length
        ? data.items
            .map(
              (item) => `<article class="card-soft p-4 mb-3">
                <div class="d-flex flex-wrap justify-content-between gap-2">
                  <div>
                    <div class="d-flex align-items-center gap-2 flex-wrap">
                      <h2 class="h6 mb-0">${KC.escapeHtml(item.subject)}</h2>
                      ${statusBadge(item.status)}
                    </div>
                    <div class="small text-muted">${KC.escapeHtml(item.user_name)} · ${KC.escapeHtml(item.user_email)}${item.provider_name ? ` · ${KC.escapeHtml(item.provider_name)}` : ""} · ${KC.formatDateTime(item.created_at)}</div>
                  </div>
                  <button class="btn btn-sm btn-outline-brand align-self-start" type="button" data-update-complaint="${Number(item.id)}">Update</button>
                </div>
                <p class="small text-muted mb-2 mt-3">${KC.escapeHtml(item.message)}</p>
                ${item.admin_response ? `<div class="small p-3 bg-brand-soft rounded"><strong>Staff response:</strong> ${KC.escapeHtml(item.admin_response)}</div>` : ""}
              </article>`
            )
            .join("")
        : KC.emptyState("bi-flag", "No complaints found", "No complaints match the selected status.");
      KC.pagination(document.getElementById("adminComplaintsPagination"), data, (next) => {
        complaintsPage = next;
        loadAdminComplaints();
      });
      container.querySelectorAll("[data-update-complaint]").forEach((button) => {
        button.addEventListener("click", () => openComplaintUpdate(Number(button.dataset.updateComplaint)));
      });
    } catch (error) {
      container.innerHTML = `<div class="alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
    }
  }

  function openComplaintUpdate(id) {
    const item = complaintItems.find((complaint) => complaint.id === id);
    if (!item) return;
    const form = document.getElementById("complaintUpdateForm");
    KC.clearErrors(form);
    form.elements.complaint_id.value = String(item.id);
    form.elements.status.value = item.status;
    form.elements.admin_response.value = item.admin_response || "";
    document.getElementById("complaintUpdateContext").textContent =
      `${item.subject} — filed by ${item.user_name}${item.provider_name ? ` about ${item.provider_name}` : ""}.`;
    bootstrap.Modal.getOrCreateInstance(document.getElementById("complaintUpdateModal")).show();
  }

  async function saveComplaint(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const id = form.elements.complaint_id.value;
    const submit = form.querySelector("[type='submit']");
    KC.clearErrors(form);
    KC.setBusy(submit, true, "Saving…");
    try {
      await KC.patch(`/admin/complaints/${id}`, {
        status: form.elements.status.value,
        admin_response: form.elements.admin_response.value.trim() || null,
      });
      bootstrap.Modal.getOrCreateInstance(document.getElementById("complaintUpdateModal")).hide();
      KC.toast("Complaint updated");
      loadAdminComplaints();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  let adsPage = 1;
  let adItems = [];
  async function loadAdminAds() {
    const body = document.getElementById("adminAdsBody");
    if (!body) return;
    const status = document.getElementById("adStatusFilter").value;
    replaceQuery({ status, page: adsPage > 1 ? adsPage : "" });
    body.innerHTML = '<tr><td colspan="5" class="text-muted p-4">Loading advertisements…</td></tr>';
    try {
      const query = new URLSearchParams({ page: String(adsPage), page_size: "15" });
      if (status) query.set("status", status);
      const data = await KC.get(`/admin/advertisements?${query.toString()}`);
      adItems = data.items;
      body.innerHTML = data.items.length
        ? data.items
            .map(
              (ad) => `<tr>
                <td>
                  <div class="d-flex gap-2">
                    <img class="ad-thumb" src="${KC.escapeHtml(ad.image_path)}" alt="" loading="lazy">
                    <div class="min-w-0">
                      <div class="fw-semibold">${KC.escapeHtml(ad.title)}</div>
                      <div class="small text-muted text-truncate">${KC.escapeHtml(ad.description.slice(0, 90))}</div>
                      ${ad.admin_note ? `<div class="small text-muted">Note: ${KC.escapeHtml(ad.admin_note)}</div>` : ""}
                    </div>
                  </div>
                </td>
                <td class="small">${KC.escapeHtml(ad.provider_name)}</td>
                <td class="small">${KC.formatDate(ad.start_date)}<br>${KC.formatDate(ad.end_date)}</td>
                <td>${statusBadge(ad.is_live ? "live" : ad.status)}</td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <a class="btn btn-outline-secondary" href="${KC.escapeHtml(ad.destination_url)}" target="_blank" rel="noopener noreferrer">Open</a>
                    <button class="btn btn-outline-brand" type="button" data-moderate-ad="${Number(ad.id)}">Moderate</button>
                  </div>
                </td>
              </tr>`
            )
            .join("")
        : '<tr><td colspan="5" class="text-muted p-4">No advertisements match these filters.</td></tr>';
      const count = document.getElementById("adminAdsCount");
      if (count) count.textContent = `${data.total} advertisement${data.total === 1 ? "" : "s"} found`;
      KC.pagination(document.getElementById("adminAdsPagination"), data, (next) => {
        adsPage = next;
        loadAdminAds();
      });
      body.querySelectorAll("[data-moderate-ad]").forEach((button) => {
        button.addEventListener("click", () => openAdModeration(Number(button.dataset.moderateAd)));
      });
    } catch (error) {
      body.innerHTML = `<tr><td colspan="5" class="text-danger p-4">${KC.escapeHtml(error.message)}</td></tr>`;
    }
  }

  function openAdModeration(id) {
    const item = adItems.find((ad) => ad.id === id);
    if (!item) return;
    const form = document.getElementById("adModerationForm");
    KC.clearErrors(form);
    form.elements.ad_id.value = String(item.id);
    form.elements.status.value = item.status;
    form.elements.note.value = item.admin_note || "";
    document.getElementById("adModerationContext").textContent =
      `${item.title} by ${item.provider_name}. Campaign ${item.start_date} to ${item.end_date}.`;
    bootstrap.Modal.getOrCreateInstance(document.getElementById("adModerationModal")).show();
  }

  async function saveAdModeration(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const id = form.elements.ad_id.value;
    const submit = form.querySelector("[type='submit']");
    KC.clearErrors(form);
    KC.setBusy(submit, true, "Saving…");
    try {
      await KC.patch(`/admin/advertisements/${id}`, {
        status: form.elements.status.value,
        note: form.elements.note.value.trim() || null,
      });
      bootstrap.Modal.getOrCreateInstance(document.getElementById("adModerationModal")).hide();
      KC.toast("Advertisement updated");
      loadAdminAds();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  let activityPage = 1;
  async function loadActivity() {
    const body = document.getElementById("adminActivityBody");
    const alert = document.getElementById("adminActivityAlert");
    if (!body) return;
    const action = document.getElementById("activityActionFilter").value.trim();
    replaceQuery({ action, page: activityPage > 1 ? activityPage : "" });
    body.innerHTML = '<tr><td colspan="6" class="text-muted p-4">Loading activity…</td></tr>';
    try {
      const query = new URLSearchParams({ page: String(activityPage), page_size: "20" });
      if (action) query.set("action", action);
      const data = await KC.get(`/admin/audit-logs?${query.toString()}`);
      if (!data.items.length) {
        body.innerHTML = '<tr><td colspan="6" class="text-muted p-4">No activity matches these filters.</td></tr>';
      } else {
        body.innerHTML = data.items
          .map((item) => {
            const details = item.details || "";
            const shortDetails = details.length > 120 ? `${details.slice(0, 117)}…` : details;
            return `<tr>
              <td class="small text-muted text-nowrap">${KC.formatDateTime(item.created_at)}</td>
              <td class="small">
                <div class="fw-semibold">${KC.escapeHtml(item.actor_name || "System")}</div>
                <div class="text-muted">${KC.escapeHtml(item.actor_email || "")}</div>
              </td>
              <td class="small">
                <div>${KC.escapeHtml(actionLabel(item.action))}</div>
                <code class="small text-muted">${KC.escapeHtml(item.action)}</code>
              </td>
              <td class="small">${KC.escapeHtml(item.entity_type)}${item.entity_id ? ` #${KC.escapeHtml(item.entity_id)}` : ""}</td>
              <td class="small text-muted">${KC.escapeHtml(item.ip_address || "—")}</td>
              <td class="small text-muted">${KC.escapeHtml(shortDetails)}</td>
            </tr>`;
          })
          .join("");
      }
      const count = document.getElementById("adminActivityCount");
      if (count) count.textContent = `${data.total} event${data.total === 1 ? "" : "s"} found`;
      KC.pagination(document.getElementById("adminActivityPagination"), data, (next) => {
        activityPage = next;
        loadActivity();
      });
    } catch (error) {
      body.innerHTML = `<tr><td colspan="6" class="text-danger p-4">${KC.escapeHtml(error.message)}</td></tr>`;
      if (alert) alert.innerHTML = "";
    }
  }

  function bindFilters() {
    const userForm = document.getElementById("userFilterForm");
    if (userForm) {
      userForm.addEventListener("submit", (event) => {
        event.preventDefault();
        usersPage = 1;
        loadUsers();
      });
      document.getElementById("clearUserFilters").addEventListener("click", () => {
        userForm.reset();
        usersPage = 1;
        loadUsers();
      });
    }
    const verificationForm = document.getElementById("verificationFilterForm");
    if (verificationForm) {
      verificationForm.addEventListener("submit", (event) => {
        event.preventDefault();
        verificationPage = 1;
        loadVerification();
      });
      document.getElementById("clearVerificationFilters").addEventListener("click", () => {
        verificationForm.reset();
        verificationPage = 1;
        loadVerification();
      });
    }
    const reviewForm = document.getElementById("reviewFilterForm");
    if (reviewForm) {
      reviewForm.addEventListener("submit", (event) => {
        event.preventDefault();
        reviewsPage = 1;
        loadAdminReviews();
      });
      document.getElementById("clearReviewFilters").addEventListener("click", () => {
        reviewForm.reset();
        reviewsPage = 1;
        loadAdminReviews();
      });
    }
    const complaintForm = document.getElementById("complaintFilterForm");
    if (complaintForm) {
      complaintForm.addEventListener("submit", (event) => {
        event.preventDefault();
        complaintsPage = 1;
        loadAdminComplaints();
      });
      document.getElementById("clearComplaintFilters").addEventListener("click", () => {
        complaintForm.reset();
        complaintsPage = 1;
        loadAdminComplaints();
      });
    }
    const adForm = document.getElementById("adFilterForm");
    if (adForm) {
      adForm.addEventListener("submit", (event) => {
        event.preventDefault();
        adsPage = 1;
        loadAdminAds();
      });
      document.getElementById("clearAdFilters").addEventListener("click", () => {
        adForm.reset();
        adsPage = 1;
        loadAdminAds();
      });
    }
    const activityForm = document.getElementById("activityFilterForm");
    if (activityForm) {
      activityForm.addEventListener("submit", (event) => {
        event.preventDefault();
        activityPage = 1;
        loadActivity();
      });
      document.getElementById("clearActivityFilters").addEventListener("click", () => {
        activityForm.reset();
        activityPage = 1;
        loadActivity();
      });
    }
  }

  function applyInitialFilters() {
    const mapping = {
      "admin-users": [["userSearch", "q"], ["userRoleFilter", "role"]],
      "admin-verification": [["verificationSearch", "q"], ["verificationStatusFilter", "status"]],
      "admin-reviews": [["reviewSearch", "q"], ["reviewStatusFilter", "status"]],
      "admin-complaints": [["complaintStatusFilter", "status"]],
      "admin-advertisements": [["adStatusFilter", "status"]],
      "admin-activity": [["activityActionFilter", "action"]],
    };
    (mapping[page] || []).forEach(([id, param]) => {
      const field = document.getElementById(id);
      if (field) field.value = urlParam(param);
    });
  }

  function bindForms() {
    const map = [
      ["verificationForm", saveVerification],
      ["categoryForm", saveCategory],
      ["reviewModerationForm", saveReviewModeration],
      ["complaintUpdateForm", saveComplaint],
      ["adModerationForm", saveAdModeration],
    ];
    map.forEach(([id, handler]) => {
      const form = document.getElementById(id);
      if (form) form.addEventListener("submit", handler);
    });
    const addCategory = document.getElementById("addCategoryButton");
    if (addCategory) addCategory.addEventListener("click", () => openCategory(null));
  }

  document.addEventListener("DOMContentLoaded", async () => {
    me = await KC.requireAuth(["admin"]);
    if (!me) return;
    applyInitialFilters();
    bindFilters();
    bindForms();
    const copyResetLink = document.getElementById("resetLinkCopy");
    if (copyResetLink) {
      copyResetLink.addEventListener("click", async () => {
        const input = document.getElementById("resetLinkInput");
        if (!input.value) return;
        try {
          await navigator.clipboard.writeText(input.value);
          KC.toast("Reset link copied");
        } catch (_error) {
          input.select();
          document.execCommand("copy");
          KC.toast("Reset link copied");
        }
      });
    }
    if (page === "admin-dashboard") dashboard();
    if (page === "admin-users") {
      usersPage = Math.max(1, Number(urlParam("page")) || 1);
      loadUsers();
    }
    if (page === "admin-verification") {
      verificationPage = Math.max(1, Number(urlParam("page")) || 1);
      loadVerification();
    }
    if (page === "admin-categories") loadCategories();
    if (page === "admin-reviews") {
      reviewsPage = Math.max(1, Number(urlParam("page")) || 1);
      loadAdminReviews();
    }
    if (page === "admin-complaints") {
      complaintsPage = Math.max(1, Number(urlParam("page")) || 1);
      loadAdminComplaints();
    }
    if (page === "admin-advertisements") {
      adsPage = Math.max(1, Number(urlParam("page")) || 1);
      loadAdminAds();
    }
    if (page === "admin-activity") {
      activityPage = Math.max(1, Number(urlParam("page")) || 1);
      loadActivity();
    }
  });
})();
