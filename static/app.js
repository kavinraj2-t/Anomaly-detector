const state = {
  currentUser: null,
  deviceId: null,
  deviceLabel: null,
  pendingOtpTransactionId: null,
  transactions: [],
};

const authView = document.getElementById("auth-view");
const dashboardView = document.getElementById("dashboard-view");
const loginTab = document.getElementById("login-tab");
const registerTab = document.getElementById("register-tab");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const otpForm = document.getElementById("otp-form");
const passwordResetForm = document.getElementById("password-reset-form");
const logoutBtn = document.getElementById("logout-btn");
const addMoneyBtn = document.getElementById("add-money-btn");
const paymentForm = document.getElementById("payment-form");
const toast = document.getElementById("toast");
const bankHandleInput = document.getElementById("bank-handle-input");
const backToRegisterBtn = document.getElementById("back-to-register-btn");
const openPasswordResetBtn = document.getElementById("open-password-reset-btn");
const sendPasswordResetOtpBtn = document.getElementById("send-password-reset-otp-btn");
const backToLoginBtn = document.getElementById("back-to-login-btn");
const deviceIdDisplay = document.getElementById("device-id-display");
const locationStatus = document.getElementById("location-status");
const openDeleteModalBtn = document.getElementById("open-delete-modal-btn");
const deleteModal = document.getElementById("delete-modal");
const cancelDeleteBtn = document.getElementById("cancel-delete-btn");
const deleteAccountForm = document.getElementById("delete-account-form");
const openUpiPinResetBtn = document.getElementById("open-upi-pin-reset-btn");
const upiPinResetModal = document.getElementById("upi-pin-reset-modal");
const upiPinResetForm = document.getElementById("upi-pin-reset-form");
const sendPinResetOtpBtn = document.getElementById("send-pin-reset-otp-btn");
const cancelUpiPinResetBtn = document.getElementById("cancel-upi-pin-reset-btn");
const transactionOtpBox = document.getElementById("transaction-otp-box");
const verifyTransactionOtpBtn = document.getElementById("verify-transaction-otp-btn");
const transactionDetailModal = document.getElementById("transaction-detail-modal");
const transactionDetailBody = document.getElementById("transaction-detail-body");
const closeTransactionDetailBtn = document.getElementById("close-transaction-detail-btn");

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add("hidden"), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong");
  }
  return data;
}

function currency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function ensureDeviceIdentity() {
  let existingId = localStorage.getItem("upiFraudDeviceId");
  if (!existingId) {
    existingId = `device-${crypto.randomUUID()}`;
    localStorage.setItem("upiFraudDeviceId", existingId);
  }
  state.deviceId = existingId;
  state.deviceLabel = `${navigator.platform || "Browser"} | ${navigator.userAgent.slice(0, 60)}`;
  if (deviceIdDisplay) {
    deviceIdDisplay.textContent = existingId;
  }
}

function requestCurrentLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation is not supported in this browser"));
      return;
    }

    locationStatus.textContent = "Requesting location permission...";
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        locationStatus.textContent = `Location captured: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
        resolve({ latitude, longitude });
      },
      () => {
        reject(new Error("Location permission is required to process a payment"));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  });
}

function setAuthMode(mode) {
  const loginActive = mode === "login";
  loginTab.classList.toggle("active", loginActive);
  registerTab.classList.toggle("active", !loginActive);
  loginForm.classList.toggle("hidden", !loginActive);
  registerForm.classList.toggle("hidden", loginActive);
  otpForm.classList.add("hidden");
  passwordResetForm.classList.add("hidden");
}

function showDashboard(show) {
  authView.classList.toggle("hidden", show);
  dashboardView.classList.toggle("hidden", !show);
}

function openTransactionDetail(transactionId) {
  const transaction = state.transactions.find((tx) => tx._id === transactionId);
  if (!transaction) {
    showToast("Transaction details not found");
    return;
  }

  const direction = transaction.sender_id === state.currentUser.user_id ? "Sent" : "Received";
  const reasons = (transaction.reasons || []).map((reason) => `<li>${reason}</li>`).join("");
  const latitude = transaction.location?.latitude;
  const longitude = transaction.location?.longitude;
  transactionDetailBody.innerHTML = `
    <p><strong>Direction:</strong> ${direction}</p>
    <p><strong>Amount:</strong> ${currency(transaction.amount)}</p>
    <p><strong>Status:</strong> ${transaction.status.replace("_", " ").toUpperCase()}</p>
    <p><strong>Decision:</strong> ${transaction.decision.toUpperCase()}</p>
    <p><strong>Risk score:</strong> ${(transaction.risk_score * 100).toFixed(0)}%</p>
    <p><strong>Sender:</strong> ${transaction.sender_id}</p>
    <p><strong>Receiver:</strong> ${transaction.receiver_id}</p>
    <p><strong>Device ID:</strong> ${transaction.device_id}</p>
    <p><strong>Location:</strong> ${latitude?.toFixed(4)}, ${longitude?.toFixed(4)}</p>
    <p><strong>Created at:</strong> ${new Date(transaction.created_at).toLocaleString()}</p>
    <p><strong>Why this risk score:</strong></p>
    <ul class="detail-list">${reasons || "<li>Pattern looks normal</li>"}</ul>
  `;
  transactionDetailModal.classList.remove("hidden");
}

function renderTransactions(transactions, currentUserId) {
  const container = document.getElementById("transaction-list");
  container.innerHTML = "";
  state.transactions = transactions;

  if (!transactions.length) {
    container.innerHTML = "<p>No transactions yet.</p>";
    return;
  }

  transactions.forEach((tx) => {
    const direction = tx.sender_id === currentUserId ? "Paid" : "Received";
    const counterpart = tx.sender_id === currentUserId ? tx.receiver_id : tx.sender_id;
    const item = document.createElement("div");
    item.className = "transaction-item";
    item.innerHTML = `
      <div>
        <strong>${direction} ${currency(tx.amount)}</strong>
        <p>${counterpart}</p>
        <p class="muted">${new Date(tx.created_at).toLocaleString()}</p>
      </div>
      <div>
        <p>${tx.status.replace("_", " ").toUpperCase()}</p>
        <p class="muted">Risk ${(tx.risk_score * 100).toFixed(0)}%</p>
        <button type="button" class="ghost-btn tiny-btn view-transaction-btn" data-transaction-id="${tx._id}">View More</button>
      </div>
    `;
    container.appendChild(item);
  });

  container.querySelectorAll(".view-transaction-btn").forEach((button) => {
    button.addEventListener("click", () => openTransactionDetail(button.dataset.transactionId));
  });
}

function renderSpendingChart(transactions, currentUserId) {
  const chart = document.getElementById("spending-chart");
  chart.innerHTML = "";
  const outgoing = transactions.filter((tx) => tx.sender_id === currentUserId).slice().reverse();
  const values = outgoing.map((tx) => tx.amount);

  if (!values.length) {
    chart.innerHTML = "<p>No outgoing transactions yet.</p>";
    return;
  }

  const max = Math.max(...values, 1);
  values.forEach((value, index) => {
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${Math.max((value / max) * 140, 20)}px`;
    bar.title = currency(value);
    bar.innerHTML = `<span>T${index + 1}</span>`;
    chart.appendChild(bar);
  });
}

function renderBehavior(profile) {
  document.getElementById("avg-amount").textContent = currency(profile?.avg_amount || 0);
  document.getElementById("known-devices").textContent = (profile?.known_devices || []).length;
}

function renderResult(transaction) {
  const resultCard = document.getElementById("result-card");
  const decision = transaction.decision;
  const labels = {
    allow: ["SUCCESS", "status-success", "Success"],
    otp: ["OTP REQUIRED", "status-otp", "OTP Required"],
    block: ["BLOCKED", "status-block", "Blocked"],
  };
  const [statusText, pillClass, headline] = labels[decision] || labels.allow;
  const latitude = transaction.location?.latitude;
  const longitude = transaction.location?.longitude;
  resultCard.className = `result-card ${decision}`;
  resultCard.innerHTML = `
    <div class="status-pill ${pillClass}">${statusText}</div>
    <h3>${headline}</h3>
    <p><strong>Risk score:</strong> ${(transaction.risk_score * 100).toFixed(0)}%</p>
    <p><strong>Reasons:</strong> ${(transaction.reasons || []).join(", ")}</p>
    <p><strong>Amount:</strong> ${currency(transaction.amount)}</p>
    <p><strong>Device:</strong> ${transaction.device_id}</p>
    <p><strong>Location:</strong> ${latitude?.toFixed(4)}, ${longitude?.toFixed(4)}</p>
  `;
}

async function loadDashboard() {
  const [balanceData, behaviorData, historyData] = await Promise.all([
    api("/api/balance"),
    api("/api/behavior"),
    api("/api/transactions"),
  ]);

  state.currentUser = balanceData.user;
  document.getElementById("user-name").textContent = balanceData.user.name;
  document.getElementById("user-upi").textContent = balanceData.user.user_id;
  document.getElementById("balance-amount").textContent = currency(balanceData.balance);
  renderTransactions(historyData.transactions || [], balanceData.user.user_id);
  renderSpendingChart(historyData.transactions || [], balanceData.user.user_id);
  renderBehavior(behaviorData.profile);
  showDashboard(true);
}

async function bootstrapSession() {
  try {
    const me = await api("/api/auth/me");
    if (me.authenticated) {
      state.currentUser = me.user;
      await loadDashboard();
    }
  } catch (error) {
    showDashboard(false);
  }
}

loginTab.addEventListener("click", () => setAuthMode("login"));
registerTab.addEventListener("click", () => setAuthMode("register"));

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(loginForm);
  try {
    await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(formData.entries())),
    });
    showToast("Login successful");
    await loadDashboard();
  } catch (error) {
    showToast(error.message);
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(registerForm);
  try {
    const payload = Object.fromEntries(formData.entries());
    payload.device_id = state.deviceId;
    await api("/api/auth/request-registration-otp", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    document.getElementById("otp-email").value = payload.email;
    document.getElementById("registration-otp").value = "";
    registerForm.classList.add("hidden");
    otpForm.classList.remove("hidden");
    showToast("OTP sent to email");
  } catch (error) {
    showToast(error.message);
  }
});

otpForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/auth/verify-registration-otp", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("otp-email").value,
        otp: document.getElementById("registration-otp").value,
      }),
    });
    showToast("Registration complete");
    await loadDashboard();
  } catch (error) {
    showToast(error.message);
  }
});

backToRegisterBtn.addEventListener("click", () => {
  otpForm.classList.add("hidden");
  registerForm.classList.remove("hidden");
});

openPasswordResetBtn.addEventListener("click", () => {
  loginForm.classList.add("hidden");
  registerForm.classList.add("hidden");
  otpForm.classList.add("hidden");
  passwordResetForm.classList.remove("hidden");
});

backToLoginBtn.addEventListener("click", () => {
  passwordResetForm.classList.add("hidden");
  loginForm.classList.remove("hidden");
});

sendPasswordResetOtpBtn.addEventListener("click", async () => {
  try {
    await api("/api/auth/request-password-reset-otp", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("password-reset-email").value,
      }),
    });
    showToast("Reset OTP sent to email");
  } catch (error) {
    showToast(error.message);
  }
});

passwordResetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/auth/verify-password-reset-otp", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("password-reset-email").value,
        otp: document.getElementById("password-reset-otp").value,
        new_password: document.getElementById("new-password").value,
      }),
    });
    passwordResetForm.reset();
    passwordResetForm.classList.add("hidden");
    loginForm.classList.remove("hidden");
    showToast("Password reset successful");
  } catch (error) {
    showToast(error.message);
  }
});

logoutBtn.addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  state.currentUser = null;
  state.pendingOtpTransactionId = null;
  transactionOtpBox.classList.add("hidden");
  showDashboard(false);
  showToast("Logged out");
});

addMoneyBtn.addEventListener("click", async () => {
  const input = document.getElementById("add-money-input");
  try {
    await api("/api/add_money", {
      method: "POST",
      body: JSON.stringify({ amount: Number(input.value) }),
    });
    input.value = "";
    await loadDashboard();
    showToast("Money added");
  } catch (error) {
    showToast(error.message);
  }
});

paymentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const location = await requestCurrentLocation();
    const payload = {
      recipient: document.getElementById("recipient-input").value,
      amount: Number(document.getElementById("amount-input").value),
      device_id: state.deviceId,
      device_label: state.deviceLabel,
      upi_pin: document.getElementById("upi-pin-input").value,
      latitude: location.latitude,
      longitude: location.longitude,
    };

    const data = await api("/api/send_money", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderResult(data.transaction);
    document.getElementById("upi-pin-input").value = "";
    if (data.otp_required) {
      state.pendingOtpTransactionId = data.transaction_id;
      transactionOtpBox.classList.remove("hidden");
    } else {
      state.pendingOtpTransactionId = null;
      transactionOtpBox.classList.add("hidden");
    }
    await loadDashboard();

    if (data.transaction.decision === "otp") {
      showToast("Payment flagged for step-up verification. Enter the OTP to approve it.");
    } else if (data.transaction.decision === "block") {
      showToast("Transaction blocked");
    } else {
      showToast("Payment successful");
    }
  } catch (error) {
    locationStatus.textContent = error.message;
    showToast(error.message);
  }
});

verifyTransactionOtpBtn.addEventListener("click", async () => {
  if (!state.pendingOtpTransactionId) {
    showToast("No OTP verification is pending");
    return;
  }

  try {
    const data = await api("/api/confirm_transaction_otp", {
      method: "POST",
      body: JSON.stringify({
        transaction_id: state.pendingOtpTransactionId,
        otp: document.getElementById("transaction-otp-input").value,
      }),
    });
    state.pendingOtpTransactionId = null;
    document.getElementById("transaction-otp-input").value = "";
    transactionOtpBox.classList.add("hidden");
    renderResult(data.transaction);
    await loadDashboard();
    showToast("OTP verified and payment completed");
  } catch (error) {
    showToast(error.message);
  }
});

openUpiPinResetBtn.addEventListener("click", () => {
  document.getElementById("pin-reset-email").value = state.currentUser?.email || "";
  document.getElementById("pin-reset-otp").value = "";
  document.getElementById("new-upi-pin").value = "";
  upiPinResetModal.classList.remove("hidden");
});

cancelUpiPinResetBtn.addEventListener("click", () => {
  upiPinResetModal.classList.add("hidden");
  upiPinResetForm.reset();
  document.getElementById("pin-reset-email").value = state.currentUser?.email || "";
});

sendPinResetOtpBtn.addEventListener("click", async () => {
  try {
    await api("/api/auth/request-upi-pin-reset-otp", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("pin-reset-email").value,
      }),
    });
    showToast("UPI PIN reset OTP sent");
  } catch (error) {
    showToast(error.message);
  }
});

upiPinResetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/auth/verify-upi-pin-reset-otp", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("pin-reset-email").value,
        otp: document.getElementById("pin-reset-otp").value,
        new_upi_pin: document.getElementById("new-upi-pin").value,
      }),
    });
    upiPinResetModal.classList.add("hidden");
    upiPinResetForm.reset();
    document.getElementById("pin-reset-email").value = state.currentUser?.email || "";
    showToast("UPI PIN reset successful");
  } catch (error) {
    showToast(error.message);
  }
});

openDeleteModalBtn.addEventListener("click", () => {
  deleteModal.classList.remove("hidden");
});

cancelDeleteBtn.addEventListener("click", () => {
  deleteModal.classList.add("hidden");
  deleteAccountForm.reset();
});

closeTransactionDetailBtn.addEventListener("click", () => {
  transactionDetailModal.classList.add("hidden");
});

deleteAccountForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/auth/delete_account", {
      method: "DELETE",
      body: JSON.stringify({
        user_id: state.currentUser.user_id,
        password: document.getElementById("delete-password").value,
        upi_pin: document.getElementById("delete-upi-pin").value,
      }),
    });
    deleteModal.classList.add("hidden");
    deleteAccountForm.reset();
    state.currentUser = null;
    showDashboard(false);
    showToast("Account deleted permanently");
  } catch (error) {
    showToast(error.message);
  }
});

async function loadBankHandles() {
  try {
    const data = await api("/api/auth/bank-handles");
    bankHandleInput.innerHTML = '<option value="">Select bank handle</option>';
    (data.bank_handles || []).forEach((handle) => {
      const option = document.createElement("option");
      option.value = handle;
      option.textContent = handle.toUpperCase();
      bankHandleInput.appendChild(option);
    });
  } catch (error) {
    showToast(error.message);
  }
}

function setupVisibilityToggles() {
  document.querySelectorAll(".toggle-visibility").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.targetId;
      const targetName = button.dataset.targetName;
      let input = null;

      if (targetId) {
        input = document.getElementById(targetId);
      } else if (targetName) {
        input = button.parentElement.querySelector(`input[name="${targetName}"]`);
      }

      if (!input) {
        return;
      }

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      button.textContent = isPassword ? "Hide" : "Show";
    });
  });
}

ensureDeviceIdentity();
setupVisibilityToggles();
loadBankHandles();
bootstrapSession();
