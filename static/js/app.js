/**
 * Smart College Complaint Management System
 * Frontend Application Script
 */

// Global State
let currentUser = null;
let authToken = null;
let availableCategories = [];
let adminComplaintsList = [];
let searchTimeout = null;

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  initAuth();
  fetchMetaOptions();
  renderNavigation();

  // If user is already logged in, redirect to their dashboard
  if (currentUser) {
    if (currentUser.role === "admin") {
      switchView("admin-dashboard");
    } else {
      switchView("student-dashboard");
    }
  } else {
    switchView("home");
  }
});

// ==========================================
// Authentication State Management
// ==========================================

function initAuth() {
  try {
    const savedUser = localStorage.getItem("college_cms_user");
    const savedToken = localStorage.getItem("college_cms_token");
    if (savedUser && savedToken) {
      currentUser = JSON.parse(savedUser);
      authToken = savedToken;
    }
  } catch (e) {
    console.error("Error reading saved session:", e);
    clearAuth();
  }
}

function saveAuth(user, token) {
  currentUser = user;
  authToken = token;
  localStorage.setItem("college_cms_user", JSON.stringify(user));
  localStorage.setItem("college_cms_token", token);
  renderNavigation();
}

function clearAuth() {
  currentUser = null;
  authToken = null;
  localStorage.removeItem("college_cms_user");
  localStorage.removeItem("college_cms_token");
  renderNavigation();
}

async function logout() {
  if (authToken) {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch (e) {
      // Ignore logout errors
    }
  }
  clearAuth();
  showToast("Logged out successfully.", "info");
  switchView("home");
}

// ==========================================
// Navigation & View Routing
// ==========================================

function switchView(viewName) {
  // Hide all views
  document.querySelectorAll(".view-section").forEach((sec) => {
    sec.classList.remove("active-view");
  });

  const target = document.getElementById(`view-${viewName}`);
  if (target) {
    target.classList.add("active-view");
  }

  // View-specific trigger actions
  if (viewName === "student-dashboard") {
    if (!currentUser || currentUser.role !== "student") {
      switchView("student-auth");
      return;
    }
    updateStudentHeader();
    loadStudentComplaints();
  } else if (viewName === "admin-dashboard") {
    if (!currentUser || currentUser.role !== "admin") {
      switchView("admin-auth");
      return;
    }
    updateAdminHeader();
    loadAdminStats();
    loadAdminComplaints();
  }

  renderNavigation();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderNavigation() {
  const navContainer = document.getElementById("nav-links");
  const heroActions = document.getElementById("hero-actions");

  let navHtml = `
    <li><button class="nav-btn" onclick="switchView('home')">Home</button></li>
  `;

  let heroHtml = "";

  if (!currentUser) {
    // Unauthenticated State
    navHtml += `
      <li><button class="nav-btn" onclick="switchView('student-auth')">Student Portal</button></li>
      <li><button class="nav-btn nav-btn-primary" onclick="switchView('admin-auth')">Admin Portal</button></li>
    `;

    heroHtml = `
      <button class="btn btn-white" onclick="switchView('student-auth')">
        Student Login / Register
      </button>
      <button class="btn btn-outline-white" onclick="switchView('admin-auth')">
        Admin Portal Login
      </button>
    `;
  } else if (currentUser.role === "student") {
    // Student Logged In
    navHtml += `
      <li><button class="nav-btn" onclick="switchView('student-dashboard')">My Complaints</button></li>
      <li>
        <span class="nav-user-badge">
          🎓 ${escapeHtml(currentUser.name)}
          <span class="role-tag student">Student</span>
        </span>
      </li>
      <li><button class="nav-btn btn-secondary btn-sm" onclick="logout()">Logout</button></li>
    `;

    heroHtml = `
      <button class="btn btn-white" onclick="switchView('student-dashboard')">
        Go to Student Dashboard
      </button>
      <button class="btn btn-outline-white" onclick="openNewComplaintModal()">
        + Lodge New Grievance
      </button>
    `;
  } else if (currentUser.role === "admin") {
    // Admin Logged In
    navHtml += `
      <li><button class="nav-btn" onclick="switchView('admin-dashboard')">Admin Console</button></li>
      <li>
        <span class="nav-user-badge">
          🛡️ ${escapeHtml(currentUser.name)}
          <span class="role-tag admin">Admin</span>
        </span>
      </li>
      <li><button class="nav-btn btn-secondary btn-sm" onclick="logout()">Logout</button></li>
    `;

    heroHtml = `
      <button class="btn btn-white" onclick="switchView('admin-dashboard')">
        Open Admin Console
      </button>
    `;
  }

  if (navContainer) navContainer.innerHTML = navHtml;
  if (heroActions) heroActions.innerHTML = heroHtml;
}

// ==========================================
// API Fetch Helper
// ==========================================

async function apiFetch(endpoint, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  try {
    const response = await fetch(endpoint, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 401) {
        // Expired or invalid session
        clearAuth();
        showToast("Session expired. Please log in again.", "error");
        switchView("home");
      }
      const errorMsg = data.detail || data.message || "An unexpected error occurred.";
      throw new Error(errorMsg);
    }

    return data;
  } catch (err) {
    throw err;
  }
}

// ==========================================
// Meta & Categories Fetching
// ==========================================

async function fetchMetaOptions() {
  try {
    const data = await apiFetch("/api/meta/options");
    availableCategories = data.categories || [];

    // Populate category dropdowns
    const compCategorySelect = document.getElementById("complaint-category");
    const adminCategorySelect = document.getElementById("admin-filter-category");

    if (compCategorySelect) {
      compCategorySelect.innerHTML = availableCategories
        .map((cat) => `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`)
        .join("");
    }

    if (adminCategorySelect) {
      adminCategorySelect.innerHTML =
        `<option value="All">All Categories</option>` +
        availableCategories
          .map((cat) => `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`)
          .join("");
    }
  } catch (e) {
    console.warn("Failed to load options metadata:", e);
  }
}

// ==========================================
// Student Auth Handlers
// ==========================================

function toggleStudentAuthTab(tab) {
  const loginBtn = document.getElementById("tab-btn-student-login");
  const signupBtn = document.getElementById("tab-btn-student-signup");
  const loginForm = document.getElementById("form-student-login");
  const signupForm = document.getElementById("form-student-signup");

  if (tab === "login") {
    loginBtn.classList.add("active");
    signupBtn.classList.remove("active");
    loginForm.style.display = "block";
    signupForm.style.display = "none";
  } else {
    loginBtn.classList.remove("active");
    signupBtn.classList.add("active");
    loginForm.style.display = "none";
    signupForm.style.display = "block";
  }
}

async function handleStudentLogin(event) {
  event.preventDefault();
  const email = document.getElementById("student-login-email").value.trim();
  const password = document.getElementById("student-login-password").value;

  try {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (data.user.role === "admin") {
      showToast("Notice: Logged in as Administrator.", "info");
      saveAuth(data.user, data.token);
      switchView("admin-dashboard");
    } else {
      showToast(data.message || "Logged in successfully!", "success");
      saveAuth(data.user, data.token);
      switchView("student-dashboard");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleStudentSignup(event) {
  event.preventDefault();
  const name = document.getElementById("signup-name").value.trim();
  const roll_number = document.getElementById("signup-roll").value.trim();
  const department = document.getElementById("signup-dept").value;
  const email = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;
  const confirmPassword = document.getElementById("signup-confirm-password").value;

  if (password !== confirmPassword) {
    showToast("Passwords do not match.", "error");
    return;
  }

  try {
    const data = await apiFetch("/api/auth/student-signup", {
      method: "POST",
      body: JSON.stringify({
        name,
        roll_number,
        department,
        email,
        password,
      }),
    });

    showToast("Registration successful! Welcome to the portal.", "success");
    saveAuth(data.user, data.token);
    switchView("student-dashboard");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==========================================
// Admin Auth Handler
// ==========================================

async function handleAdminLogin(event) {
  event.preventDefault();
  const email = document.getElementById("admin-login-email").value.trim();
  const password = document.getElementById("admin-login-password").value;

  try {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (data.user.role !== "admin") {
      showToast("Access Denied: Account does not have administrator privileges.", "error");
      return;
    }

    showToast("Administrator login verified!", "success");
    saveAuth(data.user, data.token);
    switchView("admin-dashboard");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==========================================
// Student Dashboard & Complaints
// ==========================================

function updateStudentHeader() {
  if (!currentUser) return;
  const title = document.getElementById("student-welcome-title");
  const info = document.getElementById("student-profile-info");
  if (title) title.textContent = `Welcome, ${currentUser.name}`;
  if (info) {
    info.textContent = `Roll No: ${currentUser.roll_number || "N/A"} | Department: ${currentUser.department || "General"} | ${currentUser.email}`;
  }
}

async function loadStudentComplaints() {
  const container = document.getElementById("student-complaints-container");
  if (!container) return;

  const filterSelect = document.getElementById("student-filter-status");
  const statusFilter = filterSelect ? filterSelect.value : "All";

  container.innerHTML = `
    <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
      Loading your complaints...
    </div>
  `;

  try {
    const url = statusFilter && statusFilter !== "All"
      ? `/api/complaints/my?status=${encodeURIComponent(statusFilter)}`
      : "/api/complaints/my";

    const complaints = await apiFetch(url);

    // Compute stats
    updateStudentStats(complaints, statusFilter === "All");

    if (complaints.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📝</div>
          <h3>No Complaints Found</h3>
          <p>${statusFilter === "All" ? "You haven't submitted any complaints yet. Encountered a campus issue? Lodge one now!" : `No complaints with status "${escapeHtml(statusFilter)}".`}</p>
          <button class="btn btn-primary btn-sm" onclick="openNewComplaintModal()">+ Lodge New Complaint</button>
        </div>
      `;
      return;
    }

    container.innerHTML = complaints.map(renderStudentComplaintCard).join("");
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <p style="color: var(--status-rejected);">Failed to load complaints: ${escapeHtml(err.message)}</p>
        <button class="btn btn-secondary btn-sm" onclick="loadStudentComplaints()">Retry</button>
      </div>
    `;
  }
}

function updateStudentStats(complaints, isFullList) {
  if (!isFullList) return; // Don't override stats when filtered

  let pending = 0;
  let inProgress = 0;
  let resolved = 0;

  complaints.forEach((c) => {
    if (c.status === "Pending" || c.status === "Under Review") pending++;
    else if (c.status === "In Progress") inProgress++;
    else if (c.status === "Resolved") resolved++;
  });

  const totalEl = document.getElementById("student-stat-total");
  const pendingEl = document.getElementById("student-stat-pending");
  const progressEl = document.getElementById("student-stat-progress");
  const resolvedEl = document.getElementById("student-stat-resolved");

  if (totalEl) totalEl.textContent = complaints.length;
  if (pendingEl) pendingEl.textContent = pending;
  if (progressEl) progressEl.textContent = inProgress;
  if (resolvedEl) resolvedEl.textContent = resolved;
}

function renderStudentComplaintCard(c) {
  const statusClass = getStatusClass(c.status);
  const priorityClass = getPriorityClass(c.priority);
  const formattedDate = formatDate(c.created_at);
  const updatedDate = formatDate(c.updated_at);

  let adminRemarksBlock = "";
  if (c.admin_remarks || c.verified_by) {
    adminRemarksBlock = `
      <div class="admin-remarks-box">
        <div class="title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          Admin Verification & Action Notes
          ${c.verified_by ? `<span style="font-weight: 500; font-size: 0.8rem; color: var(--text-muted);">(By ${escapeHtml(c.verified_by)})</span>` : ""}
        </div>
        <div style="color: #1e293b; margin-top: 4px;">
          ${escapeHtml(c.admin_remarks || "Status has been updated by administration.")}
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
          Last updated: ${updatedDate}
        </div>
      </div>
    `;
  }

  return `
    <div class="complaint-card">
      <div class="complaint-header">
        <div>
          <span class="ticket-tag">${escapeHtml(c.ticket_id)}</span>
          <span class="badge ${priorityClass}" style="margin-left: 6px;">${escapeHtml(c.priority)} Priority</span>
        </div>
        <div>
          <span class="badge ${statusClass}">● ${escapeHtml(c.status)}</span>
        </div>
      </div>

      <div class="complaint-title">${escapeHtml(c.title)}</div>

      <div class="complaint-meta">
        <span>📁 <strong>Category:</strong> ${escapeHtml(c.category)}</span>
        ${c.location ? `<span>📍 <strong>Location:</strong> ${escapeHtml(c.location)}</span>` : ""}
        <span>🕒 <strong>Submitted:</strong> ${formattedDate}</span>
      </div>

      <div class="complaint-desc">${escapeHtml(c.description)}</div>

      ${adminRemarksBlock}
    </div>
  `;
}

// Student New Complaint Modal
function openNewComplaintModal() {
  const modal = document.getElementById("modal-new-complaint");
  if (modal) {
    document.getElementById("form-new-complaint").reset();
    modal.classList.add("active");
  }
}

function closeNewComplaintModal() {
  const modal = document.getElementById("modal-new-complaint");
  if (modal) modal.classList.remove("active");
}

async function handleCreateComplaint(event) {
  event.preventDefault();

  const title = document.getElementById("complaint-title").value.trim();
  const category = document.getElementById("complaint-category").value;
  const priority = document.getElementById("complaint-priority").value;
  const location = document.getElementById("complaint-location").value.trim();
  const description = document.getElementById("complaint-description").value.trim();

  try {
    const newComplaint = await apiFetch("/api/complaints", {
      method: "POST",
      body: JSON.stringify({
        title,
        category,
        priority,
        location,
        description,
      }),
    });

    closeNewComplaintModal();
    showToast(`Complaint registered successfully! Ticket: ${newComplaint.ticket_id}`, "success");
    loadStudentComplaints();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==========================================
// Admin Dashboard & Management
// ==========================================

function updateAdminHeader() {
  if (!currentUser) return;
  const info = document.getElementById("admin-profile-info");
  if (info) {
    info.textContent = `Administrator: ${currentUser.name} (${currentUser.email}) | ${currentUser.department || "Central Administration"}`;
  }
}

async function loadAdminStats() {
  try {
    const stats = await apiFetch("/api/admin/stats");
    document.getElementById("admin-stat-total").textContent = stats.total;
    document.getElementById("admin-stat-pending").textContent = stats.pending;
    document.getElementById("admin-stat-review").textContent = stats.under_review;
    document.getElementById("admin-stat-progress").textContent = stats.in_progress;
    document.getElementById("admin-stat-resolved").textContent = stats.resolved;
    document.getElementById("admin-stat-rejected").textContent = stats.rejected;
  } catch (e) {
    console.warn("Failed to load admin stats:", e);
  }
}

async function loadAdminComplaints() {
  const tbody = document.getElementById("admin-complaints-tbody");
  if (!tbody) return;

  const statusFilter = document.getElementById("admin-filter-status").value;
  const categoryFilter = document.getElementById("admin-filter-category").value;
  const priorityFilter = document.getElementById("admin-filter-priority").value;
  const search = document.getElementById("admin-search-input").value.trim();

  tbody.innerHTML = `
    <tr>
      <td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">
        Loading complaints...
      </td>
    </tr>
  `;

  try {
    const params = new URLSearchParams();
    if (statusFilter && statusFilter !== "All") params.append("status", statusFilter);
    if (categoryFilter && categoryFilter !== "All") params.append("category", categoryFilter);
    if (priorityFilter && priorityFilter !== "All") params.append("priority", priorityFilter);
    if (search) params.append("search", search);

    const complaints = await apiFetch(`/api/admin/complaints?${params.toString()}`);
    adminComplaintsList = complaints;

    if (complaints.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 2.5rem 1rem;">
            <div style="font-size: 1.5rem; margin-bottom: 6px;">📂</div>
            <strong>No complaints matched your criteria.</strong>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">
              Try changing the search query or filters.
            </p>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = complaints.map(renderAdminTableRow).join("");
  } catch (err) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: var(--status-rejected);">
          Error loading complaints: ${escapeHtml(err.message)}
        </td>
      </tr>
    `;
  }
}

function renderAdminTableRow(c) {
  const statusClass = getStatusClass(c.status);
  const priorityClass = getPriorityClass(c.priority);
  const dateStr = formatDate(c.created_at);

  return `
    <tr>
      <td>
        <span class="ticket-tag">${escapeHtml(c.ticket_id)}</span>
      </td>
      <td style="white-space: nowrap; font-size: 0.82rem; color: var(--text-muted);">
        ${dateStr}
      </td>
      <td>
        <strong>${escapeHtml(c.student_name)}</strong><br>
        <small style="color: var(--text-muted);">Roll: ${escapeHtml(c.student_roll)}</small><br>
        <small style="color: var(--text-muted); font-size: 0.78rem;">${escapeHtml(c.student_dept)}</small>
      </td>
      <td>
        <div style="font-weight: 600; color: var(--secondary); max-width: 260px;">${escapeHtml(c.title)}</div>
        <span style="font-size: 0.8rem; color: var(--text-muted);">📁 ${escapeHtml(c.category)}</span>
        ${c.location ? `<br><small style="color: var(--text-muted);">📍 ${escapeHtml(c.location)}</small>` : ""}
        ${c.admin_remarks ? `<div style="font-size: 0.78rem; color: #475569; margin-top: 4px; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">💬 ${escapeHtml(c.admin_remarks)}</div>` : ""}
      </td>
      <td>
        <span class="badge ${priorityClass}">${escapeHtml(c.priority)}</span>
      </td>
      <td>
        <span class="badge ${statusClass}">● ${escapeHtml(c.status)}</span>
        ${c.verified_by ? `<div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">by ${escapeHtml(c.verified_by)}</div>` : ""}
      </td>
      <td style="white-space: nowrap;">
        <button class="btn btn-primary btn-sm" onclick="openAdminUpdateModal(${c.id})">
          Verify / Update
        </button>
        <button class="btn btn-secondary btn-sm" onclick="deleteComplaintAsAdmin(${c.id}, '${escapeHtml(c.ticket_id)}')" style="color: var(--status-rejected); margin-left: 4px;" title="Delete">
          🗑️
        </button>
      </td>
    </tr>
  `;
}

function debounceAdminSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    loadAdminComplaints();
  }, 300);
}

// Admin Update Modal
function openAdminUpdateModal(complaintId) {
  const complaint = adminComplaintsList.find((c) => c.id === complaintId);
  if (!complaint) return;

  document.getElementById("admin-update-complaint-id").value = complaint.id;
  document.getElementById("modal-update-ticket").textContent = complaint.ticket_id;

  const priorityBadge = document.getElementById("modal-update-priority");
  priorityBadge.textContent = complaint.priority + " Priority";
  priorityBadge.className = `badge ${getPriorityClass(complaint.priority)}`;

  document.getElementById("modal-update-title").textContent = complaint.title;
  document.getElementById("modal-update-student").textContent =
    `Student: ${complaint.student_name} (${complaint.student_roll}) - Dept: ${complaint.student_dept}`;
  document.getElementById("modal-update-desc").textContent = complaint.description;

  document.getElementById("admin-select-status").value = complaint.status;
  document.getElementById("admin-input-remarks").value = complaint.admin_remarks || "";

  document.getElementById("modal-admin-update").classList.add("active");
}

function closeAdminUpdateModal() {
  const modal = document.getElementById("modal-admin-update");
  if (modal) modal.classList.remove("active");
}

async function handleAdminStatusUpdate(event) {
  event.preventDefault();
  const complaintId = document.getElementById("admin-update-complaint-id").value;
  const newStatus = document.getElementById("admin-select-status").value;
  const remarks = document.getElementById("admin-input-remarks").value;

  try {
    const updated = await apiFetch(`/api/admin/complaints/${complaintId}/status`, {
      method: "PUT",
      body: JSON.stringify({
        status: newStatus,
        admin_remarks: remarks,
      }),
    });

    closeAdminUpdateModal();
    showToast(`Complaint ${updated.ticket_id} status updated to '${updated.status}'!`, "success");
    loadAdminComplaints();
    loadAdminStats();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteComplaintAsAdmin(complaintId, ticketId) {
  if (!confirm(`Are you sure you want to permanently delete complaint ${ticketId}?`)) {
    return;
  }

  try {
    await apiFetch(`/api/admin/complaints/${complaintId}`, {
      method: "DELETE",
    });
    showToast(`Complaint ${ticketId} deleted successfully.`, "info");
    loadAdminComplaints();
    loadAdminStats();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==========================================
// Helper Utilities
// ==========================================

function getStatusClass(status) {
  switch (status) {
    case "Pending":
      return "badge-pending";
    case "Under Review":
      return "badge-under-review";
    case "In Progress":
      return "badge-in-progress";
    case "Resolved":
      return "badge-resolved";
    case "Rejected":
      return "badge-rejected";
    default:
      return "badge-pending";
  }
}

function getPriorityClass(priority) {
  switch (priority) {
    case "Low":
      return "priority-low";
    case "Medium":
      return "priority-medium";
    case "High":
      return "priority-high";
    case "Urgent":
      return "priority-urgent";
    default:
      return "priority-medium";
  }
}

function formatDate(dateStr) {
  if (!dateStr) return "N/A";
  try {
    const d = new Date(dateStr);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (e) {
    return dateStr;
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "error") icon = "⚠️";

  toast.innerHTML = `
    <span>${icon}</span>
    <span style="flex: 1;">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 4000);
}
