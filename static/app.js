"use strict";

const $ = (id) => document.getElementById(id);

const TOKEN_KEY = "finance_access_token";
const PAGE_SIZE = 20;

const state = {
  token: sessionStorage.getItem(TOKEN_KEY),
  mode: "login",
  editingId: null,
  transactions: [],
  page: 0,
  hasNext: false,
  dateFrom: "",
  dateTo: "",
  type: "",
  category: "",
  loading: false,
  saving: false,
  deleting: false,
  requestId: 0,
};

const euro = new Intl.NumberFormat("de-DE", {
  style: "currency",
  currency: "EUR",
});

function formatMoney(value) {
  return euro.format(Number(value));
}

function today() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function showMessage(text, isError = false) {
  $("message").textContent = text;
  $("message").classList.toggle("error", isError);
  $("message").hidden = false;
}

function clearMessage() {
  $("message").hidden = true;
  $("message").textContent = "";
}

function setToken(token) {
  state.token = token;

  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

function setAuthMode(mode) {
  state.mode = mode;
  const isLogin = mode === "login";

  $("login-tab").classList.toggle("active", isLogin);
  $("register-tab").classList.toggle("active", !isLogin);

  $("login-tab").setAttribute("aria-pressed", String(isLogin));
  $("register-tab").setAttribute("aria-pressed", String(!isLogin));

  $("auth-submit").textContent = isLogin ? "Log in" : "Create account";
  $("password").minLength = isLogin ? 1 : 8;
  $("password").autocomplete = isLogin
    ? "current-password"
    : "new-password";

  clearMessage();
}

function resetTransactionForm() {
  state.editingId = null;
  $("transaction-form").reset();
  $("transaction-date").value = today();
  $("transaction-form-title").textContent = "Add transaction";
  $("transaction-submit").textContent = "Add transaction";
  $("cancel-edit").hidden = true;
}

function showDashboard(user) {
  $("auth-section").hidden = true;
  $("dashboard-section").hidden = false;
  $("user-menu").hidden = false;
  $("user-email").textContent = user.email;
  $("password").value = "";
}

function logout() {
  setToken(null);

  // Ignore responses from the previous session.
  state.requestId += 1;
  state.transactions = [];
  state.page = 0;
  state.hasNext = false;
  state.loading = false;
  state.dateFrom = "";
  state.dateTo = "";
  state.type = "";
  state.category = "";

  $("period-form").reset();
  $("list-filter-form").reset();
  $("transactions-body").replaceChildren();
  $("income-value").textContent = "—";
  $("expense-value").textContent = "—";
  $("balance-value").textContent = "—";
  $("user-email").textContent = "";

  $("auth-section").hidden = false;
  $("dashboard-section").hidden = true;
  $("user-menu").hidden = true;

  resetTransactionForm();
  setAuthMode("login");
}

function errorText(data, status) {
  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => {
        const field = (item.loc || [])
          .filter((part) => !["body", "query", "path"].includes(part))
          .join(".");

        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join("; ");
  }

  return `Request failed (${status}).`;
}

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { Accept: "application/json" };
  const requestToken = state.token;

  if (auth && requestToken) {
    headers.Authorization = `Bearer ${requestToken}`;
  }

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let response;

  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("Cannot reach the server. Check that it is running.");
  }

  const data = response.status === 204
    ? null
    : await response.json().catch(() => null);

  if (!response.ok) {
    if (
      response.status === 401 &&
      auth &&
      requestToken === state.token
    ) {
      logout();
      showMessage("Your session has expired. Please log in again.", true);
      throw new Error("Please log in again.");
    }

    throw new Error(errorText(data, response.status));
  }

  return data;
}

function periodParams() {
  const params = new URLSearchParams();

  if (state.dateFrom) params.set("date_from", state.dateFrom);
  if (state.dateTo) params.set("date_to", state.dateTo);

  return params;
}

function updatePagination() {
  $("page-label").textContent = `Page ${state.page + 1}`;

  $("previous-page").disabled =
    state.loading || state.page === 0;

  $("next-page").disabled =
    state.loading || !state.hasNext;
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function renderTransactions() {
  const fragment = document.createDocumentFragment();

  for (const transaction of state.transactions) {
    const row = document.createElement("tr");

    row.append(
      cell(transaction.date),
      cell(transaction.category),
      cell(transaction.description || "—"),
    );

    const typeCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `badge ${transaction.type}`;
    badge.textContent =
      transaction.type === "income" ? "Income" : "Expense";
    typeCell.append(badge);

    const amountCell = cell(formatMoney(transaction.amount));
    const actionsCell = document.createElement("td");
    const actions = document.createElement("div");
    actions.className = "row-actions";

    for (const action of ["edit", "delete"]) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.action = action;
      button.dataset.id = String(transaction.id);
      button.textContent = action === "edit" ? "Edit" : "Delete";
      button.setAttribute(
        "aria-label",
        `${button.textContent} transaction ${transaction.id}`,
      );

      if (action === "delete") {
        button.classList.add("danger");
      }

      actions.append(button);
    }

    actionsCell.append(actions);
    row.append(typeCell, amountCell, actionsCell);
    fragment.append(row);
  }

  // User-provided content is inserted as text, never as HTML.
  $("transactions-body").replaceChildren(fragment);
  $("list-status").hidden = state.transactions.length > 0;
  $("list-status").textContent = "No transactions found.";
}

async function loadDashboard() {
  const requestId = ++state.requestId;
  const summaryParams = periodParams();
  const listParams = periodParams();

  if (state.type) listParams.set("type", state.type);
  if (state.category) listParams.set("category", state.category);

  // One additional record tells us whether a next page exists.
  listParams.set("limit", String(PAGE_SIZE + 1));
  listParams.set("offset", String(state.page * PAGE_SIZE));

  state.loading = true;
  state.transactions = [];
  $("transactions-body").replaceChildren();
  $("list-status").hidden = false;
  $("list-status").textContent = "Loading…";
  updatePagination();

  try {
    const [summary, transactions] = await Promise.all([
      api(`/transactions/summary?${summaryParams}`),
      api(`/transactions?${listParams}`),
    ]);

    if (requestId !== state.requestId) return;

    if (transactions.length === 0 && state.page > 0) {
      state.page -= 1;
      return await loadDashboard();
    }

    $("income-value").textContent = formatMoney(summary.income);
    $("expense-value").textContent = formatMoney(summary.expense);
    $("balance-value").textContent = formatMoney(summary.balance);

    state.hasNext = transactions.length > PAGE_SIZE;
    state.transactions = transactions.slice(0, PAGE_SIZE);

    renderTransactions();
  } catch (error) {
    if (requestId !== state.requestId) return;

    state.hasNext = false;
    $("income-value").textContent = "—";
    $("expense-value").textContent = "—";
    $("balance-value").textContent = "—";
    $("list-status").textContent =
      "Could not load data. Apply the filters again to retry.";
    showMessage(error.message, true);
  } finally {
    if (requestId === state.requestId) {
      state.loading = false;
      updatePagination();
    }
  }
}

// AUTHENTICATION

$("login-tab").addEventListener("click", () => setAuthMode("login"));
$("register-tab").addEventListener("click", () => setAuthMode("register"));
$("logout-button").addEventListener("click", logout);

$("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage();

  const mode = state.mode;
  const data = {
    email: $("email").value.trim(),
    password: $("password").value,
  };

  const buttons = [
    $("auth-submit"),
    $("login-tab"),
    $("register-tab"),
  ];

  buttons.forEach((button) => { button.disabled = true; });

  try {
    if (mode === "register") {
      await api("/auth/register", {
        method: "POST",
        body: data,
        auth: false,
      });

      setAuthMode("login");
      showMessage("Account created. Logging you in…");
    }

    const result = await api("/auth/login", {
      method: "POST",
      body: data,
      auth: false,
    });

    setToken(result.access_token);

    const user = await api("/auth/me");
    showDashboard(user);
    clearMessage();
    await loadDashboard();
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
  }
});

// PERIOD AND LIST FILTERS

$("period-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const from = $("date-from").value;
  const to = $("date-to").value;

  if (from && to && from > to) {
    showMessage("The start date must not be after the end date.", true);
    return;
  }

  clearMessage();
  state.dateFrom = from;
  state.dateTo = to;
  state.page = 0;
  await loadDashboard();
});

$("reset-period").addEventListener("click", async () => {
  $("period-form").reset();
  state.dateFrom = "";
  state.dateTo = "";
  state.page = 0;
  clearMessage();
  await loadDashboard();
});

$("list-filter-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  state.type = $("filter-type").value;
  state.category = $("filter-category").value.trim();
  state.page = 0;
  clearMessage();
  await loadDashboard();
});

$("reset-list-filters").addEventListener("click", async () => {
  $("list-filter-form").reset();
  state.type = "";
  state.category = "";
  state.page = 0;
  clearMessage();
  await loadDashboard();
});

$("previous-page").addEventListener("click", async () => {
  if (state.loading || state.page === 0) return;
  state.page -= 1;
  await loadDashboard();
});

$("next-page").addEventListener("click", async () => {
  if (state.loading || !state.hasNext) return;
  state.page += 1;
  await loadDashboard();
});

// CREATE AND UPDATE

$("cancel-edit").addEventListener("click", () => {
  if (!state.saving) resetTransactionForm();
});

$("transaction-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.saving || state.deleting) return;

  const category = $("transaction-category").value.trim();

  if (!category) {
    showMessage("Enter a category.", true);
    return;
  }

  const data = {
    type: $("transaction-type").value,
    // Keep money as a decimal string when sending it to the API.
    amount: $("transaction-amount").value,
    category,
    date: $("transaction-date").value,
    description: $("transaction-description").value.trim() || null,
  };

  const editingId = state.editingId;
  const sessionToken = state.token;
  const controls = [...$("transaction-form").elements];

  state.saving = true;
  controls.forEach((control) => { control.disabled = true; });
  clearMessage();

  try {
    await api(
      editingId === null
        ? "/transactions"
        : `/transactions/${editingId}`,
      {
        method: editingId === null ? "POST" : "PATCH",
        body: data,
      },
    );

    if (sessionToken !== state.token) return;

    resetTransactionForm();
    state.page = 0;

    showMessage(
      editingId === null
        ? "Transaction added. Active filters still apply."
        : "Transaction updated.",
    );

    await loadDashboard();
  } catch (error) {
    if (sessionToken === state.token) {
      showMessage(error.message, true);
    }
  } finally {
    state.saving = false;
    controls.forEach((control) => { control.disabled = false; });
  }
});

// ROW ACTIONS

$("transactions-body").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button || state.saving || state.deleting || state.loading) return;

  const id = Number(button.dataset.id);
  const transaction = state.transactions.find((item) => item.id === id);
  if (!transaction) return;

  if (button.dataset.action === "edit") {
    state.editingId = id;

    $("transaction-type").value = transaction.type;
    $("transaction-amount").value = transaction.amount;
    $("transaction-category").value = transaction.category;
    $("transaction-date").value = transaction.date;
    $("transaction-description").value = transaction.description || "";

    $("transaction-form-title").textContent = "Edit transaction";
    $("transaction-submit").textContent = "Save changes";
    $("cancel-edit").hidden = false;
    $("transaction-amount").focus();
    clearMessage();
    return;
  }

  const confirmed = window.confirm(
    `Delete ${transaction.category} — ${formatMoney(transaction.amount)}?`,
  );

  if (!confirmed) return;

  const sessionToken = state.token;
  state.deleting = true;
  button.disabled = true;
  clearMessage();

  try {
    await api(`/transactions/${id}`, { method: "DELETE" });

    if (sessionToken !== state.token) return;

    if (state.editingId === id) resetTransactionForm();

    showMessage("Transaction deleted.");
    await loadDashboard();
  } catch (error) {
    if (sessionToken === state.token) {
      showMessage(error.message, true);
    }
  } finally {
    state.deleting = false;
    button.disabled = false;
  }
});

// RESTORE THE SESSION AFTER A PAGE REFRESH

async function init() {
  resetTransactionForm();

  if (!state.token) return;

  $("auth-section").hidden = true;

  try {
    const user = await api("/auth/me");
    showDashboard(user);
    await loadDashboard();
  } catch (error) {
    $("auth-section").hidden = false;
    showMessage(error.message, true);
  }
}

init();