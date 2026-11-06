(function () {
  "use strict";

  const list = document.getElementById("complaintsList");
  const form = document.getElementById("complaintForm");
  const modalEl = document.getElementById("complaintModal");
  let me = null;

  function badge(status) {
    const map = {
      open: "badge-neutral",
      in_review: "badge-pending",
      resolved: "badge-verified",
      rejected: "badge-rejected",
    };
    return `<span class="badge ${map[status] || "badge-neutral"}">${KC.escapeHtml(String(status).replace("_", " "))}</span>`;
  }

  function complaintCard(complaint) {
    return `<article class="card-soft p-4 mb-3">
      <div class="d-flex flex-wrap justify-content-between gap-2">
        <div>
          <h2 class="h6 mb-1">${KC.escapeHtml(complaint.subject)}</h2>
          <div class="small text-muted">
            ${KC.escapeHtml(complaint.provider_name || "General complaint")} · ${KC.formatDateTime(complaint.created_at)}
          </div>
        </div>
        ${badge(complaint.status)}
      </div>
      <p class="small text-muted mt-3 mb-2">${KC.escapeHtml(complaint.message)}</p>
      ${complaint.admin_response ? `<div class="p-3 bg-brand-soft rounded small"><strong><i class="bi bi-person-badge me-1"></i>Staff response:</strong> ${KC.escapeHtml(complaint.admin_response)}</div>` : ""}
      <div class="d-flex justify-content-end mt-2">
        <button class="btn btn-sm btn-outline-danger" type="button" data-delete-complaint="${Number(complaint.id)}">
          <i class="bi bi-trash me-1"></i>Delete
        </button>
      </div>
    </article>`;
  }

  async function load() {
    try {
      const complaints = await KC.get("/complaints/me");
      if (!complaints.length) {
        list.innerHTML = KC.emptyState(
          "bi-flag",
          "No complaints filed",
          "If a provider or marketplace interaction goes wrong, you can report it here.",
          '<button class="btn btn-brand" type="button" data-bs-toggle="modal" data-bs-target="#complaintModal">File a complaint</button>'
        );
        return;
      }
      list.innerHTML = complaints.map(complaintCard).join("");
      list.querySelectorAll("[data-delete-complaint]").forEach((button) => {
        button.addEventListener("click", () =>
          removeComplaint(Number(button.dataset.deleteComplaint))
        );
      });
    } catch (error) {
      list.innerHTML = `<div class="alert alert-danger">${KC.escapeHtml(error.message)}</div>`;
    }
  }

  async function removeComplaint(id) {
    const confirmed = await KC.confirm(
      "Delete this complaint? This cannot be undone.",
      "Delete complaint"
    );
    if (!confirmed) return;
    try {
      await KC.del(`/complaints/${id}`);
      KC.toast("Complaint deleted");
      await load();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  async function loadProviders() {
    const select = document.getElementById("complaintProvider");
    if (!select) return;
    try {
      const data = await KC.get("/providers?page_size=50&sort=name");
      select.innerHTML =
        '<option value="">General complaint</option>' +
        data.items
          .filter((provider) => !me || provider.user_id !== me.id)
          .map((provider) => `<option value="${Number(provider.id)}">${KC.escapeHtml(provider.business_name)} — ${KC.escapeHtml([provider.area, provider.city].filter(Boolean).join(", "))}</option>`)
          .join("");
      const params = new URLSearchParams(window.location.search);
      const preselected = params.get("provider");
      if (preselected && select.querySelector(`option[value="${Number(preselected)}"]`)) {
        select.value = String(Number(preselected));
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
      }
    } catch (_error) {
      // The general complaint option remains available.
    }
  }

  async function submit(event) {
    event.preventDefault();
    KC.clearErrors(form);
    const submitButton = form.querySelector("[type='submit']");
    const providerId = form.elements.provider_id.value;
    KC.setBusy(submitButton, true, "Submitting…");
    try {
      await KC.post("/complaints", {
        provider_id: providerId ? Number(providerId) : null,
        subject: form.elements.subject.value.trim(),
        message: form.elements.message.value.trim(),
      });
      form.reset();
      bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      KC.toast("Complaint submitted. The moderation team will review it.");
      await load();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submitButton, false);
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    me = await KC.requireAuth(["customer", "provider", "admin"]);
    if (!me) return;
    form.addEventListener("submit", submit);
    await load();
    loadProviders();
  });
})();
