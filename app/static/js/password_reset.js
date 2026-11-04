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

  async function handleRequest(form) {
    const submit = form.querySelector("[type='submit']");
    const email = form.elements.email.value.trim();
    KC.clearErrors(form);
    document.getElementById("forgotPasswordSuccess").classList.add("d-none");
    document.getElementById("forgotPasswordDevLink").classList.add("d-none");
    if (!email) {
      markInvalid(form.elements.email, "Enter the email address for your account");
      return;
    }
    KC.setBusy(submit, true, "Sending…");
    try {
      const data = await KC.post("/auth/password-reset/request", { email });
      const success = document.getElementById("forgotPasswordSuccess");
      success.textContent = data.message;
      success.classList.remove("d-none");
      if (data.reset_url) {
        const devLink = document.getElementById("forgotPasswordDevLink");
        devLink.innerHTML =
          'Email delivery is not configured in this environment. ' +
          `<a href="${KC.escapeHtml(data.reset_url)}">Open the reset link</a> ` +
          "(it also appears in the server log).";
        devLink.classList.remove("d-none");
      }
      form.reset();
    } catch (error) {
      showFormError(form, error.message);
      if (error.errors && error.errors.length) KC.applyFieldErrors(form, error.errors);
    } finally {
      KC.setBusy(submit, false);
    }
  }

  async function handleConfirm(form, token) {
    const submit = form.querySelector("[type='submit']");
    const password = form.elements.password;
    const confirm = form.elements.password_confirm;
    KC.clearErrors(form);
    if (password.value !== confirm.value) {
      markInvalid(confirm, "Passwords do not match");
      return;
    }
    KC.setBusy(submit, true, "Saving…");
    try {
      await KC.post("/auth/password-reset/confirm", {
        token,
        new_password: password.value,
      });
      KC.toast("Password reset. Please log in with your new password.");
      window.setTimeout(() => {
        window.location.href = "/login";
      }, 500);
    } catch (error) {
      showFormError(form, error.message);
      if (error.errors && error.errors.length) KC.applyFieldErrors(form, error.errors);
      KC.setBusy(submit, false);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const requestForm = document.getElementById("forgotPasswordForm");
    if (requestForm) {
      requestForm.addEventListener("submit", (event) => {
        event.preventDefault();
        handleRequest(requestForm);
      });
    }

    const resetForm = document.getElementById("resetPasswordForm");
    if (resetForm) {
      const token = new URLSearchParams(window.location.search).get("token") || "";
      if (!token) {
        document.getElementById("resetTokenAlert").classList.remove("d-none");
        resetForm.querySelector("[type='submit']").disabled = true;
      }
      resetForm.addEventListener("submit", (event) => {
        event.preventDefault();
        if (token) handleConfirm(resetForm, token);
      });
    }
  });
})();
