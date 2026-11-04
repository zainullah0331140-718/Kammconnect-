(function () {
  "use strict";

  let me = null;
  let hasProfile = false;

  function fillAccount(user) {
    const form = document.getElementById("accountForm");
    form.elements.full_name.value = user.full_name || "";
    form.elements.phone.value = user.phone || "";
    document.getElementById("accountEmail").value = user.email || "";
    document.getElementById("accountRole").value = user.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : "";
    const preview = document.getElementById("accountImagePreview");
    if (preview) preview.src = KC.avatarUrl(user);
  }

  function updateNavAvatar(user) {
    document.querySelectorAll("[data-user-avatar]").forEach((avatar) => {
      avatar.innerHTML = `<img src="${KC.escapeHtml(KC.avatarUrl(user))}" alt="">`;
    });
  }

  function fillProvider(profile) {
    const form = document.getElementById("providerProfileForm");
    form.elements.business_name.value = profile.business_name || "";
    form.elements.experience_years.value = profile.experience_years || 0;
    form.elements.city.value = profile.city || "";
    form.elements.area.value = profile.area || "";
    form.elements.address.value = profile.address || "";
    form.elements.contact_phone.value = profile.contact_phone || "";
    form.elements.whatsapp_number.value = profile.whatsapp_number || "";
    form.elements.description.value = profile.description || "";
    document.getElementById("profileVerification").innerHTML = KC.verificationBadge(profile.verification_status);
    const preview = document.getElementById("profileImagePreview");
    preview.src = KC.avatarUrl(profile);
    renderWorkImages(profile.work_images || []);
  }

  function renderWorkImages(images) {
    const grid = document.getElementById("workImagesGrid");
    const count = document.getElementById("workImagesCount");
    const empty = document.getElementById("workImagesEmpty");
    if (!grid) return;
    const sorted = [...images].sort((a, b) => (a.position - b.position) || (a.id - b.id));
    if (count) count.textContent = `${sorted.length} / 5`;
    if (empty) empty.classList.toggle("d-none", sorted.length > 0);
    grid.innerHTML = sorted
      .map(
        (image) => `<div class="work-photo">
          <a href="${KC.escapeHtml(image.image_path)}" target="_blank" rel="noopener noreferrer">
            <img src="${KC.escapeHtml(image.image_path)}" alt="Work photo" loading="lazy">
          </a>
          <button class="btn btn-sm btn-danger work-photo-remove" type="button" data-delete-work-image="${Number(image.id)}" aria-label="Remove work photo">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>`
      )
      .join("");
    grid.querySelectorAll("[data-delete-work-image]").forEach((button) => {
      button.addEventListener("click", () => deleteWorkImage(Number(button.dataset.deleteWorkImage)));
    });
  }

  async function uploadWorkImages(event) {
    event.preventDefault();
    const form = event.currentTarget;
    KC.clearErrors(form);
    const input = document.getElementById("workImagesInput");
    const submit = form.querySelector("[type='submit']");
    if (!input.files.length) {
      KC.toast("Choose at least one photo first", "warning");
      return;
    }
    const data = new FormData();
    [...input.files].forEach((file) => data.append("files", file));
    KC.setBusy(submit, true, "Uploading…");
    try {
      const profile = await KC.upload("/providers/me/work-images", data);
      fillProvider(profile);
      form.reset();
      KC.toast("Work photos updated");
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function deleteWorkImage(imageId) {
    const confirmed = await KC.confirm("Remove this work photo?", "Remove photo");
    if (!confirmed) return;
    try {
      const profile = await KC.del(`/providers/me/work-images/${imageId}`);
      fillProvider(profile);
      KC.toast("Work photo removed");
    } catch (error) {
      KC.toast(error.message, "error");
    }
  }

  async function saveAccount(event) {
    event.preventDefault();
    const form = event.currentTarget;
    KC.clearErrors(form);
    const submit = form.querySelector("[type='submit']");
    KC.setBusy(submit, true, "Saving…");
    try {
      await KC.patch("/users/me", {
        full_name: form.elements.full_name.value.trim(),
        phone: form.elements.phone.value.trim() || null,
      });
      me = await KC.me(true);
      fillAccount(me);
      KC.toast("Account details updated");
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function savePassword(event) {
    event.preventDefault();
    const form = event.currentTarget;
    KC.clearErrors(form);
    const current = form.elements.current_password;
    const next = form.elements.new_password;
    const confirm = form.elements.new_password_confirm;
    if (next.value !== confirm.value) {
      confirm.classList.add("is-invalid");
      const feedback = confirm.parentElement.querySelector(".invalid-feedback.js-error");
      if (feedback) {
        feedback.textContent = "Passwords do not match";
        feedback.classList.remove("d-none");
      }
      return;
    }
    const submit = form.querySelector("[type='submit']");
    KC.setBusy(submit, true, "Updating…");
    try {
      const data = await KC.post("/auth/change-password", {
        current_password: current.value,
        new_password: next.value,
      });
      me = data.user;
      form.reset();
      KC.toast("Password updated");
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function deleteAccount(event) {
    event.preventDefault();
    const form = event.currentTarget;
    KC.clearErrors(form);
    const confirmInput = document.getElementById("deleteAccountConfirm");
    if (!confirmInput.checked) {
      KC.toast("Please confirm that you understand this cannot be undone", "warning");
      return;
    }
    const confirmed = await KC.confirm(
      "This permanently deletes your account and all related data. Continue?",
      "Delete account?"
    );
    if (!confirmed) return;
    const submit = form.querySelector("[type='submit']");
    KC.setBusy(submit, true, "Deleting…");
    try {
      await KC.del("/users/me", { password: form.elements.password.value });
      window.location.href = "/";
    } catch (error) {
      KC.setBusy(submit, false);
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    }
  }

  async function saveProvider(event) {
    event.preventDefault();
    const form = event.currentTarget;
    KC.clearErrors(form);
    const submit = form.querySelector("[type='submit']");
    const payload = {
      business_name: form.elements.business_name.value.trim(),
      experience_years: Number(form.elements.experience_years.value) || 0,
      city: form.elements.city.value.trim(),
      area: form.elements.area.value.trim() || null,
      address: form.elements.address.value.trim() || null,
      contact_phone: form.elements.contact_phone.value.trim() || null,
      whatsapp_number: form.elements.whatsapp_number.value.trim() || null,
      description: form.elements.description.value.trim() || null,
    };
    KC.setBusy(submit, true, "Saving…");
    try {
      if (hasProfile) {
        await KC.patch("/providers/me", payload);
      } else {
        await KC.post("/providers/me", payload);
        hasProfile = true;
        document.getElementById("profileImageForm").classList.remove("d-none");
        document.getElementById("workImagesForm").classList.remove("d-none");
      }
      KC.toast("Business profile updated");
      const profile = await KC.get("/providers/me");
      fillProvider(profile);
    } catch (error) {
      KC.showError(form.querySelector(".form-error"), error);
      if (error.errors) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function uploadImage(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = document.getElementById("profileImage");
    const submit = form.querySelector("[type='submit']");
    if (!input.files.length) {
      KC.toast("Choose an image first", "warning");
      return;
    }
    const data = new FormData();
    data.append("file", input.files[0]);
    KC.setBusy(submit, true, "Uploading…");
    try {
      const profile = await KC.upload("/providers/me/image", data);
      fillProvider(profile);
      form.reset();
      KC.toast("Profile image updated");
    } catch (error) {
      KC.toast(error.message, "error");
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function uploadAccountImage(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = document.getElementById("accountImage");
    const submit = form.querySelector("[type='submit']");
    if (!input.files.length) {
      KC.toast("Choose an image first", "warning");
      return;
    }
    const data = new FormData();
    data.append("file", input.files[0]);
    KC.setBusy(submit, true, "Uploading…");
    try {
      me = await KC.upload("/users/me/image", data);
      fillAccount(me);
      updateNavAvatar(me);
      form.reset();
      KC.toast("Profile photo updated");
    } catch (error) {
      KC.toast(error.message, "error");
    } finally {
      KC.setBusy(submit, false);
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    me = await KC.requireAuth(["customer", "provider", "admin"]);
    if (!me) return;
    fillAccount(me);
    if (new URLSearchParams(window.location.search).get("media") === "error") {
      KC.toast("Some photos could not be uploaded. Please try again below.", "warning");
    }

    const accountForm = document.getElementById("accountForm");
    accountForm.addEventListener("submit", saveAccount);
    const accountImageForm = document.getElementById("accountImageForm");
    if (accountImageForm) accountImageForm.addEventListener("submit", uploadAccountImage);
    const passwordForm = document.getElementById("passwordForm");
    if (passwordForm) passwordForm.addEventListener("submit", savePassword);
    const deleteForm = document.getElementById("deleteAccountForm");
    if (deleteForm) deleteForm.addEventListener("submit", deleteAccount);

    if (me.role !== "provider") return;
    const section = document.getElementById("providerProfileSection");
    section.classList.remove("d-none");
    const imageForm = document.getElementById("profileImageForm");
    imageForm.classList.add("d-none");
    const workImagesForm = document.getElementById("workImagesForm");
    workImagesForm.classList.add("d-none");
    const profileForm = document.getElementById("providerProfileForm");
    profileForm.addEventListener("submit", saveProvider);
    imageForm.addEventListener("submit", uploadImage);
    workImagesForm.addEventListener("submit", uploadWorkImages);
    try {
      const profile = await KC.get("/providers/me");
      hasProfile = true;
      imageForm.classList.remove("d-none");
      workImagesForm.classList.remove("d-none");
      fillProvider(profile);
    } catch (error) {
      if (error.status === 404) {
        document.getElementById("profileVerification").innerHTML = '<span class="badge badge-pending">Profile not created yet</span>';
        KC.toast("Add your business details to create your public profile", "warning");
      } else {
        KC.toast(error.message, "error");
      }
    }
  });
})();
