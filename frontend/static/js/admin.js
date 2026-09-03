// Global Image Lightbox Modal for Admin Dashboard
window.openAdminImageLightbox = function(src, caption) {
    let modal = document.getElementById("image-lightbox-modal");
    let img = document.getElementById("lightbox-img");
    let cap = document.getElementById("lightbox-caption");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "image-lightbox-modal";
        modal.style.cssText = "display:none; position:fixed; inset:0; z-index:999999; background:rgba(0,0,0,0.88); backdrop-filter:blur(8px); align-items:center; justify-content:center; padding:20px;";
        modal.innerHTML = `
            <div style="position:relative; max-width:90vw; max-height:90vh; display:flex; flex-direction:column; align-items:center;">
                <button id="close-lightbox-btn" onclick="window.closeAdminImageLightbox()" style="position:absolute; top:-45px; right:0; background:rgba(255,255,255,0.25); border:none; color:#ffffff; width:36px; height:36px; border-radius:50%; cursor:pointer; font-size:1.2rem; display:flex; align-items:center; justify-content:center;">
                    <i class="fa-solid fa-xmark"></i>
                </button>
                <div style="background:#ffffff; padding:16px; border-radius:16px; box-shadow:0 25px 50px -12px rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; max-height:80vh; max-width:80vw; overflow:hidden;">
                    <img id="lightbox-img" src="" alt="Product Image" style="max-width:100%; max-height:75vh; object-fit:contain; border-radius:8px;">
                </div>
                <div id="lightbox-caption" style="color:#ffffff; margin-top:14px; font-weight:600; font-size:1.05rem; text-align:center; text-shadow:0 2px 4px rgba(0,0,0,0.8);"></div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener("click", (e) => {
            if (e.target === modal) window.closeAdminImageLightbox();
        });
        img = document.getElementById("lightbox-img");
        cap = document.getElementById("lightbox-caption");
    }
    if (img) img.src = src;
    if (cap) cap.textContent = caption || "";
    modal.style.display = "flex";
};

window.closeAdminImageLightbox = function() {
    const modal = document.getElementById("image-lightbox-modal");
    const img = document.getElementById("lightbox-img");
    if (modal) modal.style.display = "none";
    if (img) img.src = "";
};

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") window.closeAdminImageLightbox();
});

// Admin Panel Controller Script
// Theme Toggle Logic
const currentTheme = localStorage.getItem("sales_ai_theme") || "dark";
if (currentTheme === "light") {
    document.body.setAttribute("data-theme", "light");
}
document.addEventListener("DOMContentLoaded", () => {
    const themeToggleBtn = document.getElementById("theme-toggle-btn");
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            if (document.body.getAttribute("data-theme") === "light") {
                document.body.removeAttribute("data-theme");
                localStorage.setItem("sales_ai_theme", "dark");
            } else {
                document.body.setAttribute("data-theme", "light");
                localStorage.setItem("sales_ai_theme", "light");
            }
        });
    }
});

// ─── Admin auth gate ────────────────────────────────────────────────────────
// The admin key is stored in localStorage on this machine only and sent as
// the X-Admin-Key header on every admin API call. This is a real deployed
// webapp (not a hosted Claude artifact), so localStorage is the right place
// for this — it's just gating access to *your own* admin dashboard.
const ADMIN_KEY_STORAGE = "salesai_admin_key";

function getAdminKey() {
    return localStorage.getItem(ADMIN_KEY_STORAGE) || "change-me-please";
}

function setAdminKey(key) {
    localStorage.setItem(ADMIN_KEY_STORAGE, key || "change-me-please");
}

async function adminFetch(url, options = {}) {
    const headers = Object.assign({}, options.headers || {}, { "X-Admin-Key": getAdminKey() });
    const res = await fetch(url, Object.assign({}, options, { headers }));
    if (res.status === 401) {
        showAdminLoginOverlay("Invalid key — try again.");
        throw new Error("Unauthorized");
    }
    return res;
}

function showAdminLoginOverlay(errorMsg) {
    const overlay = document.getElementById("admin-login-overlay");
    const errEl = document.getElementById("admin-login-error");
    overlay.style.display = "flex";
    if (errorMsg) {
        errEl.textContent = errorMsg;
        errEl.style.display = "block";
    } else {
        errEl.style.display = "none";
    }
}

function hideAdminLoginOverlay() {
    document.getElementById("admin-login-overlay").style.display = "none";
}

async function performAdminLogin(e) {
    if (e) e.preventDefault();
    const keyInput = document.getElementById("admin-key-input");
    const key = keyInput.value.trim();
    const submitBtn = document.getElementById("admin-login-submit");
    const errorEl = document.getElementById("admin-login-error");
    
    if (!key) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Verifying...";
    errorEl.style.display = "none";

    setAdminKey(key);

    try {
        const res = await fetch("/api/admin/leads", { headers: { "X-Admin-Key": key } });
        if (res.status === 401) {
            errorEl.textContent = "Invalid key — try again.";
            errorEl.style.display = "block";
            submitBtn.disabled = false;
            submitBtn.textContent = "Enter";
            keyInput.focus();
            return;
        }
        hideAdminLoginOverlay();
        fetchProducts();
        fetchAnalytics();
    } catch (err) {
        errorEl.textContent = "Could not reach the server.";
        errorEl.style.display = "block";
        submitBtn.disabled = false;
        submitBtn.textContent = "Enter";
    }
}

const adminLoginForm = document.getElementById("admin-login-form");
if (adminLoginForm) {
    adminLoginForm.addEventListener("submit", performAdminLogin);
} else {
    document.getElementById("admin-login-submit").addEventListener("click", performAdminLogin);
}

// If we already have a stored key, hide the gate optimistically; any 401
// from adminFetch will bring it back.
if (getAdminKey()) {
    hideAdminLoginOverlay();
} else {
    showAdminLoginOverlay();
}

// DOM Elements
const navTabs = document.querySelectorAll(".nav-tab");
const tabPanels = document.querySelectorAll(".tab-panel");

// Tables
const productsTableBody = document.getElementById("products-table-body");
const leadsTableBody = document.getElementById("leads-table-body");
const ordersTableBody = document.getElementById("orders-table-body");

// Initial Boot
function initDashboard() {
    fetchProducts();
    if (getAdminKey()) {
        fetchAnalytics();
        fetchLeads();
        fetchOrders();
    }
}

// Boot immediately on load
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDashboard);
} else {
    initDashboard();
}

// Searches
const productSearch = document.getElementById("product-search");
const leadSearch = document.getElementById("lead-search");
const orderSearch = document.getElementById("order-search");

// Modal Elements
const openModalBtn = document.getElementById("open-product-modal");
const closeModalBtn = document.getElementById("close-product-modal");
const productModal = document.getElementById("product-modal");
const addProductForm = document.getElementById("add-product-form");

// State Data Store
let productsData = [];
let leadsData = [];
let ordersData = [];

// --- Tab Switching Navigation ---
navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
        // Toggle tabs active state
        navTabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");

        // Toggle panel display
        const targetPanelId = tab.getAttribute("data-tab");
        tabPanels.forEach(panel => {
            if (panel.id === targetPanelId) {
                panel.classList.add("active");
            } else {
                panel.classList.remove("active");
            }
        });

        // Hide analytics strip when in WhatsApp messenger for maximum full screen space
        const analyticsStrip = document.querySelector(".analytics-strip");
        if (analyticsStrip) {
            if (targetPanelId === "whatsapp-tab") {
                analyticsStrip.style.display = "none";
            } else {
                analyticsStrip.style.display = "flex";
            }
        }

        // Trigger loading for active tab
        loadActiveTabData(targetPanelId);
    });
});

// Load data based on active tab
function loadActiveTabData(tabId) {
    if (tabId === "products-tab") {
        fetchProducts();
    } else if (tabId === "leads-tab") {
        fetchLeads();
    } else if (tabId === "pipeline-tab") {
        fetchLeads();
    } else if (tabId === "orders-tab") {
        fetchOrders();
    }
}

// Active Category State
let activeCategory = "all";
let inStockOnlyFilter = false;

// --- Fetch and Render Products ---
async function fetchProducts() {
    try {
        const res = await fetch("/api/products");
        productsData = await res.json();
        updateCategoryPillCounts();
        applyProductFiltersAndSort();
    } catch (e) {
        console.error("Error loading products:", e);
    }
}

function isMaintenanceProduct(p) {
    const cat = (p.category || "").toLowerCase();
    const name = (p.name || "").toLowerCase();
    return cat === "maintenance box" || name.includes("maintenance box") || name.includes("maintenance tank") || name.includes("waste ink") || name.includes("waste tank");
}

function isPrinterProduct(p) {
    if (isMaintenanceProduct(p) || isInkProduct(p) || isScannerProduct(p) || isPaperProduct(p)) {
        return false;
    }
    const cat = (p.category || "").toLowerCase();
    const name = (p.name || "").toLowerCase();
    return cat.includes("printer") || cat.includes("plotter") || name.includes("surecolor") || name.includes("workforce") || name.includes("citizen") || name.includes("plotter") || name.includes("printer");
}

function isScannerProduct(p) {
    const cat = (p.category || "").toLowerCase();
    const name = (p.name || "").toLowerCase();
    return cat.includes("scanner") || name.includes("scanner") || name.includes("perfection");
}

function isInkProduct(p) {
    if (isMaintenanceProduct(p)) {
        return false;
    }
    const cat = (p.category || "").toLowerCase();
    const name = (p.name || "").toLowerCase();
    return cat.includes("ink") || cat.includes("cartridge") || cat.includes("toner") || cat.includes("ribbon") ||
           name.includes("ink") || name.includes("cartridge") || name.includes("singlepack") || name.includes("ultrachrome") || name.includes("toner");
}

function isPaperProduct(p) {
    const cat = (p.category || "").toLowerCase();
    const name = (p.name || "").toLowerCase();
    return cat.includes("paper") || cat.includes("media") || name.includes("paper") || name.includes("canvas") || name.includes("roll");
}

function updateCategoryPillCounts() {
    const allCount = productsData.length;
    const printerCount = productsData.filter(isPrinterProduct).length;
    const scannerCount = productsData.filter(isScannerProduct).length;
    const inkCount = productsData.filter(isInkProduct).length;
    const maintenanceCount = productsData.filter(isMaintenanceProduct).length;
    const paperCount = productsData.filter(isPaperProduct).length;

    const elAll = document.getElementById("count-all");
    const elPrinters = document.getElementById("count-printers");
    const elScanners = document.getElementById("count-scanners");
    const elInks = document.getElementById("count-inks");
    const elMaintenance = document.getElementById("count-maintenance");
    const elPapers = document.getElementById("count-papers");

    if (elAll) elAll.textContent = allCount;
    if (elPrinters) elPrinters.textContent = printerCount;
    if (elScanners) elScanners.textContent = scannerCount;
    if (elInks) elInks.textContent = inkCount;
    if (elMaintenance) elMaintenance.textContent = maintenanceCount;
    if (elPapers) elPapers.textContent = paperCount;
}

let activeSubCategory = "all";

window.filterSubCategory = function(sub) {
    activeSubCategory = sub;
    const chips = document.querySelectorAll(".subcat-chip");
    chips.forEach(c => {
        if (c.getAttribute("data-sub") === sub) {
            c.classList.add("active");
            c.style.background = "rgba(255,255,255,0.08)";
            c.style.color = "var(--text-primary)";
        } else {
            c.classList.remove("active");
            c.style.background = "transparent";
            c.style.color = "var(--text-secondary)";
        }
    });
    applyProductFiltersAndSort();
};

function applyProductFiltersAndSort() {
    let filtered = [...productsData];

    // Primary Category Filter
    if (activeCategory === "Printers") {
        filtered = filtered.filter(isPrinterProduct);
    } else if (activeCategory === "Scanners") {
        filtered = filtered.filter(isScannerProduct);
    } else if (activeCategory === "Inks & Consumables") {
        filtered = filtered.filter(isInkProduct);
    } else if (activeCategory === "Maintenance Boxes") {
        filtered = filtered.filter(isMaintenanceProduct);
    } else if (activeCategory === "Papers & Media") {
        filtered = filtered.filter(isPaperProduct);
    }

    // Sub-Category Filter
    if (activeSubCategory !== "all") {
        if (activeSubCategory === "cad") {
            filtered = filtered.filter(p => {
                const n = p.name.toLowerCase();
                return n.includes("sc-t") || n.includes("t3100") || n.includes("t5100") || n.includes("t7700") || n.includes("t5700") || n.includes("t3700") || n.includes("t3200") || n.includes("t5200") || n.includes("cad") || n.includes("technical");
            });
        } else if (activeSubCategory === "fineart") {
            filtered = filtered.filter(p => {
                const n = p.name.toLowerCase();
                return n.includes("sc-p") || n.includes("p9500") || n.includes("p7500") || n.includes("p900") || n.includes("p700") || n.includes("p20000") || n.includes("p8500") || n.includes("p6500") || n.includes("p5300") || n.includes("fine art");
            });
        } else if (activeSubCategory === "office") {
            filtered = filtered.filter(p => {
                const n = p.name.toLowerCase();
                return n.includes("workforce") || n.includes("enterprise") || n.includes("wf-") || n.includes("am-c") || n.includes("em-c") || n.includes("office");
            });
        } else if (activeSubCategory === "photo") {
            filtered = filtered.filter(p => {
                const n = p.name.toLowerCase();
                return n.includes("citizen") || n.includes("cx-02") || n.includes("cy-02") || n.includes("cz-01") || n.includes("photo booth");
            });
        } else if (activeSubCategory === "maintenance") {
            filtered = filtered.filter(p => {
                const n = p.name.toLowerCase();
                return n.includes("maintenance box") || n.includes("waste") || (p.category === "Maintenance Box");
            });
        }
    }

    // In Stock Only Filter
    if (inStockOnlyFilter) {
        filtered = filtered.filter(p => (p.availability === "In Stock") || (p.stock > 0 && p.availability !== "Out of Stock"));
    }

    // Search Filter
    const searchInput = document.getElementById("product-search");
    if (searchInput && searchInput.value.trim()) {
        const query = searchInput.value.toLowerCase().trim();
        filtered = filtered.filter(p => 
            p._id.toLowerCase().includes(query) ||
            p.name.toLowerCase().includes(query) ||
            (p.category && p.category.toLowerCase().includes(query)) ||
            (p.tags && p.tags.some(t => t.toLowerCase().includes(query)))
        );
    }

    // Sort
    const sortSelect = document.getElementById("product-sort");
    if (sortSelect) {
        const sortVal = sortSelect.value;
        if (sortVal === "name-asc") {
            filtered.sort((a, b) => a.name.localeCompare(b.name));
        } else if (sortVal === "name-desc") {
            filtered.sort((a, b) => b.name.localeCompare(a.name));
        } else if (sortVal === "price-asc") {
            filtered.sort((a, b) => a.price - b.price);
        } else if (sortVal === "price-desc") {
            filtered.sort((a, b) => b.price - a.price);
        } else if (sortVal === "stock-desc") {
            filtered.sort((a, b) => b.stock - a.stock);
        } else if (sortVal === "availability") {
            filtered.sort((a, b) => {
                const aAvail = (a.availability === "In Stock") || (a.stock > 0);
                const bAvail = (b.availability === "In Stock") || (b.stock > 0);
                return bAvail - aAvail;
            });
        }
    }

    renderProducts(filtered);
}

// Category Pills Event Listeners Setup
function initProductFilters() {
    const catPills = document.querySelectorAll(".cat-pill");
    catPills.forEach(pill => {
        pill.addEventListener("click", () => {
            catPills.forEach(p => {
                p.classList.remove("active");
                p.style.background = "transparent";
                p.style.color = "var(--text-secondary)";
            });
            pill.classList.add("active");
            pill.style.background = "var(--header-bg)";
            pill.style.color = "var(--text-primary)";

            activeCategory = pill.getAttribute("data-cat");
            applyProductFiltersAndSort();
        });
    });

    const searchInput = document.getElementById("product-search");
    if (searchInput) {
        searchInput.addEventListener("input", applyProductFiltersAndSort);
    }

    const sortSelect = document.getElementById("product-sort");
    if (sortSelect) {
        sortSelect.addEventListener("change", applyProductFiltersAndSort);
    }

    const inStockBtn = document.getElementById("filter-instock-btn");
    if (inStockBtn) {
        inStockBtn.addEventListener("click", () => {
            inStockOnlyFilter = !inStockOnlyFilter;
            if (inStockOnlyFilter) {
                inStockBtn.style.background = "#10b981";
                inStockBtn.style.color = "#ffffff";
            } else {
                inStockBtn.style.background = "rgba(16, 185, 129, 0.12)";
                inStockBtn.style.color = "#10b981";
            }
            applyProductFiltersAndSort();
        });
    }
}

// Call on startup
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initProductFilters);
} else {
    initProductFilters();
}

// Consumables Drawer Functions
window.openConsumablesModal = function(printerId, printerName) {
    const modal = document.getElementById("consumables-modal");
    const titleEl = document.getElementById("consumables-modal-title");
    const subTitleEl = document.getElementById("consumables-modal-subtitle");
    const listBody = document.getElementById("consumables-list-body");

    const printer = productsData.find(p => p._id === printerId);
    if (!printer) return;

    titleEl.innerHTML = `<i class="fa-solid fa-droplet" style="color: #ec4899;"></i> Linked Consumables for ${printer.name}`;
    subTitleEl.textContent = `Model SKU: ${printer._id} • ${printer.consumables ? printer.consumables.length : 0} matching supplies`;

    listBody.innerHTML = "";

    if (!printer.consumables || printer.consumables.length === 0) {
        listBody.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 24px; color: var(--text-secondary);">No linked consumables found for this model.</div>`;
    } else {
        printer.consumables.forEach(cId => {
            const item = productsData.find(p => p._id === cId);
            if (item) {
                const card = document.createElement("div");
                card.style.cssText = "background: var(--inner-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 6px; transition: all 0.2s;";
                card.innerHTML = `
                    <div style="font-weight: 700; font-size: 0.86rem; color: var(--text-primary);">${item.name}</div>
                    <div style="font-family: monospace; font-size: 0.76rem; color: var(--text-muted);">${item._id}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 8px;">
                        <span style="font-weight: 700; color: var(--accent-cyan); font-size: 0.88rem;">${item.price.toFixed(2)} AED</span>
                        <span style="font-size: 0.72rem; font-weight: 600; color: ${item.stock > 0 ? '#10b981' : '#ef4444'};">${item.stock > 0 ? '🟢 In Stock (' + item.stock + ')' : '🔴 Out of Stock'}</span>
                    </div>
                    <button type="button" onclick="adminSendProductToActiveChat('${item._id}')" style="margin-top: 6px; padding: 6px 10px; background: rgba(0, 168, 132, 0.15); color: #00a884; border: 1px solid rgba(0, 168, 132, 0.35); border-radius: 6px; font-size: 0.76rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 5px;">
                        <i class="fa-solid fa-paper-plane"></i> Send to Chat
                    </button>
                `;
                listBody.appendChild(card);
            }
        });
    }

    modal.style.display = "flex";
};

window.closeConsumablesModal = function() {
    const modal = document.getElementById("consumables-modal");
    if (modal) modal.style.display = "none";
};

// Generate rich markdown card for any product
function buildProductCardBlock(prod) {
    const isAvail = (prod.availability === "In Stock") || (prod.stock > 0 && prod.availability !== "Out of Stock");
    const availText = isAvail ? (prod.stock > 0 ? `🟢 In Stock (${prod.stock} pcs)` : '🟢 In Stock') : '🔴 Out of Stock';
    const webUrl = prod.website_url || `https://www.keplertechllc.com/?s=${encodeURIComponent(prod._id || prod.name)}&post_type=product`;
    
    return `━━━━━━━━━━━━━━━━━━━━\n📦 *${prod.name}*\n💵 *Price:* ${prod.price.toFixed(2)} AED\n📊 *Availability:* ${availText}\n📝 *Description:* ${prod.description || 'Genuine OEM printing equipment / supply.'}\n🔗 *Website:* ${webUrl}\n🆔 *Product ID:* \`${prod._id}\`\n[Draft: ${prod._id}]\n━━━━━━━━━━━━━━━━━━━━`;
}

// 1-Click Send Product to Active WhatsApp/Web Chat
window.adminSendProductToActiveChat = async function(prodId) {
    const prod = productsData.find(p => p._id === prodId);
    if (!prod) return;

    if (!activeWhatsAppSessionId) {
        // Switch to Live Chats tab and alert
        const chatTabBtn = document.querySelector('[data-tab="whatsapp-tab"]');
        if (chatTabBtn) chatTabBtn.click();
        alert("Please select a customer chat from the list on the left first to send this product.");
        return;
    }

    const cardBlock = buildProductCardBlock(prod);

    try {
        const res = await adminFetch(`/api/admin/chats/${activeWhatsAppSessionId}/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: cardBlock })
        });
        const data = await res.json();
        if (data.status === "success") {
            // Close any open modals
            closeAdminProductPickerModal();
            closeConsumablesModal();
            // Switch to chat tab if not already on it
            const chatTabBtn = document.querySelector('[data-tab="whatsapp-tab"]');
            if (chatTabBtn && !chatTabBtn.classList.contains("active")) {
                chatTabBtn.click();
            }
            await loadWhatsAppChat({ session_id: activeWhatsAppSessionId });
            await fetchWhatsAppChats();
        } else {
            alert("Failed to send product to chat: " + (data.error || "Unknown error"));
        }
    } catch (err) {
        console.error("Error sending product:", err);
        alert("Failed to send product to active chat.");
    }
};

// Copy Formatted Product Card to Clipboard
window.copyProductCard = function(prodId) {
    const prod = productsData.find(p => p._id === prodId);
    if (!prod) return;
    const cardBlock = buildProductCardBlock(prod);
    navigator.clipboard.writeText(cardBlock).then(() => {
        alert(`Copied product card for "${prod.name}" to clipboard!`);
    }).catch(err => {
        console.error("Clipboard copy failed:", err);
    });
};

function renderProducts(products) {
    productsTableBody.innerHTML = "";
    if (products.length === 0) {
        productsTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-secondary); padding: 20px;">No products found matching active filter.</td></tr>`;
        return;
    }

    products.forEach(prod => {
        const tr = document.createElement("tr");
        
        let imgUrl = prod.image_url;
        if (!imgUrl) {
            const nameL = prod.name.toLowerCase();
            if (nameL.includes("citizen") || nameL.includes("cx-02") || nameL.includes("cz-01")) {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2023/03/Citizen-CX-02-Photo-Printer-Dubai.webp";
            } else if (nameL.includes("p9500") || nameL.includes("p7500") || nameL.includes("p9000") || nameL.includes("p20000") || nameL.includes("sc-p")) {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2023/05/Epson-P9500-Spectro.webp";
            } else if (nameL.includes("ink") || nameL.includes("cartridge") || nameL.includes("singlepack") || nameL.includes("ultrachrome")) {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2018/04/Ink-300x300.jpg";
            } else if (nameL.includes("paper") || nameL.includes("canvas") || nameL.includes("roll")) {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2023/06/Innova-Decor-Smooth-Art-DS-IFA-25.webp";
            } else {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2023/05/Large-Format-Printer.webp";
            }
        }

        const isAvailable = (prod.availability === "In Stock") || (prod.stock > 0 && prod.availability !== "Out of Stock");
        const availBadge = isAvailable
            ? `<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 0.74rem; font-weight: 700; padding: 2px 7px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-circle-check"></i> In Stock</span>`
            : `<span style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); font-size: 0.74rem; font-weight: 700; padding: 2px 7px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-circle-xmark"></i> Out of Stock</span>`;

        // Category Badge Color
        let catBadgeColor = "#3b82f6";
        let catBg = "rgba(59, 130, 246, 0.12)";
        if (prod.category === "Inks & Consumables") {
            catBadgeColor = "#ec4899";
            catBg = "rgba(236, 72, 153, 0.12)";
        } else if (prod.category === "Papers & Media") {
            catBadgeColor = "#f59e0b";
            catBg = "rgba(245, 158, 11, 0.12)";
        } else if (prod.category === "Scanners") {
            catBadgeColor = "#8b5cf6";
            catBg = "rgba(139, 92, 246, 0.12)";
        }

        const categoryBadge = `<span style="background: ${catBg}; color: ${catBadgeColor}; border: 1px solid ${catBadgeColor}33; font-size: 0.73rem; font-weight: 700; padding: 2px 7px; border-radius: 6px; white-space: nowrap;">${prod.category || 'Supplies'}</span>`;

        // Linked Consumables Button for Printers
        let consumablesHtml = `<span style="color: var(--text-muted); font-size: 0.78rem;">—</span>`;
        if (prod.consumables && prod.consumables.length > 0) {
            consumablesHtml = `
                <button type="button" onclick="openConsumablesModal('${prod._id}', '${prod.name.replace(/'/g, "\\'")}')" style="background: rgba(236, 72, 153, 0.15); color: #ec4899; border: 1px solid rgba(236, 72, 153, 0.35); padding: 4px 9px; border-radius: 6px; font-size: 0.74rem; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; transition: all 0.2s;" onmouseover="this.style.background='#ec4899'; this.style.color='#fff';" onmouseout="this.style.background='rgba(236, 72, 153, 0.15)'; this.style.color='#ec4899';">
                    <i class="fa-solid fa-droplet"></i> ${prod.consumables.length} Supplies
                </button>
            `;
        }

        tr.innerHTML = `
            <td style="width: 55px; text-align: center; vertical-align: middle;">
                <div onclick="openAdminImageLightbox('${imgUrl}', '${prod.name.replace(/'/g, "\\'")}')" style="width: 44px; height: 44px; border-radius: 8px; overflow: hidden; background: #ffffff; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-color); padding: 2px; cursor: pointer; transition: transform 0.2s ease;" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'" title="Click to view large photo">
                    <img src="${imgUrl}" alt="${prod.name}" style="max-width: 100%; max-height: 100%; object-fit: contain; pointer-events: none;">
                </div>
            </td>
            <td style="font-family: monospace; font-weight: 600; font-size: 0.8rem; color: var(--text-primary);">${prod._id}</td>
            <td style="font-weight: 500;">
                <div style="display: flex; flex-direction: column; gap: 2px;">
                    <div style="display: inline-flex; align-items: center; gap: 6px;">
                        <span style="font-weight: 600; font-size: 0.88rem; color: var(--text-primary);">${prod.name}</span>
                        <a href="${prod.website_url || ('https://www.keplertechllc.com/product/' + encodeURIComponent(prod.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')) + '/')}" target="_blank" rel="noopener noreferrer" style="color: #3b82f6; background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 4px; padding: 2px 5px; font-size: 0.72rem; display: inline-flex; align-items: center; gap: 3px; text-decoration: none; cursor: pointer;" title="Open live Kepler product page">
                            <i class="fa-solid fa-arrow-up-right-from-square"></i>
                        </a>
                    </div>
                    <span style="font-size: 0.72rem; color: var(--text-muted); line-height: 1.25; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;">${prod.description || ''}</span>
                </div>
            </td>
            <td>${categoryBadge}</td>
            <td style="font-weight: 700; color: var(--accent-cyan); font-size: 0.86rem;">${prod.price.toFixed(2)} AED</td>
            <td>${availBadge}</td>
            <td>${consumablesHtml}</td>
            <td style="text-align: center;">
                <div style="display: flex; gap: 5px; justify-content: center; align-items: center;">
                    <button type="button" onclick="adminSendProductToActiveChat('${prod._id}')" style="background: rgba(0, 168, 132, 0.15); color: #00a884; border: 1px solid rgba(0, 168, 132, 0.35); padding: 5px 10px; border-radius: 6px; font-size: 0.74rem; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; transition: all 0.2s;" onmouseover="this.style.background='#00a884'; this.style.color='#fff';" onmouseout="this.style.background='rgba(0, 168, 132, 0.15)'; this.style.color='#00a884';" title="Send Product Card to active chat">
                        <i class="fa-solid fa-paper-plane"></i> Send
                    </button>
                    <button type="button" onclick="copyProductCard('${prod._id}')" style="background: rgba(255,255,255,0.06); color: var(--text-secondary); border: 1px solid var(--border-color); padding: 5px 8px; border-radius: 6px; font-size: 0.74rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" title="Copy formatted product block">
                        <i class="fa-regular fa-copy"></i>
                    </button>
                </div>
            </td>
        `;
        productsTableBody.appendChild(tr);
    });
}

// Inline quick adjustments (updates display only, user clicks Save to submit)
function adjustStockInline(prodId, delta) {
    const input = document.querySelector(`.stock-input[data-id="${prodId}"]`);
    let val = parseInt(input.value) || 0;
    val += delta;
    if (val < 0) val = 0;
    input.value = val;
}

// Save Stock PUT Request
async function saveStockLevel(prodId, stock, buttonEl) {
    const originalText = buttonEl.textContent;
    buttonEl.disabled = true;
    buttonEl.textContent = "Saving...";
    try {
        const res = await adminFetch(`/api/admin/products/${prodId}/stock`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stock: parseInt(stock) })
        });
        const result = await res.json();
        if (result.status === "success") {
            console.log(`Stock for ${prodId} updated to ${stock}`);
            buttonEl.textContent = "Saved!";
            buttonEl.style.background = "#10b981"; // green success
            setTimeout(() => {
                buttonEl.textContent = "Save";
                buttonEl.style.background = ""; // restore default
                buttonEl.disabled = false;
            }, 1000);
        } else {
            alert("Error updating stock: " + result.error);
            buttonEl.textContent = "Save";
            buttonEl.disabled = false;
        }
    } catch (e) {
        console.error(e);
        buttonEl.textContent = "Save";
        buttonEl.disabled = false;
    }
}

// --- Fetch and Render Leads ---
async function fetchLeads() {
    try {
        const res = await adminFetch("/api/admin/leads");
        leadsData = await res.json();
        renderLeads(leadsData);
    } catch (e) {
        console.error("Error loading leads:", e);
    }
}

function renderLeads(leads) {
    // Render CRM table leads
    leadsTableBody.innerHTML = "";
    if (leads.length === 0) {
        leadsTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">No leads found.</td></tr>`;
    } else {
        leads.forEach(lead => {
            const tr = document.createElement("tr");
            const formattedDate = lead.updated_at ? new Date(lead.updated_at).toLocaleDateString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) : "N/A";
            tr.innerHTML = `
                <td style="font-weight: 600; color: var(--text-primary);">${lead.name || '<span style="color: var(--text-muted); font-style: italic;">Not Provided</span>'}</td>
                <td style="font-family: monospace; font-size: 0.82rem;">${lead.contact || '<span style="color: var(--text-muted); font-style: italic;">Not Provided</span>'}</td>
                <td style="max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-secondary);">${lead.needs || '<span style="color: var(--text-muted); font-style: italic;">Not Analyzed</span>'}</td>
                <td style="font-weight: 600; color: var(--wa-teal);">${lead.budget || '<span style="color: var(--text-muted); font-style: italic;">Not Set</span>'}</td>
                <td><span class="status-badge ${lead.status}">${lead.status}</span></td>
                <td style="font-size: 0.78rem; color: var(--text-secondary); white-space: nowrap;">${formattedDate}</td>
                <td>
                    <button class="btn btn-secondary view-transcript-btn" data-session="${lead.session_id}" style="padding: 4px 10px; font-size: 0.76rem; border-radius: 6px;">
                        <i class="fa-solid fa-comment-dots"></i> View
                    </button>
                </td>
            `;
            leadsTableBody.appendChild(tr);
        });

        document.querySelectorAll(".view-transcript-btn").forEach(btn => {
            btn.addEventListener("click", () => openTranscript(btn.getAttribute("data-session")));
        });
    }

    // Render Pipeline Kanban Board
    renderPipeline(leads);
}

function renderPipeline(leads) {
    const colNew = document.getElementById("cards-new");
    const colContacted = document.getElementById("cards-contacted");
    const colQualified = document.getElementById("cards-qualified");
    const colWon = document.getElementById("cards-won");
    const colLost = document.getElementById("cards-lost");

    if (!colNew) return; // Not on pipeline panel page

    colNew.innerHTML = "";
    colContacted.innerHTML = "";
    colQualified.innerHTML = "";
    colWon.innerHTML = "";
    colLost.innerHTML = "";

    const counts = { new: 0, contacted: 0, qualified: 0, won: 0, lost: 0 };

    leads.forEach(lead => {
        let status = lead.status || "new";
        if (status === "prospect") status = "new";
        if (!counts.hasOwnProperty(status)) status = "new";

        counts[status]++;

        const card = document.createElement("div");
        card.className = "kanban-card";
        card.id = `card-${lead.session_id}`;
        card.draggable = true;
        card.ondragstart = window.drag;

        const score = lead.score || 0;
        let scoreClass = "";
        if (score >= 30) scoreClass = "hot";
        else if (score >= 15) scoreClass = "warm";

        card.innerHTML = `
            <div class="kanban-card-title">${lead.name || lead.session_id}</div>
            <div class="kanban-card-meta">${lead.contact || 'No Contact'}</div>
            <div class="kanban-card-meta" style="font-style: italic; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${lead.needs || 'No needs info'}</div>
            <div class="kanban-card-footer">
                <span class="score-badge ${scoreClass}">Score: ${score}</span>
                <div class="stage-actions" style="display: flex; gap: 6px; align-items: center;">
                    <button onclick="window.openTranscript('${lead.session_id}')" class="btn-stage" style="padding: 2px 5px; font-size: 0.7rem; border-radius: 4px; border: 1px solid var(--glass-border); background: rgba(255,255,255,0.05); color: white; cursor: pointer;">
                        <i class="fa-solid fa-comments"></i> Chat
                    </button>
                    <select onchange="window.updateLeadStage('${lead.session_id}', this.value)" class="btn-stage" style="background:#1a1a26; color:white; border:none; padding:2px; font-size:0.75rem;">
                        <option value="new" ${status === 'new' ? 'selected' : ''}>New</option>
                        <option value="contacted" ${status === 'contacted' ? 'selected' : ''}>Contacted</option>
                        <option value="qualified" ${status === 'qualified' ? 'selected' : ''}>Qualified</option>
                        <option value="won" ${status === 'won' ? 'selected' : ''}>Won</option>
                        <option value="lost" ${status === 'lost' ? 'selected' : ''}>Lost</option>
                    </select>
                </div>
            </div>
        `;

        if (status === "new") colNew.appendChild(card);
        else if (status === "contacted") colContacted.appendChild(card);
        else if (status === "qualified") colQualified.appendChild(card);
        else if (status === "won") colWon.appendChild(card);
        else if (status === "lost") colLost.appendChild(card);
    });

    // Update Kanban headers counts
    document.getElementById("count-new").textContent = counts.new;
    document.getElementById("count-contacted").textContent = counts.contacted;
    document.getElementById("count-qualified").textContent = counts.qualified;
    document.getElementById("count-won").textContent = counts.won;
    document.getElementById("count-lost").textContent = counts.lost;
}

// Drag & Drop global hooks
window.allowDrop = function(ev) {
    ev.preventDefault();
}

window.drag = function(ev) {
    ev.dataTransfer.setData("text", ev.target.id);
}

window.drop = async function(ev, stage) {
    ev.preventDefault();
    const data = ev.dataTransfer.getData("text");
    const leadSessionId = data.replace("card-", "");
    window.updateLeadStage(leadSessionId, stage);
}

window.updateLeadStage = async function(leadSessionId, stage) {
    try {
        const res = await adminFetch(`/api/admin/leads/${leadSessionId}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: stage })
        });
        const result = await res.json();
        if (result.status === "success") {
            fetchLeads();
        } else {
            alert("Error updating status: " + result.error);
        }
    } catch(e) {
        console.error("Pipeline update failed:", e);
    }
}

// --- Fetch and Render Orders ---
async function fetchOrders() {
    try {
        const res = await adminFetch("/api/admin/orders");
        ordersData = await res.json();
        renderOrders(ordersData);
    } catch (e) {
        console.error("Error loading orders:", e);
    }
}

function renderOrders(orders) {
    ordersTableBody.innerHTML = "";
    if (orders.length === 0) {
        ordersTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">No orders logged.</td></tr>`;
        return;
    }

    orders.forEach(order => {
        const tr = document.createElement("tr");
        const formattedDate = order.created_at ? new Date(order.created_at).toLocaleDateString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) : "N/A";
        
        // Render items breakdown
        const itemsList = order.items.map(item => `${item.name} (x${item.quantity})`).join(", ");

        const isPaid = order.payment_status === "paid";
        const toggleStatus = isPaid ? "unpaid" : "paid";
        const buttonText = isPaid ? "Mark Unpaid" : "Mark Paid";
        const buttonBg = isPaid ? "rgba(239, 68, 68, 0.15)" : "rgba(0, 168, 132, 0.15)";
        const buttonColor = isPaid ? "#f87171" : "var(--wa-teal)";
        const buttonBorder = isPaid ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid rgba(0, 168, 132, 0.3)";

        tr.innerHTML = `
            <td style="font-family: monospace; font-weight: 600; font-size: 0.82rem; color: var(--wa-teal);">${order._id}</td>
            <td style="font-weight: 600; color: var(--text-primary);">${order.customer_name || 'Customer'}</td>
            <td style="font-family: monospace; font-size: 0.82rem;">${order.customer_contact || '—'}</td>
            <td style="font-size: 0.82rem; max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-secondary);" title="${itemsList}">${itemsList}</td>
            <td style="font-weight: 700; color: var(--wa-teal);">${order.total_amount.toFixed(2)} AED</td>
            <td><span class="status-badge ${order.payment_status}">${order.payment_status}</span></td>
            <td style="font-size: 0.78rem; color: var(--text-secondary); white-space: nowrap;">${formattedDate}</td>
            <td>
                <button class="btn toggle-payment-btn" data-id="${order._id}" data-status="${toggleStatus}" style="padding: 4px 10px; font-size: 0.76rem; border-radius: 6px; background: ${buttonBg}; color: ${buttonColor}; border: ${buttonBorder}; cursor: pointer; font-weight: 600;">
                    ${buttonText}
                </button>
            </td>
        `;
        ordersTableBody.appendChild(tr);
    });

    // Add click listeners to toggle payment buttons
    document.querySelectorAll(".toggle-payment-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const orderId = btn.getAttribute("data-id");
            const newStatus = btn.getAttribute("data-status");
            togglePaymentStatus(orderId, newStatus, btn);
        });
    });
}

async function togglePaymentStatus(orderId, newStatus, btn) {
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = "Updating...";
    try {
        const res = await adminFetch(`/api/admin/orders/${orderId}/payment`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ payment_status: newStatus })
        });
        const result = await res.json();
        if (result.status === "success") {
            fetchOrders(); // Refresh table
        } else {
            alert("Error updating order payment status: " + result.error);
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (e) {
        console.error(e);
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// --- Add Product Modal Handlers ---
if (openModalBtn) {
    openModalBtn.addEventListener("click", () => {
        productModal.classList.add("active");
    });
}

closeModalBtn.addEventListener("click", () => {
    productModal.classList.remove("active");
    addProductForm.reset();
});

// Submit add product form
addProductForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const prodIdVal = document.getElementById("prod-id").value.trim();
    const nameVal = document.getElementById("prod-name").value.trim();
    const priceVal = parseFloat(document.getElementById("prod-price").value);
    const stockVal = parseInt(document.getElementById("prod-stock").value);
    const descVal = document.getElementById("prod-desc").value.trim();
    const tagsVal = document.getElementById("prod-tags").value.split(",").map(t => t.trim()).filter(t => t.length > 0);

    const payload = {
        name: nameVal,
        price: priceVal,
        stock: stockVal,
        description: descVal,
        tags: tagsVal
    };
    if (prodIdVal) {
        payload.product_id = prodIdVal;
    }

    try {
        const res = await adminFetch("/api/admin/products", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        
        if (result.status === "success") {
            productModal.classList.remove("active");
            addProductForm.reset();
            fetchProducts(); // Reload products catalog tab
        } else {
            alert("Error adding product: " + result.error);
        }
    } catch (err) {
        console.error("Add product error:", err);
    }
});

// Apply product filters logic is defined above and handles activeCategory + search + sorting correctly.

leadSearch.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = leadsData.filter(l => 
        (l.name && l.name.toLowerCase().includes(q)) || 
        (l.contact && l.contact.toLowerCase().includes(q)) ||
        (l.needs && l.needs.toLowerCase().includes(q))
    );
    renderLeads(filtered);
});

orderSearch.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = ordersData.filter(o => 
        o.customer_name.toLowerCase().includes(q) || 
        o._id.toLowerCase().includes(q) || 
        o.customer_contact.toLowerCase().includes(q)
    );
    renderOrders(filtered);
});

// Initial load
fetchProducts();

// ─── Analytics ──────────────────────────────────────────────────────────────

async function fetchAnalytics() {
    try {
        const res = await adminFetch("/api/admin/analytics");
        const data = await res.json();

        document.getElementById("stat-leads").textContent = data.leads.total;
        document.getElementById("stat-qualified").textContent = data.leads.qualified;
        document.getElementById("stat-orders").textContent = data.orders.total;
        document.getElementById("stat-paid").textContent = data.orders.paid;
        document.getElementById("stat-revenue").textContent = `${data.revenue.collected.toFixed(0)} ${data.revenue.currency}`;
        document.getElementById("stat-conversion").textContent = `${data.conversion_rate_percent}%`;
        document.getElementById("stat-pending-revenue").textContent = `${data.revenue.pending.toFixed(0)} ${data.revenue.currency}`;
        if (data.products) {
            document.getElementById("stat-products").textContent = data.products.total;
            document.getElementById("stat-item-groups").textContent = data.products.item_groups;
        }
    } catch (e) {
        console.error("Analytics fetch error:", e);
    }
}

if (getAdminKey()) {
    fetchAnalytics();
}
setInterval(() => { if (getAdminKey()) fetchAnalytics(); }, 30000); // Auto-refresh every 30s

// ─── Transcript Modal ────────────────────────────────────────────────────────

async function openTranscript(sessionId) {
    const modal = document.getElementById("transcript-modal");
    const container = document.getElementById("transcript-messages");
    container.innerHTML = `<p style="color: var(--text-secondary); text-align: center;">Loading transcript...</p>`;
    modal.classList.add("active");

    try {
        const res = await adminFetch(`/api/chat/${sessionId}`);
        const data = await res.json();
        const messages = data.messages || [];

        if (messages.length === 0) {
            container.innerHTML = `<p style="color: var(--text-secondary); text-align: center;">No messages in this session.</p>`;
            return;
        }

        container.innerHTML = "";
        messages.forEach(msg => {
            if (!msg.content) return;
            const div = document.createElement("div");
            div.className = `transcript-msg ${msg.role}`;
            div.innerHTML = `<div class="transcript-bubble">${msg.content}</div>`;
            container.appendChild(div);
        });

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        container.innerHTML = `<p style="color: #ef4444; text-align: center;">Failed to load transcript.</p>`;
    }
}

document.getElementById("close-transcript").addEventListener("click", () => {
    document.getElementById("transcript-modal").classList.remove("active");
});

document.getElementById("transcript-modal").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) {
        e.currentTarget.classList.remove("active");
    }
});

window.openTranscript = openTranscript;

// ─── Live WhatsApp Messenger (Authentic WhatsApp Web & Voice Recording) ──────────────────
let activeWhatsAppSessionId = null;
let allWhatsAppChatsData = [];

// Helper to format WhatsApp markdown and rich product blocks for admin viewer
function formatWhatsAppText(text) {
    if (!text) return "";

    // Strip internal brackets like [Draft: SKU] and role tags like 'assistant'
    let cleaned = text
        .replace(/^(?:assistant|system|bot)\s*[:\n\-]+\s*/i, "")
        .replace(/\[Draft:\s*[^\]]+\]/gi, "")
        .trim();

    // Check if the message contains one or more product card blocks
    if (cleaned.includes("━━━━━━━━━━━━━━━━━━━━") || (cleaned.includes("📦") && (cleaned.includes("Price:") || cleaned.includes("Availability:")))) {
        const blocks = cleaned.split("━━━━━━━━━━━━━━━━━━━━").map(b => b.trim()).filter(b => b.length > 0);
        let introText = "";
        let cardItemsHtml = "";

        for (const block of blocks) {
            if (!block.includes("📦")) {
                introText += `<div style="margin-bottom: 8px;">${formatStandardMarkdown(block)}</div>`;
                continue;
            }

            const nameMatch = block.match(/📦\s*\*?([^\n\*]+)\*?/);
            const priceMatch = block.match(/💵\s*\*?Price:\*?\s*([^\n]+)/i);
            const availMatch = block.match(/📊\s*\*?Availability:\*?\s*([^\n]+)/i);
            const descMatch = block.match(/📝\s*\*?Description:\*?\s*([^\n]+)/i);
            const webMatch = block.match(/🔗\s*\*?Website:\*?\s*([^\n\s]+)/i);
            const idMatch = block.match(/(?:Product ID|ID):\*?\s*`?([A-Za-z0-9\-]+)`?/i);
            const scoreMatch = block.match(/🎯\s*\*?Match Satisfaction:\s*([^\n\*]+)\*?/i);

            const prodName = nameMatch ? nameMatch[1].trim() : "Kepler Product";
            const prodPrice = priceMatch ? priceMatch[1].trim() : "";
            const prodAvail = availMatch ? availMatch[1].trim() : "🟢 In Stock";
            const prodDesc = descMatch ? descMatch[1].trim() : "";
            const prodId = idMatch ? idMatch[1].trim() : "";
            const prodWeb = webMatch ? webMatch[1].trim() : "https://www.keplertechllc.com/";
            const matchScore = scoreMatch ? scoreMatch[1].trim() : "";

            // Find matching product image from catalog if available
            let prodImg = "";
            const nameClean = prodName.toLowerCase();
            const found = (productsData || []).find(p => 
                p._id === prodId || 
                (p.sku && p.sku === prodId) || 
                p.name.toLowerCase() === nameClean ||
                p.name.toLowerCase().includes(nameClean) ||
                nameClean.includes(p.name.toLowerCase())
            );
            
            if (found && found.image_url) {
                prodImg = found.image_url;
            } else {
                if (nameClean.includes("citizen") || nameClean.includes("cx-02") || nameClean.includes("cz-01")) {
                    prodImg = "https://www.keplertechllc.com/wp-content/uploads/2023/03/Citizen-CX-02-Photo-Printer-Dubai.webp";
                } else if (nameClean.includes("p9500") || nameClean.includes("p7500") || nameClean.includes("p9000") || nameClean.includes("p20000") || nameClean.includes("sc-p")) {
                    prodImg = "https://www.keplertechllc.com/wp-content/uploads/2023/05/Epson-P9500-Spectro.webp";
                } else if (nameClean.includes("wf-c87") || nameClean.includes("c878") || nameClean.includes("c879") || nameClean.includes("workforce") || nameClean.includes("enterprise")) {
                    prodImg = "https://www.keplertechllc.com/wp-content/uploads/2023/05/Business-Printers.webp";
                } else if (nameClean.includes("printer") || nameClean.includes("plotter")) {
                    prodImg = "https://www.keplertechllc.com/wp-content/uploads/2023/05/Large-Format-Printer.webp";
                } else if (nameClean.includes("ink") || nameClean.includes("cartridge") || nameClean.includes("singlepack") || nameClean.includes("ultrachrome")) {
                    prodImg = "https://www.keplertechllc.com/wp-content/uploads/2018/04/Ink-300x300.jpg";
                } else if (nameClean.includes("paper") || nameClean.includes("canvas") || nameClean.includes("roll")) {
                    prodImg = "https://www.keplertechllc.com/wp-content/uploads/2023/06/Innova-Decor-Smooth-Art-DS-IFA-25.webp";
                } else if (nameClean.includes("scanner")) {
                    prodImg = "https://www.keplertechllc.com/wp-content/uploads/2018/04/Epson-Business-Scanners.webp";
                } else {
                    prodImg = "https://www.keplertechllc.com/wp-content/uploads/2023/05/citizen-consumables.webp";
                }
            }

            let brandTag = "Genuine OEM";
            if (found && found.category) {
                brandTag = found.category;
            } else if (nameClean.includes("epson") || nameClean.includes("ultrachrome") || nameClean.includes("surecolor")) {
                brandTag = "Epson OEM";
            } else if (nameClean.includes("citizen")) {
                brandTag = "Citizen Media";
            } else if (nameClean.includes("innova")) {
                brandTag = "Innova Art";
            }

            cardItemsHtml += `
                <div style="flex: 0 0 210px; width: 210px; background: rgba(0, 0, 0, 0.28); border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.2); display: flex; flex-direction: column;">
                    <div style="width: 100%; height: 95px; background: #ffffff; display: flex; align-items: center; justify-content: center; padding: 4px; position: relative;">
                        <img src="${prodImg}" alt="${prodName}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                        <span style="position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.72); color: #fff; font-size: 0.6rem; padding: 1px 4px; border-radius: 3px; font-weight: 600;">${prodAvail}</span>
                        ${matchScore ? `<span style="position: absolute; top: 4px; left: 4px; background: #10b981; color: #fff; font-size: 0.6rem; padding: 1px 4px; border-radius: 3px; font-weight: 700;">🎯 ${matchScore}</span>` : ''}
                    </div>
                    <div style="padding: 8px; display: flex; flex-direction: column; flex: 1;">
                        <h4 style="margin: 0 0 4px 0; font-size: 0.8rem; color: #53bdeb; font-weight: 700; line-height: 1.25; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${prodName}">${prodName}</h4>
                        ${prodDesc ? `<p style="margin: 0 0 6px 0; font-size: 0.7rem; color: rgba(233,237,239,0.8); line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${prodDesc}">${prodDesc}</p>` : ''}
                        <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 6px; border-top: 1px dashed rgba(255,255,255,0.1); font-size: 0.78rem; margin-top: auto;">
                            <span style="font-size: 0.68rem; color: #53bdeb; font-weight: 700; background: rgba(83,189,235,0.15); padding: 1px 5px; border-radius: 3px;">🏷️ ${brandTag}</span>
                            <a href="${prodWeb}" target="_blank" style="display: inline-flex; align-items: center; gap: 3px; font-size: 0.68rem; color: #53bdeb; text-decoration: none; padding: 2px 6px; border-radius: 4px; background: rgba(83,189,235,0.15); font-weight: 600;">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i> Web
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }

        return `
            ${introText}
            ${cardItemsHtml ? `<div style="display: flex; overflow-x: auto; gap: 8px; padding-bottom: 6px; -webkit-overflow-scrolling: touch;">${cardItemsHtml}</div>` : ''}
        `;
    }

    return formatStandardMarkdown(cleaned);
}

function formatStandardMarkdown(text) {
    if (!text) return "";
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    
    // Bold **text** or *text*
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');
    // Italic _text_
    html = html.replace(/_(.*?)_/g, '<em>$1</em>');
    // Code `text`
    html = html.replace(/`(.*?)`/g, '<code style="background: rgba(0,0,0,0.25); padding: 2px 5px; border-radius: 4px; font-size: 0.85em;">$1</code>');
    // URLs
    html = html.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" style="color: #53bdeb; text-decoration: underline;">$1</a>');
    
    // Format [Options: Choice 1 | Choice 2] -> Visual Pills
    html = html.replace(/\[(?:Options:\s*)?([^\[\]|]{2,}(?:\s*\|\s*[^\[\]|]{2,})+)\]/g, (match, optsStr) => {
        const opts = optsStr.split("|").map(o => o.trim()).filter(o => o.length > 0);
        const pills = opts.map(opt => `
            <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.35); padding: 3px 10px; border-radius: 14px; font-size: 0.75rem; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
                <i class="fa-solid fa-arrow-right-long" style="font-size: 0.68rem;"></i> ${opt}
            </span>
        `).join(" ");
        return `<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;">${pills}</div>`;
    });

    // Line breaks
    html = html.replace(/\n/g, '<br>');
    return html;
}

let lastRenderedChatListHash = "";

async function fetchWhatsAppChats(isBackground = false) {
    try {
        const res = await adminFetch("/api/admin/chats");
        const chats = await res.json();
        allWhatsAppChatsData = chats;

        const countEl = document.getElementById("whatsapp-sessions-count");
        if (countEl) countEl.textContent = chats.length;

        const currentHash = JSON.stringify(chats.map(c => [c.session_id, c.last_message, c.updated_at]));
        if (isBackground && currentHash === lastRenderedChatListHash) {
            return;
        }
        lastRenderedChatListHash = currentHash;
        applyChatFilters();
    } catch (e) {
        console.error("Error loading WhatsApp chats:", e);
    }
}

let activeChatFilter = "all";

window.filterChatChannel = function(channel) {
    activeChatFilter = channel;
    const allBtn = document.getElementById("chat-filter-all");
    const waBtn = document.getElementById("chat-filter-wa");
    const webBtn = document.getElementById("chat-filter-web");

    [allBtn, waBtn, webBtn].forEach(b => b && b.classList.remove("active"));
    if (channel === "all" && allBtn) allBtn.classList.add("active");
    if (channel === "whatsapp" && waBtn) waBtn.classList.add("active");
    if (channel === "web" && webBtn) webBtn.classList.add("active");

    applyChatFilters();
};

function isWhatsAppChat(c) {
    const sid = String(c.session_id || "");
    const contact = String(c.contact || "");
    return (sid.startsWith("+") || /^\d{7,15}$/.test(sid) || contact.startsWith("+") || /^\d{7,15}$/.test(contact)) && !sid.startsWith("session_");
}

function applyChatFilters() {
    let filtered = allWhatsAppChatsData;
    if (activeChatFilter === "whatsapp") {
        filtered = filtered.filter(c => isWhatsAppChat(c));
    } else if (activeChatFilter === "web") {
        filtered = filtered.filter(c => !isWhatsAppChat(c));
    }

    const q = (waSearchInput ? waSearchInput.value : "").toLowerCase().trim();
    if (q) {
        filtered = filtered.filter(c => 
            (c.name && c.name.toLowerCase().includes(q)) || 
            (c.session_id && c.session_id.toLowerCase().includes(q)) ||
            (c.contact && c.contact.toLowerCase().includes(q)) ||
            (c.last_message && c.last_message.toLowerCase().includes(q))
        );
    }
    renderWhatsAppSidebar(filtered);
}

function renderWhatsAppSidebar(chats) {
    const listContainer = document.getElementById("whatsapp-sessions-list");
    if (!listContainer) return;

    if (!chats || chats.length === 0) {
        listContainer.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">No matching conversations found.</div>`;
        return;
    }

    listContainer.innerHTML = "";
    chats.forEach(c => {
        const item = document.createElement("div");
        item.className = "whatsapp-session-item";
        const isActive = c.session_id === activeWhatsAppSessionId;
        const initial = (c.name && c.name.charAt(0)) ? c.name.charAt(0).toUpperCase() : 'C';
        const isWA = isWhatsAppChat(c);
        const channelIcon = isWA 
            ? `<span style="display:inline-flex; align-items:center; gap:3px; background:rgba(37,211,102,0.15); color:#25d366; font-size:0.65rem; padding:1px 5px; border-radius:4px; font-weight:700;"><i class="fa-brands fa-whatsapp"></i> WA</span>`
            : `<span style="display:inline-flex; align-items:center; gap:3px; background:rgba(83,189,235,0.15); color:#53bdeb; font-size:0.65rem; padding:1px 5px; border-radius:4px; font-weight:700;"><i class="fa-solid fa-desktop"></i> Web</span>`;

        item.style.cssText = `
            padding: 12px 16px;
            border-bottom: 1px solid var(--glass-border);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            background: ${isActive ? 'rgba(0, 168, 132, 0.12)' : 'transparent'};
            border-left: ${isActive ? '4px solid #00a884' : '4px solid transparent'};
            transition: all 0.2s ease;
        `;

        function formatSessionTime(isoStr) {
            if (!isoStr) return "";
            try {
                const d = new Date(isoStr);
                if (isNaN(d.getTime())) return isoStr.substring(11, 16);
                const now = new Date();
                const isToday = d.toDateString() === now.toDateString();
                if (isToday) {
                    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
                }
                return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
            } catch (e) {
                return "";
            }
        }

        function getSessionIntentChip(c) {
            const intent = c.user_intent || "";
            if (intent === "printer") {
                return `<span style="background: rgba(83,189,235,0.2); color: #53bdeb; font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; font-weight: 700; margin-left: 4px;">Printer Inquirer</span>`;
            }
            if (intent === "ink") {
                return `<span style="background: rgba(168,85,247,0.2); color: #c084fc; font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; font-weight: 700; margin-left: 4px;">Ink Lead</span>`;
            }
            if (intent === "media") {
                return `<span style="background: rgba(245,158,11,0.2); color: #fbbf24; font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; font-weight: 700; margin-left: 4px;">Media Lead</span>`;
            }
            if (intent === "checkout") {
                return `<span style="background: rgba(16,185,129,0.2); color: #10b981; font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; font-weight: 700; margin-left: 4px;">Checkout Intent</span>`;
            }

            const msg = (c.last_message || "").toLowerCase();
            if (msg.includes("p9500") || msg.includes("p7500") || msg.includes("p20000") || msg.includes("p9000") || msg.includes("printer")) {
                return `<span style="background: rgba(83,189,235,0.2); color: #53bdeb; font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; font-weight: 700; margin-left: 4px;">Printer Inquirer</span>`;
            }
            if (msg.includes("ink") || msg.includes("cartridge") || msg.includes("t800")) {
                return `<span style="background: rgba(168,85,247,0.2); color: #c084fc; font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; font-weight: 700; margin-left: 4px;">Ink Lead</span>`;
            }
            if (msg.includes("canvas") || msg.includes("paper") || msg.includes("media") || msg.includes("korejet")) {
                return `<span style="background: rgba(245,158,11,0.2); color: #fbbf24; font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; font-weight: 700; margin-left: 4px;">Media Lead</span>`;
            }
            if (msg.includes("payment") || msg.includes("order") || msg.includes("buy")) {
                return `<span style="background: rgba(16,185,129,0.2); color: #10b981; font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; font-weight: 700; margin-left: 4px;">Checkout Intent</span>`;
            }
            return "";
        }

        item.innerHTML = `
            <div style="width: 44px; height: 44px; border-radius: 50%; background: ${isWA ? '#00a884' : '#2563eb'}; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; flex-shrink: 0;">
                ${initial}
            </div>
            <div style="flex: 1; min-width: 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                    <div style="display:flex; align-items:center; gap:4px; overflow:hidden;">
                        <span style="font-weight: 700; font-size: 0.88rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px;">${c.name || c.session_id}</span>
                        ${channelIcon}
                        ${getSessionIntentChip(c)}
                    </div>
                    <span style="font-size: 0.68rem; color: var(--text-muted);">${formatSessionTime(c.updated_at)}</span>
                </div>
                <div style="font-size: 0.76rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    ${c.last_message ? (c.last_message.startsWith('[Admin]') ? '<strong>Admin:</strong> ' + c.last_message.replace('[Admin]: ', '') : c.last_message.replace(/^(?:assistant|system|bot)\s*[:\n\-]+\s*/i, '')) : 'No messages yet'}
                </div>
            </div>
        `;

        item.addEventListener("click", () => {
            activeWhatsAppSessionId = c.session_id;
            loadWhatsAppChat(c);
            applyChatFilters();
        });

        listContainer.appendChild(item);
    });
}

// Search Filter Input Listener
const waSearchInput = document.getElementById("wa-search-input");
if (waSearchInput) {
    waSearchInput.addEventListener("input", () => {
        applyChatFilters();
    });
}

function formatWhatsAppText(text) {
    if (!text) return "";
    let formatted = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/_([^_]+)_/g, '<em>$1</em>');
    formatted = formatted.replace(/~([^~]+)~/g, '<del>$1</del>');
    formatted = formatted.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.15); padding:1px 4px; border-radius:3px; font-size:0.85em;">$1</code>');
    formatted = formatted.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" style="color: #53bdeb; text-decoration: underline;">$1</a>');
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
}

let currentRenderedMessageCount = 0;
let currentRenderedSessionId = null;

async function loadWhatsAppChat(chatObj, isBackground = false) {
    if (!chatObj || !chatObj.session_id) return;
    const sid = chatObj.session_id;
    activeWhatsAppSessionId = sid;

    const titleEl = document.getElementById("whatsapp-active-title");
    const subTitleEl = document.getElementById("whatsapp-active-subtitle");
    const badgesEl = document.getElementById("whatsapp-active-badges");
    const bodyContainer = document.getElementById("whatsapp-messages-body");
    const inputContainer = document.getElementById("whatsapp-input-container");
    const avatarEl = document.getElementById("wa-header-avatar");

    const displayName = chatObj.name && chatObj.name !== sid ? chatObj.name : `Customer ${sid}`;
    if (titleEl) titleEl.textContent = displayName;
    if (subTitleEl) subTitleEl.textContent = chatObj.contact ? `Contact: ${chatObj.contact}` : `Session ID: ${sid}`;
    if (badgesEl) badgesEl.innerHTML = `<span class="badge status-${chatObj.status || 'prospect'}">${chatObj.status || 'prospect'}</span>`;
    
    if (avatarEl) {
        avatarEl.textContent = displayName.charAt(0).toUpperCase();
    }

    if (inputContainer) inputContainer.style.display = "block";
    
    // Only show loading indicator if explicitly switching conversations, NOT during background polling
    if (!isBackground || currentRenderedSessionId !== sid) {
        bodyContainer.innerHTML = `<div style="margin: auto; text-align: center; color: var(--text-muted); font-size: 0.88rem;"><i class="fa-solid fa-spinner fa-spin"></i> Fetching transcript...</div>`;
    }

    try {
        const res = await adminFetch(`/api/chat/${sid}`);
        const data = await res.json();
        const messages = data.messages || [];

        // If background refresh and message count is unchanged for this session, skip re-rendering to prevent flickering
        if (isBackground && currentRenderedSessionId === sid && currentRenderedMessageCount === messages.length) {
            return;
        }

        currentRenderedSessionId = sid;
        currentRenderedMessageCount = messages.length;

        if (messages.length === 0) {
            bodyContainer.innerHTML = `<div style="margin: auto; text-align: center; color: var(--text-muted); font-size: 0.88rem;">No messages in this chat session yet. Type below to start the conversation!</div>`;
            return;
        }

        bodyContainer.innerHTML = "";
        messages.forEach(msg => {
            if (!msg.content) return;

            const isUser = msg.role === "user";
            const isAdmin = msg.content.startsWith("[Admin]") || msg.content.startsWith("[Admin Voice Note]") || msg.sender_type === "admin";
            const isVoice = msg.is_voice || msg.content.includes("🎙️") || msg.content.startsWith("[Admin Voice Note]");
            
            const rawContent = isAdmin ? msg.content.replace("[Admin]: ", "").replace("[Admin Voice Note]: ", "") : msg.content;
            
            function formatMsgTime(t) {
                if (!t) return new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
                try {
                    const d = new Date(t);
                    if (isNaN(d.getTime())) return String(t).substring(11, 16);
                    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
                } catch (e) {
                    return "";
                }
            }
            const timeStr = formatMsgTime(msg.timestamp);

            const msgDiv = document.createElement("div");
            msgDiv.style.cssText = `
                display: flex;
                flex-direction: column;
                max-width: 70%;
                align-self: ${isUser ? 'flex-start' : 'flex-end'};
                margin-bottom: 4px;
            `;

            const bubbleDiv = document.createElement("div");
            bubbleDiv.className = isUser ? "wa-bubble-user" : "wa-bubble-admin";

            if (isVoice) {
                // Render Voice Note Bubble
                bubbleDiv.innerHTML = `
                    <div class="wa-voice-bubble">
                        <button type="button" class="wa-voice-play-btn" onclick="playVoiceText('${rawContent.replace(/'/g, "\\'")}')">
                            <i class="fa-solid fa-play"></i>
                        </button>
                        <div style="flex: 1;">
                            <div class="wa-waveform">
                                <div class="wa-waveform-bar" style="height: 12px;"></div>
                                <div class="wa-waveform-bar" style="height: 18px;"></div>
                                <div class="wa-waveform-bar" style="height: 10px;"></div>
                                <div class="wa-waveform-bar" style="height: 22px;"></div>
                                <div class="wa-waveform-bar" style="height: 14px;"></div>
                                <div class="wa-waveform-bar" style="height: 20px;"></div>
                                <div class="wa-waveform-bar" style="height: 16px;"></div>
                                <div class="wa-waveform-bar" style="height: 12px;"></div>
                            </div>
                            <span style="font-size: 0.72rem; color: var(--text-muted);">Voice Note (Neural TTS)</span>
                        </div>
                    </div>
                    <div class="wa-meta-time">
                        <span>${timeStr}</span>
                        ${!isUser ? '<span class="wa-ticks"><i class="fa-solid fa-check-double"></i></span>' : ''}
                    </div>
                `;
            } else {
                // Standard Text Bubble
                bubbleDiv.innerHTML = `
                    ${isAdmin ? '<span style="font-size: 0.68rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #00a884; display: block; margin-bottom: 4px;"><i class="fa-solid fa-user-shield"></i> Sent as Admin</span>' : ''}
                    <div style="word-wrap: break-word;">${formatWhatsAppText(rawContent)}</div>
                    <div class="wa-meta-time">
                        <span>${timeStr}</span>
                        ${!isUser ? '<span class="wa-ticks"><i class="fa-solid fa-check-double"></i></span>' : ''}
                    </div>
                `;
            }

            msgDiv.appendChild(bubbleDiv);
            bodyContainer.appendChild(msgDiv);
        });

        bodyContainer.scrollTop = bodyContainer.scrollHeight;
    } catch (e) {
        console.error("Error loading chat stream:", e);
        if (!isBackground) {
            bodyContainer.innerHTML = `<div style="margin: auto; text-align: center; color: #ef4444; font-size: 0.88rem;">Failed to load transcript.</div>`;
        }
    }
}

// Speech synthesis playback helper for voice note bubbles in admin UI
window.playVoiceText = function(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const cleanText = text.replace(/🎙️/g, "").replace(/\[.*?\]/g, "");
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.0;
        window.speechSynthesis.speak(utterance);
    } else {
        alert("Audio playback not supported in this browser.");
    }
};

// Handle Admin sending text messages
const adminChatForm = document.getElementById("admin-chat-form");
if (adminChatForm) {
    adminChatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const input = document.getElementById("admin-chat-input");
        const msg = input.value.trim();
        if (!msg || !activeWhatsAppSessionId) return;

        input.disabled = true;
        try {
            const res = await adminFetch(`/api/admin/chats/${activeWhatsAppSessionId}/send`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            if (data.status === "success") {
                input.value = "";
                await loadWhatsAppChat({ session_id: activeWhatsAppSessionId });
                await fetchWhatsAppChats();
            } else {
                alert("Failed to send message: " + (data.error || "Unknown error"));
            }
        } catch (err) {
            console.error("Admin send error:", err);
            alert("Failed to send message.");
        } finally {
            input.disabled = false;
            input.focus();
        }
    });
}

// Handle Admin Recording & Sending Voice Notes
const adminMicBtn = document.getElementById("admin-mic-btn");
if (adminMicBtn) {
    adminMicBtn.addEventListener("click", async () => {
        if (!activeWhatsAppSessionId) {
            alert("Please select a WhatsApp conversation session first.");
            return;
        }

        const voiceText = prompt("🎙️ Record Admin Voice Note:\nType the message you want to synthesize and send as a humanized Neural Voice Note to WhatsApp:");
        if (!voiceText || !voiceText.trim()) return;

        adminMicBtn.disabled = true;
        adminMicBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;

        try {
            const res = await adminFetch(`/api/admin/chats/${activeWhatsAppSessionId}/voice`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: voiceText.trim() })
            });
            const data = await res.json();
            if (data.status === "success") {
                await loadWhatsAppChat({ session_id: activeWhatsAppSessionId });
                await fetchWhatsAppChats();
            } else {
                alert("Failed to send voice note: " + (data.error || "Unknown error"));
            }
        } catch (err) {
            console.error("Admin voice send error:", err);
            alert("Failed to send voice note.");
        } finally {
            adminMicBtn.disabled = false;
            adminMicBtn.innerHTML = `<i class="fa-solid fa-microphone"></i>`;
        }
    });
}

// ─── Product Picker Modal for In-Chat 1-Click Dispatch ──────────────────────────────
let pickerActiveCategory = "all";

window.openAdminProductPickerModal = function() {
    if (!activeWhatsAppSessionId) {
        alert("Please select a customer chat conversation on the left first.");
        return;
    }
    const modal = document.getElementById("product-picker-modal");
    if (!modal) return;
    modal.style.display = "flex";
    
    const searchInput = document.getElementById("picker-search-input");
    if (searchInput) {
        searchInput.value = "";
        searchInput.focus();
    }
    pickerActiveCategory = "all";
    renderPickerProducts();
};

window.closeAdminProductPickerModal = function() {
    const modal = document.getElementById("product-picker-modal");
    if (modal) modal.style.display = "none";
};

window.filterPickerCategory = function(cat) {
    pickerActiveCategory = cat;
    document.querySelectorAll(".picker-cat-btn").forEach(btn => {
        if (btn.getAttribute("data-cat") === cat) {
            btn.classList.add("active");
            btn.style.background = "#3b82f6";
            btn.style.color = "#fff";
        } else {
            btn.classList.remove("active");
            btn.style.background = "transparent";
            btn.style.color = "var(--text-secondary)";
        }
    });
    renderPickerProducts();
};

const pickerSearchInput = document.getElementById("picker-search-input");
if (pickerSearchInput) {
    pickerSearchInput.addEventListener("input", () => {
        renderPickerProducts();
    });
}

function renderPickerProducts() {
    const grid = document.getElementById("product-picker-grid");
    if (!grid) return;

    let items = [...(productsData || [])];

    if (pickerActiveCategory !== "all") {
        items = items.filter(p => p.category === pickerActiveCategory);
    }

    const q = (pickerSearchInput ? pickerSearchInput.value : "").toLowerCase().trim();
    if (q) {
        items = items.filter(p => 
            p._id.toLowerCase().includes(q) ||
            p.name.toLowerCase().includes(q) ||
            (p.category && p.category.toLowerCase().includes(q)) ||
            (p.tags && p.tags.some(t => t.toLowerCase().includes(q)))
        );
    }

    if (items.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 30px; color: var(--text-muted); font-size: 0.88rem;">No matching catalog items found.</div>`;
        return;
    }

    grid.innerHTML = "";
    items.slice(0, 60).forEach(prod => {
        let imgUrl = prod.image_url;
        if (!imgUrl) {
            const nameL = prod.name.toLowerCase();
            if (nameL.includes("citizen") || nameL.includes("cx-02") || nameL.includes("cz-01")) {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2023/03/Citizen-CX-02-Photo-Printer-Dubai.webp";
            } else if (nameL.includes("p9500") || nameL.includes("p7500") || nameL.includes("p9000") || nameL.includes("p20000") || nameL.includes("sc-p")) {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2023/05/Epson-P9500-Spectro.webp";
            } else if (nameL.includes("ink") || nameL.includes("cartridge") || nameL.includes("singlepack") || nameL.includes("ultrachrome")) {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2018/04/Ink-300x300.jpg";
            } else if (nameL.includes("paper") || nameL.includes("canvas") || nameL.includes("roll")) {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2023/06/Innova-Decor-Smooth-Art-DS-IFA-25.webp";
            } else {
                imgUrl = "https://www.keplertechllc.com/wp-content/uploads/2023/05/Large-Format-Printer.webp";
            }
        }

        const isAvail = (prod.availability === "In Stock") || (prod.stock > 0 && prod.availability !== "Out of Stock");

        const card = document.createElement("div");
        card.style.cssText = "background: var(--inner-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; display: flex; flex-direction: column; gap: 8px; transition: transform 0.2s, border-color 0.2s; box-shadow: 0 2px 6px rgba(0,0,0,0.15);";
        card.innerHTML = `
            <div style="display: flex; gap: 10px; align-items: center;">
                <div style="width: 50px; height: 50px; border-radius: 8px; overflow: hidden; background: #ffffff; display: flex; align-items: center; justify-content: center; flex-shrink: 0; padding: 2px; border: 1px solid var(--border-color);">
                    <img src="${imgUrl}" alt="${prod.name}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-weight: 700; font-size: 0.84rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${prod.name}">${prod.name}</div>
                    <div style="font-family: monospace; font-size: 0.72rem; color: var(--text-muted);">${prod._id}</div>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 4px; border-top: 1px dashed var(--border-color);">
                <span style="font-weight: 700; color: var(--accent-cyan); font-size: 0.88rem;">${prod.price.toFixed(2)} AED</span>
                <span style="font-size: 0.7rem; font-weight: 600; color: ${isAvail ? '#10b981' : '#ef4444'};">${isAvail ? '🟢 In Stock' : '🔴 Out of Stock'}</span>
            </div>
            <div style="display: flex; gap: 6px; margin-top: auto; padding-top: 4px;">
                <button type="button" onclick="adminSendProductToActiveChat('${prod._id}')" style="flex: 1; padding: 7px; background: #00a884; color: #fff; border: none; border-radius: 6px; font-size: 0.76rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 5px;">
                    <i class="fa-solid fa-paper-plane"></i> Send to Chat
                </button>
                <button type="button" onclick="copyProductCard('${prod._id}')" style="padding: 7px 10px; background: rgba(255,255,255,0.08); color: var(--text-secondary); border: 1px solid var(--border-color); border-radius: 6px; font-size: 0.76rem; cursor: pointer;" title="Copy to clipboard">
                    <i class="fa-regular fa-copy"></i>
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
}

// Auto poll WhatsApp chats when WhatsApp tab is open
document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
        if (tab.getAttribute("data-tab") === "whatsapp-tab") {
            fetchWhatsAppChats();
        }
    });
});

setInterval(() => {
    const activeTab = document.querySelector(".nav-tab.active");
    if (activeTab && activeTab.getAttribute("data-tab") === "whatsapp-tab" && getAdminKey()) {
        fetchWhatsAppChats(true);
        if (activeWhatsAppSessionId) {
            loadWhatsAppChat({ session_id: activeWhatsAppSessionId }, true);
        }
    }
}, 8000);
