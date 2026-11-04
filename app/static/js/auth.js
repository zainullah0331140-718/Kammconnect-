(function () {
  "use strict";

  function showFormError(form, message) {
    const alert = form.querySelector(".form-error");
    if (alert) {
      alert.textContent = message;
      alert.classList.remove("d-none");
    } else {
      KC.toast(message, "error");
    }
  }

  function markInvalid(field, message) {
    if (!field) return;
    field.classList.add("is-invalid");
    const feedback = field.parentElement.querySelector(".invalid-feedback.js-error");
    if (feedback) {
      feedback.textContent = message;
      feedback.classList.remove("d-none");
    }
  }

  function validatePasswordPair(form) {
    const password = form.elements.password;
    const confirm = form.elements.password_confirm;
    if (!password || !confirm) return true;
    if (password.value !== confirm.value) {
      markInvalid(confirm, "Passwords do not match");
      return false;
    }
    return true;
  }

  function validateTerms(form) {
    const terms = form.querySelector("[type='checkbox'][required]");
    if (terms && !terms.checked) {
      KC.toast("Please accept the terms to continue", "warning");
      terms.focus();
      return false;
    }
    return true;
  }

  async function handleLogin(form) {
    const submit = form.querySelector("[type='submit']");
    KC.clearErrors(form);
    KC.setBusy(submit, true, "Logging in…");
    try {
      const data = await KC.post("/auth/login", {
        email: form.elements.email.value.trim(),
        password: form.elements.password.value,
      });
      KC.toast(`Welcome back, ${data.user.full_name}`);
      window.setTimeout(() => KC.redirectAfterLogin(data.user), 250);
    } catch (error) {
      showFormError(form, error.message);
      if (error.errors && error.errors.length) KC.applyFieldErrors(form, error.errors);
      KC.setBusy(submit, false);
    }
  }

  function customerPayload(form) {
    return {
      full_name: form.elements.full_name.value.trim(),
      email: form.elements.email.value.trim(),
      phone: form.elements.phone.value.trim() || null,
      password: form.elements.password.value,
    };
  }

  function providerPayload(form) {
    return {
      full_name: form.elements.full_name.value.trim(),
      email: form.elements.email.value.trim(),
      phone: form.elements.phone.value.trim() || null,
      password: form.elements.password.value,
      business_name: form.elements.business_name.value.trim(),
      description: form.elements.description.value.trim() || null,
      experience_years: Number(form.elements.experience_years.value) || 0,
      city: form.elements.city.value.trim(),
      area: form.elements.area.value.trim() || null,
      address: form.elements.address.value.trim() || null,
      contact_phone: form.elements.contact_phone.value.trim() || null,
      whatsapp_number: form.elements.whatsapp_number.value.trim() || null,
    };
  }

  const MAX_PROVIDER_WORK_PHOTOS = 5;

  function releasePreviewUrls(container) {
    container.querySelectorAll("img[data-preview-url]").forEach((image) => {
      URL.revokeObjectURL(image.dataset.previewUrl);
    });
  }

  function renderProviderWorkPreview(files) {
    const preview = document.getElementById("providerWorkPreview");
    const count = document.getElementById("providerWorkImagesCount");
    if (!preview) return;
    releasePreviewUrls(preview);
    preview.innerHTML = "";
    const selected = [...files].slice(0, MAX_PROVIDER_WORK_PHOTOS);
    selected.forEach((file, index) => {
      const wrapper = document.createElement("div");
      wrapper.className = "work-photo";
      const image = document.createElement("img");
      const url = URL.createObjectURL(file);
      image.src = url;
      image.alt = `Work photo ${index + 1}`;
      image.loading = "lazy";
      image.dataset.previewUrl = url;
      wrapper.appendChild(image);
      preview.appendChild(wrapper);
    });
    if (count) count.textContent = `${selected.length} / ${MAX_PROVIDER_WORK_PHOTOS}`;
  }

  function setupProviderMedia(form) {
    const profileInput = form.elements.profile_image;
    const profilePreview = document.getElementById("providerProfilePreview");
    if (profileInput && profilePreview) {
      profileInput.addEventListener("change", () => {
        if (profilePreview.dataset.previewUrl) {
          URL.revokeObjectURL(profilePreview.dataset.previewUrl);
        }
        const file = profileInput.files[0];
        if (!file) {
          delete profilePreview.dataset.previewUrl;
          profilePreview.src = "/static/images/avatar.svg";
          return;
        }
        const url = URL.createObjectURL(file);
        profilePreview.dataset.previewUrl = url;
        profilePreview.src = url;
      });
    }
    const workInput = form.elements.work_images;
    if (workInput) {
      workInput.addEventListener("change", () => {
        const files = [...workInput.files];
        if (files.length > MAX_PROVIDER_WORK_PHOTOS) {
          KC.toast(
            `You can add up to ${MAX_PROVIDER_WORK_PHOTOS} work photos. Only the first ${MAX_PROVIDER_WORK_PHOTOS} will be uploaded.`,
            "warning"
          );
        }
        renderProviderWorkPreview(files);
      });
    }
  }

  async function uploadProviderMedia(form) {
    const warnings = [];
    const profileInput = form.elements.profile_image;
    if (profileInput && profileInput.files.length) {
      const data = new FormData();
      data.append("file", profileInput.files[0]);
      try {
        await KC.upload("/providers/me/image", data);
      } catch (error) {
        warnings.push(error.message);
      }
    }
    const workInput = form.elements.work_images;
    const workFiles = workInput
      ? [...workInput.files].slice(0, MAX_PROVIDER_WORK_PHOTOS)
      : [];
    if (workFiles.length) {
      const data = new FormData();
      workFiles.forEach((file) => data.append("files", file));
      try {
        await KC.upload("/providers/me/work-images", data);
      } catch (error) {
        warnings.push(error.message);
      }
    }
    return warnings;
  }

  async function handleCustomerRegister(form) {
    if (!validatePasswordPair(form) || !validateTerms(form)) return;
    const submit = form.querySelector("[type='submit']");
    KC.clearErrors(form);
    KC.setBusy(submit, true, "Creating account…");
    try {
      const data = await KC.post("/auth/register/customer", customerPayload(form));
      KC.toast("Your customer account is ready");
      window.setTimeout(() => {
        window.location.href = KC.dashboardPath(data.user.role);
      }, 250);
    } catch (error) {
      showFormError(form, error.message);
      if (error.errors && error.errors.length) KC.applyFieldErrors(form, error.errors);
      KC.setBusy(submit, false);
    }
  }

  async function handleProviderRegister(form) {
    if (!validatePasswordPair(form) || !validateTerms(form)) return;
    const submit = form.querySelector("[type='submit']");
    KC.clearErrors(form);
    KC.setBusy(submit, true, "Creating provider account…");
    try {
      await KC.post("/auth/register/provider", providerPayload(form));
      const mediaWarnings = await uploadProviderMedia(form);
      if (mediaWarnings.length) {
        KC.toast(
          `Provider account created, but some photos could not be uploaded: ${mediaWarnings.join(" ")}`,
          "warning"
        );
      } else {
        KC.toast("Provider account created. Your profile is pending verification.");
      }
      window.setTimeout(() => {
        window.location.href = mediaWarnings.length
          ? "/profile/edit?media=error"
          : "/dashboard/provider";
      }, 500);
    } catch (error) {
      showFormError(form, error.message);
      if (error.errors && error.errors.length) KC.applyFieldErrors(form, error.errors);
      KC.setBusy(submit, false);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
      loginForm.addEventListener("submit", (event) => {
        event.preventDefault();
        handleLogin(loginForm);
      });
    }
    const customerForm = document.getElementById("customerRegisterForm");
    if (customerForm) {
      customerForm.addEventListener("submit", (event) => {
        event.preventDefault();
        handleCustomerRegister(customerForm);
      });
    }
    const providerForm = document.getElementById("providerRegisterForm");
    if (providerForm) {
      setupProviderMedia(providerForm);
      providerForm.addEventListener("submit", (event) => {
        event.preventDefault();
        handleProviderRegister(providerForm);
      });
    }
  });
})();
