(function () {
  "use strict";

  const container = document.getElementById("servicesContainer");
  const form = document.getElementById("serviceForm");
  const modalEl = document.getElementById("serviceModal");
  const categorySelect = document.getElementById("serviceCategory");
  const title = document.getElementById("serviceModalTitle");
  let services = [];

  function openCreate() {
    form.reset();
    KC.clearErrors(form);
    form.elements.service_id.value = "";
    form.elements.is_active.checked = true;
    title.textContent = "Add service";
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function openEdit(service) {
    form.reset();
    KC.clearErrors(form);
    form.elements.service_id.value = service.id;
    form.elements.title.value = service.title || "";
    form.elements.category_id.value = String(service.category_id || "");
    form.elements.description.value = service.description || "";
    form.elements.price_min.value = service.price_min == null ? "" : service.price_min;
    form.elements.price_max.value = service.price_max == null ? "" : service.price_max;
    form.elements.is_active.checked = Boolean(service.is_active);
    title.textContent = "Edit service";
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function render() {
    if (!services.length) {
      container.innerHTML = KC.emptyState(
        "bi-tools",
        "No services yet",
        "Add at least one service so customers understand what you offer.",
        '<button class="btn btn-brand" type="button" id="emptyAddService">Add your first service</button>'
      );
      const button = document.getElementById("emptyAddService");
      if (button) button.addEventListener("click", openCreate);
      return;
    }
    container.innerHTML = `<div class="table-responsive">
      <table class="table align-middle">
        <thead><tr><th>Service</th><th>Category</th><th>Price</th><th>Status</th><th class="text-end">Actions</th></tr></thead>
        <tbody>
          ${services
            .map(
              (service) => `<tr>
                <td>
                  <strong>${KC.escapeHtml(service.title)}</strong>
                  <div class="small text-muted text-truncate service-description-cell">${KC.escapeHtml(service.description || "")}</div>
                </td>
                <td><span class="chip">${KC.escapeHtml(service.category_name || "—")}</span></td>
                <td class="small">${KC.escapeHtml(KC.priceRange(service.price_min, service.price_max))}</td>
                <td><span class="badge ${service.is_active ? "badge-verified" : "badge-neutral"}">${service.is_active ? "Active" : "Hidden"}</span></td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-brand" type="button" data-edit="${Number(service.id)}">Edit</button>
                    <button class="btn btn-outline-secondary" type="button" data-toggle-active="${Number(service.id)}">${service.is_active ? "Hide" : "Show"}</button>
                    <button class="btn btn-outline-danger" type="button" data-delete="${Number(service.id)}">Delete</button>
                  </div>
                </td>
              </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
    container.querySelectorAll("[data-edit]").forEach((button) => {
      button.addEventListener("click", () => {
        const service = services.find((item) => item.id === Number(button.dataset.edit));
        if (service) openEdit(service);
      });
    });
    container.querySelectorAll("[data-toggle-active]").forEach((button) => {
      button.addEventListener("click", () => toggleActive(Number(button.dataset.toggleActive)));
    });
    container.querySelectorAll("[data-delete]").forEach((button) => {
      button.addEventListener("click", () => deleteService(Number(button.dataset.delete)));
    });
  }

  async function load() {
    try {
      services = await KC.get("/provider-services/me");
      render();
      const alert = document.getElementById("serviceAlert");
      if (!services.length && alert) {
        alert.innerHTML = '<div class="alert alert-info">Your public profile will show no services until you add one.</div>';
      }
    } catch (error) {
      if (error.status === 404) {
        container.innerHTML = `<div class="p-4">${KC.emptyState(
          "bi-person-vcard",
          "Create your business profile first",
          "Add your business details before listing services.",
          '<a class="btn btn-brand" href="/profile/edit">Create profile</a>'
        )}</div>`;
      } else {
        container.innerHTML = `<div class="alert alert-danger m-3">${KC.escapeHtml(error.message)}</div>`;
      }
    }
  }

  function payload() {
    return {
      category_id: Number(form.elements.category_id.value),
      title: form.elements.title.value.trim(),
      description: form.elements.description.value.trim() || null,
      price_min: form.elements.price_min.value === "" ? null : Number(form.elements.price_min.value),
      price_max: form.elements.price_max.value === "" ? null : Number(form.elements.price_max.value),
      is_active: form.elements.is_active.checked,
    };
  }

  async function save(event) {
    event.preventDefault();
    KC.clearErrors(form);
    const id = form.elements.service_id.value;
    const submit = form.querySelector("[type='submit']");
    KC.setBusy(submit, true, "Saving…");
    try {
      if (id) await KC.patch(`/provider-services/${id}`, payload());
      else await KC.post("/provider-services", payload());
      bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      KC.toast(id ? "Service updated" : "Service added");
      await load();
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function toggleActive(id) {
    const service = services.find((item) => item.id === id);
    if (!service) return;
    try {
      await KC.patch(`/provider-services/${id}`, { is_active: !service.is_active });
      KC.toast(service.is_active ? "Service hidden from your public profile" : "Service is now visible");
      await load();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  async function deleteService(id) {
    const service = services.find((item) => item.id === id);
    if (!service) return;
    const confirmed = await KC.confirm(`Delete “${service.title}”? This cannot be undone.`, "Delete service");
    if (!confirmed) return;
    try {
      await KC.del(`/provider-services/${id}`);
      KC.toast("Service deleted");
      await load();
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const me = await KC.requireAuth(["provider"]);
    if (!me) return;
    document.getElementById("addServiceButton").addEventListener("click", openCreate);
    form.addEventListener("submit", save);
    try {
      const categories = await KC.get("/categories");
      categorySelect.innerHTML =
        '<option value="">Choose a category</option>' +
        categories
          .map((category) => `<option value="${Number(category.id)}">${KC.escapeHtml(category.name)}</option>`)
          .join("");
    } catch (error) {
      KC.toast(error.message, "error");
    }
    await load();
  });
})();
