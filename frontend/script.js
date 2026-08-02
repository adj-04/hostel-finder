const API_BASE = "http://127.0.0.1:5000";

// USER MANAGEMENT
function logout() {
  localStorage.removeItem("user");
  localStorage.removeItem("token");
  window.location.href = "login.html";
}

function getLoggedUser() {
  const userData = localStorage.getItem("user");
  return userData ? JSON.parse(userData) : null;
}

const user = getLoggedUser();
if (!user) {
  window.location.href = "login.html";
}

const notify = window.toast ? window.toast : (msg) => alert(msg);
const notifyError = window.toastError ? window.toastError : (msg) => alert(msg);
const notifySuccess = window.toastSuccess ? window.toastSuccess : (msg) => alert(msg);

// PRICE SLIDER
const priceRange = document.getElementById("priceRange");
const priceValue = document.getElementById("priceValue");
if (priceRange && priceValue) {
  priceRange.addEventListener("input", () => {
    priceValue.textContent = `₹${Number(priceRange.value).toLocaleString("en-IN")}`;
  });
}

// MAP SETUP
let map;
let markers = [];
if (document.getElementById("map")) {
  map = L.map("map").setView([13.0827, 80.2707], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
}

// LOCATION SUGGESTIONS
async function loadLocationChips() {
  const wrap = document.getElementById("locationChips");
  if (!wrap) return;
  try {
    const res = await fetch(`${API_BASE}/get_locations`);
    const locations = await res.json();
    wrap.innerHTML = locations
      .map((loc) => `<span class="chip" data-loc="${loc}">${loc}</span>`)
      .join("");
    wrap.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const isActive = chip.classList.contains("chip--active");
        wrap.querySelectorAll(".chip").forEach((c) => c.classList.remove("chip--active"));
        const searchBox = document.getElementById("searchBox");
        if (!isActive && searchBox) {
          chip.classList.add("chip--active");
          searchBox.value = chip.dataset.loc;
        } else if (searchBox) {
          searchBox.value = "";
        }
        fetchHostels();
      });
    });
  } catch (err) {
    console.error("Failed to load locations", err);
  }
}

// NEAR ME (GEOLOCATION)
let userCoords = null;
function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

const nearMeBtn = document.getElementById("nearMeBtn");
nearMeBtn?.addEventListener("click", () => {
  if (!navigator.geolocation) {
    notifyError("Geolocation isn't supported by this browser.");
    return;
  }
  if (userCoords) {
    // toggle off
    userCoords = null;
    nearMeBtn.classList.remove("active");
    nearMeBtn.textContent = "Near me";
    fetchHostels();
    return;
  }
  nearMeBtn.textContent = "Locating…";
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      userCoords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      nearMeBtn.classList.add("active");
      nearMeBtn.textContent = "Sorted by distance";
      notifySuccess("Showing hostels sorted by distance from you.");
      fetchHostels();
    },
    () => {
      nearMeBtn.textContent = "Near me";
      notifyError("Couldn't get your location. Check location permissions.");
    },
    { enableHighAccuracy: true, timeout: 8000 }
  );
});

// HOSTELS
let currentHostel = null;
let searchDebounceTimer = null;

function renderSkeletons(count = 6) {
  const list = document.getElementById("hostelList");
  if (!list) return;
  list.innerHTML = Array.from({ length: count })
    .map(
      () => `
      <div class="skeleton-card">
        <div class="skeleton-line w60"></div>
        <div class="skeleton-line w80"></div>
        <div class="skeleton-line w40"></div>
      </div>`
    )
    .join("");
}

async function fetchHostels() {
  const search = document.getElementById("searchBox")?.value.trim() || "";
  const maxPrice = priceRange ? priceRange.value : 9999999;

  renderSkeletons();

  const data = { search, price: maxPrice };

  try {
    const res = await fetch(`${API_BASE}/get_hostels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    let hostels = await res.json();

    if (userCoords) {
      hostels = hostels
        .filter((h) => h.lat && h.lng)
        .map((h) => ({
          ...h,
          _distanceKm: haversineKm(userCoords.lat, userCoords.lng, h.lat, h.lng),
        }))
        .sort((a, b) => a._distanceKm - b._distanceKm);
    }

    displayHostels(hostels);
    updateLastSynced();
  } catch (err) {
    console.error(err);
    const list = document.getElementById("hostelList");
    if (list) list.innerHTML = `<p class="hint-text">Couldn't reach the server. Is the backend running on ${API_BASE}?</p>`;
    notifyError("Server error fetching hostels.");
  }
}

function displayHostels(hostels) {
  const list = document.getElementById("hostelList");
  const countEl = document.getElementById("resultsCount");
  if (!list) return;

  list.innerHTML = "";
  if (map) {
    markers.forEach((m) => map.removeLayer(m));
    markers = [];
  }

  if (countEl) {
    countEl.innerHTML = `<strong>${hostels.length}</strong> hostel${hostels.length === 1 ? "" : "s"} found`;
  }

  if (!hostels.length) {
    list.innerHTML = `
      <div class="hint-text">
        <p>No hostels match your search just yet.</p>
        <p class="muted">Try a broader keyword, raise the price cap, or clear the "Near me" filter.</p>
      </div>`;
    return;
  }

  hostels.forEach((h, index) => {
    const facs = Array.isArray(h.facilities) ? h.facilities : [];
    const card = document.createElement("div");
    card.className = "card";
    card.style.animationDelay = `${Math.min(index * 0.06, 0.6)}s`;

    const verifiedBadge = h.verified
      ? `<span class="badge verified">Verified</span>`
      : `<span class="badge pending">Pending review</span>`;
    const distanceBadge =
      typeof h._distanceKm === "number"
        ? `<span class="badge distance">${h._distanceKm.toFixed(1)} km away</span>`
        : "";
    const sourceBadge =
      h.data_source === "generated_sample"
        ? `<span class="badge sample">Sample listing</span>`
        : h.data_source === "real_operator"
        ? `<span class="badge operator">Real operator · verify pricing</span>`
        : h.data_source === "owner_submitted"
        ? `<span class="badge owner">Owner listed</span>`
        : "";

    card.innerHTML = `
      <h3>${h.name}</h3>
      <p>${h.address || ""}</p>
      <p class="price">₹${Number(h.price).toLocaleString("en-IN")}/month · ${h.type || "N/A"}</p>
      <div class="card-badges">${verifiedBadge}${distanceBadge}${sourceBadge}</div>
      <p><strong>Facilities:</strong> ${facs.join(", ") || "N/A"}</p>
      <button class="view-more-btn">View details</button>
    `;
    const btn = card.querySelector(".view-more-btn");
    btn.addEventListener("click", () => openViewModal(h));
    list.appendChild(card);

    if (map && h.lat && h.lng) {
      const marker = L.marker([h.lat, h.lng])
        .addTo(map)
        .bindPopup(`<b>${h.name}</b><br>${h.address}<br>₹${h.price}/month`);
      markers.push(marker);
    }
  });
}

// Debounced live search as you type
document.getElementById("searchBox")?.addEventListener("input", () => {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(fetchHostels, 350);
});
document.getElementById("searchBox")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    clearTimeout(searchDebounceTimer);
    fetchHostels();
  }
});

document.getElementById("applyFilters")?.addEventListener("click", fetchHostels);
if (document.getElementById("hostelList")) {
  fetchHostels();
  loadLocationChips();
}

// LIVE UPDATES (SSE)
let lastSyncedAt = Date.now();
function updateLastSynced() {
  lastSyncedAt = Date.now();
  paintLastSynced();
}
function paintLastSynced() {
  const el = document.getElementById("lastSynced");
  if (!el) return;
  const secs = Math.max(0, Math.round((Date.now() - lastSyncedAt) / 1000));
  el.textContent = secs < 3 ? "Live" : `Synced ${secs}s ago`;
}
setInterval(paintLastSynced, 1000);

function connectLiveStream() {
  const badge = document.getElementById("liveBadge");
  if (!document.getElementById("hostelList")) return; // only on student home
  if (typeof EventSource === "undefined") return;

  let knownVersion = null;
  let es;
  try {
    es = new EventSource(`${API_BASE}/stream_hostels`);
  } catch (e) {
    return;
  }

  es.addEventListener("hello", () => badge?.classList.remove("offline"));
  es.addEventListener("update", (e) => {
    try {
      const payload = JSON.parse(e.data);
      if (knownVersion !== null && payload.version !== knownVersion) {
        fetchHostels();
      }
      knownVersion = payload.version;
    } catch (err) {
      /* ignore */
    }
    badge?.classList.remove("offline");
  });
  es.addEventListener("heartbeat", () => badge?.classList.remove("offline"));
  es.onerror = () => {
    badge?.classList.add("offline");
  };
}
connectLiveStream();

// VIEW MORE MODAL
const viewModal = document.getElementById("viewModal");
const viewContent = document.getElementById("viewContent");
const reviewList = document.getElementById("reviewList");

function openViewModal(hostel) {
  currentHostel = hostel;
  if (!viewModal) return;

  viewContent.innerHTML = `
    <h2>${hostel.name}</h2>
    <p><strong>Address:</strong> ${hostel.address}</p>
    <p><strong>Price:</strong> ₹${Number(hostel.price).toLocaleString("en-IN")}/month</p>
    <p><strong>Type:</strong> ${hostel.type || "N/A"}</p>
    <p><strong>Facilities:</strong> ${Array.isArray(hostel.facilities) ? hostel.facilities.join(", ") : "N/A"}</p>
    <div class="btn-group" style="margin-top: 16px;">
      <button type="button" class="btn-secondary" onclick="showReviews()">View reviews</button>
      <button type="button" class="btn-secondary" onclick="showWriteReview()">Write a review</button>
      <button type="button" onclick="proceedToPay()">Reserve &amp; pay</button>
    </div>
  `;
  reviewList.innerHTML = "";
  viewModal.classList.remove("hidden");
}

function closeViewModal() {
  viewModal.classList.add("hidden");
  reviewList.innerHTML = "";
}

// REVIEWS
function showReviews() {
  if (!currentHostel) return;
  reviewList.innerHTML = "Loading reviews...";
  fetch(`${API_BASE}/get_reviews/${currentHostel._id}`)
    .then((res) => res.json())
    .then((reviews) => {
      if (!reviews.length) reviewList.innerHTML = "<p class='muted'>No reviews yet — be the first to write one.</p>";
      else {
        reviewList.innerHTML = reviews
          .map(
            (r) => `
          <div class="review-card">
            <p><strong>${r.user}</strong> rated <strong>${r.rating}/5</strong></p>
            <p>${r.text}</p>
          </div>
        `
          )
          .join("");
      }
    })
    .catch((err) => {
      console.error(err);
      reviewList.innerHTML = "<p>Error loading reviews.</p>";
    });
}

function showWriteReview() {
  if (!currentHostel) return;
  reviewList.innerHTML = `
    <form id="reviewForm">
      <div class="form-group">
        <input type="hidden" id="reviewHostelId" value="${currentHostel._id}">
        <label>Rating <input type="number" id="rating" min="1" max="5" required></label>
        <label>Review <textarea id="reviewText" required placeholder="How was your stay?"></textarea></label>
        <button type="submit">Submit review</button>
      </div>
    </form>
  `;
  document.getElementById("reviewForm").addEventListener("submit", submitReview);
}

async function submitReview(e) {
  e.preventDefault();
  const hostelId = document.getElementById("reviewHostelId").value;
  const rating = document.getElementById("rating").value;
  const text = document.getElementById("reviewText").value;

  const user = getLoggedUser();
  if (!user) return notifyError("Please login first!");

  try {
    const res = await fetch(`${API_BASE}/add_review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hostelId, rating, text, user: user.name }),
    });
    const result = await res.json();
    if (result.success) {
      notifySuccess("Review submitted!");
      showReviews();
    } else {
      notifyError("Failed to submit review: " + (result.message || ""));
    }
  } catch (err) {
    console.error(err);
    notifyError("Server error adding review");
  }
}

// PAYMENT
function proceedToPay() {
  if (!currentHostel) return;
  try {
    localStorage.setItem("payment_hostel", JSON.stringify(currentHostel));
  } catch (e) {
    /* ignore */
  }
  window.location.href = "payment.html";
}

// OWNER DASHBOARD
const ownerListEl = document.getElementById("ownerHostelList");
const addHostelForm = document.getElementById("addHostelForm");
const logoutBtn = document.getElementById("logoutBtn");

logoutBtn?.addEventListener("click", (e) => {
  e.preventDefault();
  logout();
});

async function fetchOwnerHostels() {
  if (!ownerListEl) return;
  ownerListEl.innerHTML = "<p>Loading...</p>";
  try {
    const res = await fetch(`${API_BASE}/owner_hostels/${user.user_id}`);
    const hostels = await res.json();
    ownerListEl.innerHTML = "";
    if (!hostels.length) {
      ownerListEl.innerHTML = "<p class='hint-text'>No hostels listed yet. Add your first one above.</p>";
      return;
    }
    hostels.forEach((h, index) => {
      const card = document.createElement("div");
      card.className = "hostel-card";
      card.style.animationDelay = `${index * 0.08}s`;
      card.innerHTML = `
        <h4>${h.name}</h4>
        <p>${h.address}</p>
        <p class="price">₹${Number(h.price).toLocaleString("en-IN")}/month • ${h.type || "N/A"}</p>
        <p>Facilities: ${(Array.isArray(h.facilities) ? h.facilities.join(", ") : "N/A")}</p>
        <div class="card-badges">${h.verified ? `<span class="badge verified">Verified</span>` : `<span class="badge pending">Pending</span>`}</div>
      `;
      ownerListEl.appendChild(card);
    });
  } catch (err) {
    console.error(err);
    ownerListEl.innerHTML = "<p>Failed to load your hostels.</p>";
  }
}

addHostelForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("hostelName").value.trim();
  const address = document.getElementById("hostelAddress").value.trim();
  const price = parseFloat(document.getElementById("hostelPrice").value);
  const type = document.getElementById("hostelType").value;
  const facilitiesStr = document.getElementById("hostelFacilities").value || "";
  const facilities = facilitiesStr.split(",").map((f) => f.trim()).filter(Boolean);

  try {
    const res = await fetch(`${API_BASE}/add_hostel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        address,
        price,
        type,
        facilities,
        owner_id: user.user_id,
        owner_email: user.email,
      }),
    });
    const result = await res.json();
    if (result.success) {
      notifySuccess("Hostel added!");
      addHostelForm.reset();
      fetchOwnerHostels();
    } else {
      notifyError("Failed to add hostel: " + (result.message || ""));
    }
  } catch (err) {
    console.error(err);
    notifyError("Server error adding hostel.");
  }
});

if (ownerListEl) fetchOwnerHostels();

// Show selected filename for the optional hostel photo field
const hostelImageInput = document.getElementById("hostelImage");
hostelImageInput?.addEventListener("change", () => {
  const nameEl = document.getElementById("hostelImageName");
  if (nameEl) nameEl.textContent = hostelImageInput.files[0]?.name || "";
});
