// Global Image Lightbox Modal for Customer App
window.openImageLightbox = function(src, caption) {
    let modal = document.getElementById("image-lightbox-modal");
    let img = document.getElementById("lightbox-img");
    let cap = document.getElementById("lightbox-caption");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "image-lightbox-modal";
        modal.style.cssText = "display:none; position:fixed; inset:0; z-index:999999; background:rgba(0,0,0,0.88); backdrop-filter:blur(8px); align-items:center; justify-content:center; padding:20px;";
        modal.innerHTML = `
            <div style="position:relative; max-width:90vw; max-height:90vh; display:flex; flex-direction:column; align-items:center;">
                <button id="close-lightbox-btn" onclick="window.closeImageLightbox()" style="position:absolute; top:-45px; right:0; background:rgba(255,255,255,0.25); border:none; color:#ffffff; width:36px; height:36px; border-radius:50%; cursor:pointer; font-size:1.2rem; display:flex; align-items:center; justify-content:center;">
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
            if (e.target === modal) window.closeImageLightbox();
        });
        img = document.getElementById("lightbox-img");
        cap = document.getElementById("lightbox-caption");
    }
    if (img) img.src = src;
    if (cap) cap.textContent = caption || "";
    modal.style.display = "flex";
};

window.closeImageLightbox = function() {
    const modal = document.getElementById("image-lightbox-modal");
    const img = document.getElementById("lightbox-img");
    if (modal) modal.style.display = "none";
    if (img) img.src = "";
};

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") window.closeImageLightbox();
});

window.sendQuickReply = function(text) {
    if (!chatInput || !chatForm) return;
    chatInput.value = text;
    if (typeof chatForm.requestSubmit === "function") {
        chatForm.requestSubmit();
    } else {
        chatForm.dispatchEvent(new Event("submit"));
    }
};

// Load or generate a persistent session ID for the user
let sessionId = localStorage.getItem("sales_ai_session_id");
if (!sessionId) {
    sessionId = 'session_' + Math.random().toString(36).substring(2, 11);
    localStorage.setItem("sales_ai_session_id", sessionId);
}
const leadSessionEl = document.getElementById("lead-session-id");
if (leadSessionEl) leadSessionEl.textContent = sessionId;

const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const typingIndicator = document.getElementById("typing-indicator");
const productsList = document.getElementById("products-list");
const themeToggleBtn = document.getElementById("theme-toggle-btn");

// Multi-language mappings for dynamic full-UI translation
const UI_TRANSLATIONS = {
    "English": {
        "crm_monitor": "Sales AI",
        "crm_subtitle": "Real-time Lead Qualification & CRM",
        "active_lead_profile": "Lead CRM",
        "session_id": "Session ID:",
        "name_label": "Name:",
        "contact_label": "Contact:",
        "needs_label": "Needs:",
        "budget_label": "Budget:",
        "lead_status_label": "Lead Status:",
        "available_catalog": "Catalog",
        "loading_catalog": "Loading product catalog...",
        "active_consultant": "online",
        "new_chat": "New",
        "theme": "Theme",
        "admin_console": "Admin",
        "input_placeholder": "Type a message...",
        "not_provided": "Not Provided",
        "not_analyzed": "Not Analyzed",
        "not_set": "Not Set",
        "prospect": "Prospect",
        "qualified": "Qualified",
        "escalated": "Escalated",
        "stock": "Stock:",
        "catalog_empty": "Catalog empty."
    },
    "Malayalam": {
        "crm_monitor": '<i class="fa-solid fa-chart-line"></i> CRM ലൈവ് മോണിറ്റർ',
        "crm_subtitle": "ലീഡ് യോഗ്യതയും ഡാറ്റാബേസ് എഴുത്തും ട്രാക്ക് ചെയ്യുക",
        "active_lead_profile": '<i class="fa-solid fa-user-tag"></i> സജീവ ലീഡ് പ്രൊഫൈൽ',
        "session_id": "സെഷൻ ഐഡി:",
        "name_label": "പേര്:",
        "contact_label": "ഫോൺ നമ്പർ:",
        "needs_label": "ആവശ്യങ്ങൾ:",
        "budget_label": "ബഡ്ജറ്റ്:",
        "lead_status_label": "ലീഡ് നില:",
        "available_catalog": '<i class="fa-solid fa-box-open"></i> ലഭ്യമായ ഉൽപ്പന്നങ്ങൾ',
        "loading_catalog": "കാറ്റലോഗ് ലോഡ് ചെയ്യുന്നു...",
        "active_consultant": "സജീവ സെയിൽസ് കൺസൾട്ടന്റ്",
        "new_chat": "പുതിയ ചാറ്റ്",
        "theme": "തീം മാറ്റുക",
        "admin_console": "അഡ്മിൻ പാനൽ",
        "input_placeholder": "ഒരു സന്ദേശം ടൈപ്പ് ചെയ്യുക...",
        "not_provided": "നൽകിയിട്ടില്ല",
        "not_analyzed": "വിശകലനം ചെയ്തിട്ടില്ല",
        "not_set": "നിശ്ചയിച്ചിട്ടില്ല",
        "prospect": "പ്രതീക്ഷയുള്ള ആൾ",
        "qualified": "യോഗ്യതയുള്ള ആൾ",
        "escalated": "കൈമാറി",
        "stock": "സ്റ്റോക്ക്:",
        "catalog_empty": "കാറ്റലോഗ് ശൂന്യമാണ്. അഡ്മിൻ പാനലിൽ നിന്ന് സീഡ് ചെയ്യുക."
    },
    "Arabic": {
        "crm_monitor": '<i class="fa-solid fa-chart-line"></i> مراقب نظام إدارة علاقات العملاء (CRM)',
        "crm_subtitle": "متابعة تأهيل العميل وحفظ قاعدة البيانات",
        "active_lead_profile": '<i class="fa-solid fa-user-tag"></i> ملف العميل النشط',
        "session_id": "معرف الجلسة:",
        "name_label": "الاسم:",
        "contact_label": "الاتصال:",
        "needs_label": "الاحتياجات:",
        "budget_label": "الميزانية:",
        "lead_status_label": "حالة العميل:",
        "available_catalog": '<i class="fa-solid fa-box-open"></i> الكتالوج المتاح',
        "loading_catalog": "جاري تحميل الكتالوج...",
        "active_consultant": "مستشار مبيعات نشط",
        "new_chat": "محادثة جديدة",
        "theme": "المظهر",
        "admin_console": "لوحة التحكم",
        "input_placeholder": "اكتب رسالة...",
        "not_provided": "غير متوفر",
        "not_analyzed": "لم يتم تحليلها",
        "not_set": "غير محدد",
        "prospect": "عميل محتمل",
        "qualified": "مؤهل",
        "escalated": "تم التصعيد",
        "stock": "المخزون:",
        "catalog_empty": "الكتالوج فارغ. الرجاء التثبيت من لوحة التحكم."
    }
};

const WELCOME_MESSAGES = {
    "English": "👋 Hey! I'm your Kepler Sales Agent at Kepler Tech. What printing equipment, inks, or supplies can I help you find today?",
    "Malayalam": "👋 നമസ്കാരം! ഞാൻ കെപ്ലർ ടെക് AI സെയിൽസ് കൺസൾട്ടന്റ് ആണ്. നിങ്ങൾക്ക് ആവശ്യമായ പ്രിന്റർ, ഇങ്ക്, അല്ലെങ്കിൽ സപ്ലൈസ് ഏതൊക്കെയാണ്?",
    "Arabic": "👋 مرحباً! أنا مستشار المبيعات الذكي في كيبلر تك. ما هي معدات الطباعة أو الأحبار أو المستلزمات التي تبحث عنها اليوم؟"
};

const SPEECH_LANGS = {
    "English": "en-US",
    "Malayalam": "ml-IN",
    "Arabic": "ar-AE"
};

const THINKING_MESSAGES = {
    "English": {
        "default": "Kepler Sales Agent is writing a reply...",
        "order": "Kepler Sales Agent is drafting your order... 📝",
        "search": "Kepler Sales Agent is checking product database... 🔍",
        "crm": "Kepler Sales Agent is saving details to CRM... 👤"
    },
    "Malayalam": {
        "default": "കെപ്ലർ സെയിൽസ് ഏജന്റ് മറുപടി എഴുതുന്നു...",
        "order": "കെപ്ലർ സെയിൽസ് ഏജന്റ് നിങ്ങളുടെ ഓർഡർ തയ്യാറാക്കുന്നു... 📝",
        "search": "കെപ്ലർ സെയിൽസ് ഏജന്റ് ഉൽപ്പന്നങ്ങൾ പരിശോധിക്കുന്നു... 🔍",
        "crm": "കെപ്ലർ സെയിൽസ് ഏജന്റ് വിവരങ്ങൾ സംരക്ഷിക്കുന്നു... 👤"
    },
    "Arabic": {
        "default": "مستشار مبيعات كيبلر يكتب رداً...",
        "order": "مستشار مبيعات كيبلر يجهز طلبك... 📝",
        "search": "مستشار مبيعات كيبلر يبحث في قاعدة البيانات... 🔍",
        "crm": "مستشار مبيعات كيبلر يحفظ البيانات... 👤"
    }
};

// State
let currentLang = localStorage.getItem("sales_ai_lang") || "English";

// Apply full UI translation to all elements with data-translate attribute
function applyLanguage(lang) {
    currentLang = lang;
    localStorage.setItem("sales_ai_lang", lang);

    // Update active class on language buttons and visual styles
    document.querySelectorAll(".lang-btn").forEach(btn => {
        if (btn.getAttribute("data-lang") === lang) {
            btn.classList.add("active");
            btn.style.borderColor = "var(--accent-color)";
            btn.style.background = "var(--accent-color)";
            btn.style.color = "#ffffff";
        } else {
            btn.classList.remove("active");
            btn.style.borderColor = "var(--border-color)";
            btn.style.background = "var(--bg-secondary)";
            btn.style.color = "var(--text-primary)";
        }
    });

    // Translate DOM elements marked with data-translate
    const dict = UI_TRANSLATIONS[lang] || UI_TRANSLATIONS["English"];
    document.querySelectorAll("[data-translate]").forEach(el => {
        const key = el.getAttribute("data-translate");
        if (dict[key]) {
            // Check if we need to preserve font-awesome icons inside H2/H3
            const iconMatch = el.innerHTML.match(/<i class=".*?"><\/i>/);
            if (iconMatch) {
                el.innerHTML = iconMatch[0] + " " + dict[key].replace(/<i class=".*?"><\/i>\s*/, "");
            } else {
                el.textContent = dict[key];
            }
        }
    });

    // Update input placeholder
    if (chatInput) {
        chatInput.placeholder = dict["input_placeholder"] || "Type a message...";
    }

    // Update welcome message if chat history is empty
    const welcomeEl = document.getElementById("welcome-message-bubble");
    if (welcomeEl && chatMessages.children.length <= 2) {
        welcomeEl.textContent = WELCOME_MESSAGES[lang];
    }

    // Refresh dynamic content layouts
    updateLeadProfile();
    fetchProducts();
}

// Bind language buttons if present
document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        applyLanguage(btn.getAttribute("data-lang"));
    });
});

// Theme Toggle Logic
const currentTheme = localStorage.getItem("sales_ai_theme") || "dark";
if (currentTheme === "light") {
    document.body.setAttribute("data-theme", "light");
}
themeToggleBtn.addEventListener("click", () => {
    if (document.body.getAttribute("data-theme") === "light") {
        document.body.removeAttribute("data-theme");
        localStorage.setItem("sales_ai_theme", "dark");
    } else {
        document.body.setAttribute("data-theme", "light");
        localStorage.setItem("sales_ai_theme", "light");
    }
});

if (productsList) {
    productsList.addEventListener("click", (e) => {
        const btn = e.target.closest(".view-details-btn, .add-to-cart-btn");
        if (!btn) return;
        
        const prodId = btn.getAttribute("data-id");
        const prodName = btn.getAttribute("data-name");
        if (!prodId) return;

        chatInput.value = prodId;
        if (typeof chatForm.requestSubmit === "function") {
            chatForm.requestSubmit();
        } else {
            chatForm.dispatchEvent(new Event("submit"));
        }
    });
}

// Sidebar switcher between Lead CRM & Product Catalog
window.switchSidebarTab = function(tab) {
    const leadPanel = document.getElementById("sidebar-lead-panel");
    const catalogPanel = document.getElementById("sidebar-catalog-panel");
    const leadBtn = document.getElementById("tab-btn-lead");
    const catalogBtn = document.getElementById("tab-btn-catalog");

    if (tab === 'lead') {
        leadPanel.style.display = 'block';
        catalogPanel.style.display = 'none';
        leadBtn.classList.add('active');
        catalogBtn.classList.remove('active');
    } else {
        leadPanel.style.display = 'none';
        catalogPanel.style.display = 'flex';
        catalogBtn.classList.add('active');
        leadBtn.classList.remove('active');
    }
};

let allCatalogProducts = [];

// Catalog search filter
const catalogFilterInput = document.getElementById("catalog-filter-input");
if (catalogFilterInput) {
    catalogFilterInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        renderProducts(allCatalogProducts.filter(p => 
            p.name.toLowerCase().includes(query) || 
            (p._id && p._id.toLowerCase().includes(query)) ||
            (p.item_group && p.item_group.toLowerCase().includes(query))
        ));
    });
}

function renderProducts(data) {
    const dict = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS["English"];
    if (!productsList) return;
    
    if (data.length === 0) {
        productsList.innerHTML = `<div class="loading-products" style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.82rem;">No products found.</div>`;
        return;
    }
    
    productsList.innerHTML = "";
    data.forEach(prod => {
        const item = document.createElement("div");
        item.className = "product-item";
        const imgHtml = prod.image_url 
            ? `<img src="${prod.image_url}" alt="${prod.name}" class="product-thumb" style="cursor: pointer; transition: transform 0.2s ease;" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'" onclick="openImageLightbox('${prod.image_url}', '${prod.name.replace(/'/g, "\\'")}')" title="Click to view large photo" onerror="this.style.display='none'">` 
            : `<div class="product-thumb" style="display:flex;align-items:center;justify-content:center;color:var(--wa-teal);font-size:1.1rem;"><i class="fa-solid fa-box"></i></div>`;
        
        item.innerHTML = `
            ${imgHtml}
            <div class="product-details">
                <div class="prod-header">
                    <span class="prod-title" title="${prod.name}">${prod.name}</span>
                    <span class="prod-price">${prod.price.toFixed(2)} AED</span>
                </div>
                <div class="prod-desc">${prod.description || ''}</div>
                <div class="prod-footer" style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                    <span style="font-size:0.72rem; color:var(--text-muted); font-family:monospace;">${prod._id}</span>
                    <span style="font-size:0.72rem; color:${prod.stock > 0 ? 'var(--wa-teal)' : 'var(--text-escalated)'}; font-weight:600;">
                        ${prod.stock > 0 ? `<i class="fa-solid fa-check"></i> ${prod.stock} in stock` : 'Out of stock'}
                    </span>
                </div>
                <div class="prod-actions" style="margin-top: 6px;">
                    <button class="btn btn-primary view-details-btn" data-id="${prod._id}" data-name="${prod.name}" style="font-size: 0.76rem; padding: 6px 10px; width: 100%; border-radius: 6px; cursor: pointer; background: linear-gradient(135deg, #00a884 0%, #059669 100%); color: #ffffff; border: none; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 6px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                        <i class="fa-solid fa-eye"></i> View Details
                    </button>
                </div>
            </div>
        `;
        productsList.appendChild(item);
    });
}

// Fetch products list
async function fetchProducts() {
    try {
        const res = await fetch("/api/products");
        const data = await res.json();
        allCatalogProducts = data;
        renderProducts(data);
    } catch (e) {
        console.error("Error loading products:", e);
    }
}
        


// Fetch CRM Lead status
async function updateLeadProfile() {
    try {
        const res = await fetch(`/api/lead/${sessionId}`);
        const data = await res.json();
        const dict = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS["English"];
        
        if (data.status === "success" && data.lead) {
            const lead = data.lead;
            
            // Territory
            const territoryEl = document.getElementById("lead-territory");
            if (territoryEl) {
                if (lead.territory) {
                    territoryEl.textContent = lead.territory;
                    territoryEl.className = "value badge status-qualified";
                } else {
                    territoryEl.textContent = dict.not_set || "Not Set";
                    territoryEl.className = "value badge status-empty";
                }
            }

            // Name
            const nameEl = document.getElementById("lead-name");
            if (lead.name) {
                nameEl.textContent = lead.name;
                nameEl.className = "value badge status-qualified";
            } else {
                nameEl.textContent = dict.not_provided;
                nameEl.className = "value badge status-empty";
            }
            
            // Contact
            const contactEl = document.getElementById("lead-contact");
            if (lead.contact) {
                contactEl.textContent = lead.contact;
                contactEl.className = "value badge status-qualified";
            } else {
                contactEl.textContent = dict.not_provided;
                contactEl.className = "value badge status-empty";
            }
            
            // Needs
            const needsEl = document.getElementById("lead-needs");
            needsEl.textContent = lead.needs || dict.not_analyzed;
            
            // Budget
            const budgetEl = document.getElementById("lead-budget");
            if (lead.budget) {
                budgetEl.textContent = lead.budget;
                budgetEl.className = "value badge status-qualified";
            } else {
                budgetEl.textContent = dict.not_set;
                budgetEl.className = "value badge status-empty";
            }
            
            // Status
            const statusEl = document.getElementById("lead-status");
            const statusText = dict[lead.status] || lead.status.toUpperCase();
            statusEl.textContent = statusText;
            statusEl.className = `value badge status-${lead.status}`;
        }
    } catch (e) {
        console.error("Error loading lead profile:", e);
    }
}

// Format message bubble timestamps to local time with AM/PM
function getFormattedTime(dateInput = null) {
    let d = dateInput ? new Date(dateInput) : new Date();
    if (isNaN(d.getTime())) d = new Date();
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
}

// Append new message bubble
function appendMessage(sender, text, audioUrl = null, timestamp = null) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender} animate-fade-in`;
    
    let formattedText = text || "";

    // Detect and parse product card blocks into a horizontal scrollable carousel
    if (sender === 'bot' && (formattedText.includes("━━━━━━━━━━━━━━━━━━━━") || formattedText.includes("📦"))) {
        const cardRegex = /━━━━━━━━━━━━━━━━━━━━([\s\S]*?)━━━━━━━━━━━━━━━━━━━━/g;
        let cardMatches = [];
        let match;
        
        while ((match = cardRegex.exec(formattedText)) !== null) {
            cardMatches.push(match[1].trim());
        }

        // If matched full card blocks
        if (cardMatches.length > 0) {
            // Text outside of the cards
            let introText = formattedText.replace(cardRegex, "").trim();
            
            // Format intro markdown
            introText = introText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            introText = introText.replace(/\*([^*]+)\*/g, '<em>$1</em>');
            introText = introText.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" style="color: #3b82f6; font-weight:700; text-decoration: underline;">$1</a>');
            
            // Format inline category dashes and bullets into clean line breaks
            introText = introText.replace(/(?:^|\s)–\s*|\s-\s+(?=[A-Z\d\p{Emoji}])/gu, '<br>• ');
            introText = introText.replace(/(?<!<br>)\s*•\s*/g, '<br>• ');
            introText = introText.replace(/^(?:<br>)+/, '');

            // Format [Options: Choice 1 | Choice 2] or [Choice 1 | Choice 2] -> Interactive Quick-Reply Pills
            introText = introText.replace(/\[(?:Options:\s*)?([A-Za-z0-9\s&,–\-\/\+]{2,}(?:\s*\|\s*[A-Za-z0-9\s&,–\-\/\+]{2,})+)\]/g, (match, optsStr) => {
                const opts = optsStr.split("|").map(o => o.trim()).filter(o => o.length > 0);
                const pills = opts.map(opt => `
                    <button type="button" class="quick-reply-pill" onclick="sendQuickReply('${opt.replace(/'/g, "\\'")}')" style="background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.35); padding: 7px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.15s ease; display: inline-flex; align-items: center; gap: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);" onmouseover="this.style.background='#10b981'; this.style.color='#fff';" onmouseout="this.style.background='rgba(16, 185, 129, 0.12)'; this.style.color='#10b981';">
                        <i class="fa-solid fa-arrow-right-long" style="font-size: 0.75rem;"></i> <span>${opt}</span>
                    </button>
                `).join("");
                return `<div class="quick-reply-container" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; margin-bottom: 12px;">${pills}</div>`;
            });
            
            const cardHtmls = cardMatches.map(cleanBlock => {
                const nameMatch = cleanBlock.match(/📦\s*\*?([^\n\*]+)\*?/);
                const priceMatch = cleanBlock.match(/💵\s*\*?Price:\*?\s*([^\n]+)/i);
                const availMatch = cleanBlock.match(/📊\s*\*?Availability:\*?\s*([^\n]+)/i);
                const descMatch = cleanBlock.match(/📝\s*\*?Description:\*?\s*([^\n]+)/i);
                const webMatch = cleanBlock.match(/🔗\s*\*?Website:\*?\s*([^\n\s]+)/i);
                const idMatch = cleanBlock.match(/(?:Product ID|ID):\*?\s*`?([A-Za-z0-9\-]+)`?/i);
                const scoreMatch = cleanBlock.match(/🎯\s*\*?Match Satisfaction:\s*([^\n\*]+)\*?/i);

                const prodName = nameMatch ? nameMatch[1].trim() : "Kepler Product";
                const prodPrice = priceMatch ? priceMatch[1].trim() : "";
                const prodAvail = availMatch ? availMatch[1].trim() : "🟢 In Stock";
                const prodDesc = descMatch ? descMatch[1].trim() : "";
                const prodId = idMatch ? idMatch[1].trim() : "";
                const matchScore = scoreMatch ? scoreMatch[1].trim() : "";

                let prodWeb = webMatch ? webMatch[1].trim() : "";
                // Will try to resolve from catalog below (after product matching)

                // Find matching product image from catalog if available (Exact ID match first)
                let prodImg = "";
                const nameClean = prodName.toLowerCase();
                let found = null;
                if (prodId) {
                    found = allCatalogProducts.find(p => p._id === prodId || (p.sku && p.sku === prodId));
                }
                if (!found) {
                    found = allCatalogProducts.find(p => 
                        p.name.toLowerCase() === nameClean ||
                        p.name.toLowerCase().includes(nameClean) ||
                        nameClean.includes(p.name.toLowerCase())
                    );
                }
                
                if (found && found.image_url) {
                    prodImg = found.image_url;
                } else {
                    if (nameClean.includes("citizen") || nameClean.includes("cx-02") || nameClean.includes("cz-01")) {
                        prodImg = "https://www.keplertechllc.com/wp-content/uploads/2023/03/Citizen-CX-02-Photo-Printer-Dubai.webp";
                    } else if (nameClean.includes("p9500") || nameClean.includes("p7500") || nameClean.includes("p9000") || nameClean.includes("p20000") || nameClean.includes("sc-p")) {
                        prodImg = "https://www.keplertechllc.com/wp-content/uploads/2023/05/Epson-P9500-Spectro.webp";
                    } else if (nameClean.includes("enterprise") || nameClean.includes("c20600") || nameClean.includes("c21000") || nameClean.includes("workforce")) {
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

                // Resolve web URL: prefer catalog's web_url (from real Kepler sitemap), then auto-generate slug
                if (found && found.web_url) {
                    prodWeb = found.web_url;
                }
                if (!prodWeb || !prodWeb.startsWith("http")) {
                    const cleanSlug = prodName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
                    prodWeb = `https://www.keplertechllc.com/product/${cleanSlug}/`;
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

                return `
                    <div class="compact-product-card">
                        <div class="compact-card-img-wrap" onclick="openImageLightbox('${prodImg}', '${prodName.replace(/'/g, "\\'")}')" title="Click to view large photo">
                            <img src="${prodImg}" alt="${prodName}">
                            <span style="position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,0.72); backdrop-filter: blur(4px); color: #fff; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; font-weight: 600;">${prodAvail}</span>
                            ${matchScore ? `<span style="position: absolute; top: 6px; left: 6px; background: #10b981; color: #fff; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; font-weight: 700;">🎯 ${matchScore}</span>` : ''}
                        </div>
                        <div class="compact-card-body">
                            <div class="compact-card-title" title="${prodName}">${prodName}</div>
                            <div class="compact-card-desc" title="${prodDesc}">${prodDesc || 'Genuine Kepler OEM commercial printing supply.'}</div>
                            
                            <div class="compact-card-footer">
                                <span style="font-size: 0.72rem; color: #0284c7; font-weight: 700; background: rgba(2,132,199,0.08); padding: 2px 6px; border-radius: 4px;">🏷️ ${brandTag}</span>
                                <a href="${prodWeb}" target="_blank" style="font-size: 0.7rem; color: #3b82f6; font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; gap: 3px;" title="Official Kepler page">
                                    <i class="fa-solid fa-arrow-up-right-from-square"></i> Web
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }).join("");

            // Separate top introductory header from closing option pills
            let introHeader = introText;
            let closingPills = "";
            const pillsMatch = introText.match(/<div class="quick-reply-container"[\s\S]*?<\/div>/);
            if (pillsMatch) {
                closingPills = pillsMatch[0];
                introHeader = introText.replace(pillsMatch[0], "").trim();
            }

            formattedText = `
                ${introHeader ? `<div style="margin-bottom: 8px;">${introHeader}</div>` : ''}
                <div class="product-carousel-track">
                    ${cardHtmls}
                </div>
                ${closingPills ? `<div style="margin-top: 8px;">${closingPills}</div>` : ''}
            `;
        }
    } else {
        // Render markdown bold **text** → <strong>text</strong>
        formattedText = formattedText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Render markdown italic *text* → <em>text</em>
        formattedText = formattedText.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        // Render markdown links [Title](https://...)
        formattedText = formattedText.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" style="color: #3b82f6; font-weight:700; text-decoration: underline;">$1</a>');
        // Match standalone absolute http/https URLs not already in href
        formattedText = formattedText.replace(/(?<!href=")(https?:\/\/[^\s<"\)]+)/g, '<a href="$1" target="_blank" class="payment-link" style="color: #3b82f6; font-weight:600; text-decoration: underline;">$1</a>');
        // Match relative checkout URLs like /checkout/SO-XXXXXX
        formattedText = formattedText.replace(/(?<!["'=])(\/checkout\/[A-Za-z0-9\-]+)/g, '<a href="$1" target="_blank" class="payment-link" style="color: #10b981; font-weight:700; text-decoration: underline;">Tap to Pay → $1</a>');
        
        // Format [Draft: SKU] -> HTML button
        formattedText = formattedText.replace(/\[Draft:\s*([A-Za-z0-9\-]+)\]/g, (match, sku) => {
            return `<button class="btn chat-draft-btn" data-id="${sku}" style="display:block; margin-top: 8px; width: 100%; text-align:center; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color:#ffffff; padding: 8px; border-radius: 8px; font-weight:600; font-size:0.85rem; border:none; cursor:pointer;"><i class="fa-solid fa-file-invoice"></i> Draft Quotation</button>`;
        });

        // Format inline category dashes and bullets into clean line breaks
        formattedText = formattedText.replace(/(?:^|\s)–\s*|\s-\s+(?=[A-Z\d\p{Emoji}])/gu, '<br>• ');
        formattedText = formattedText.replace(/(?<!<br>)\s*•\s*/g, '<br>• ');
        formattedText = formattedText.replace(/^(?:<br>)+/, ''); // strip leading break

        // If the message lists the 4 categories without an explicit [Options: ...] tag, auto-inject the 4 suggestion buttons!
        const hasCategories = (formattedText.includes("Technical") || formattedText.includes("CAD")) && 
                              (formattedText.includes("Office") || formattedText.includes("Business") || formattedText.includes("Enterprise")) && 
                              (formattedText.includes("Photo") || formattedText.includes("Booth")) && 
                              !formattedText.includes("quick-reply-container") && 
                              !formattedText.includes("[Options:");

        if (hasCategories) {
            formattedText += `\n[Options: Technical / CAD | Office & Enterprise | Photo Booth | Fine Art & Photo]`;
        }

        // Format [Options: Choice 1 | Choice 2] or [Choice 1 | Choice 2] -> Interactive Quick-Reply Pills
        formattedText = formattedText.replace(/\[(?:Options:\s*)?([^\n\[\]|]{2,}(?:\s*\|\s*[^\n\[\]|]{2,})+)\]/g, (match, optsStr) => {
            const opts = optsStr.split("|").map(o => o.trim()).filter(o => o.length > 0);
            const pills = opts.map(opt => `
                <button type="button" class="quick-reply-pill" onclick="sendQuickReply('${opt.replace(/'/g, "\\'")}')" style="background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.35); padding: 7px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.15s ease; display: inline-flex; align-items: center; gap: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);" onmouseover="this.style.background='#10b981'; this.style.color='#fff';" onmouseout="this.style.background='rgba(16, 185, 129, 0.12)'; this.style.color='#10b981';">
                    <i class="fa-solid fa-arrow-right-long" style="font-size: 0.75rem;"></i> <span>${opt}</span>
                </button>
            `).join("");
            return `<div class="quick-reply-container" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px;">${pills}</div>`;
        });
    }

    let audioHtml = "";
    if (audioUrl) {
        const uniqueId = "audio_" + Math.random().toString(36).substr(2, 9);
        audioHtml = `
            <div class="whatsapp-audio-player" id="player_${uniqueId}">
                <button type="button" class="audio-play-btn" id="play_btn_${uniqueId}"><i class="fa-solid fa-play"></i></button>
                <div class="audio-track-container">
                    <input type="range" class="audio-slider" id="slider_${uniqueId}" min="0" max="100" value="0">
                    <div class="audio-time-row">
                        <span class="audio-time" id="time_${uniqueId}">0:00</span>
                    </div>
                </div>
                <div class="audio-avatar">
                    <i class="fa-solid fa-microphone" style="${sender === 'user' ? 'color: var(--accent-cyan);' : 'color: #8b9bb4;'}"></i>
                </div>
            </div>
        `;
        setTimeout(() => {
            initAudioPlayer(uniqueId, audioUrl);
        }, 50);
    }

    const ticksHtml = sender === 'user' ? `<span class="wa-ticks"><i class="fa-solid fa-check-double"></i></span>` : '';

    messageDiv.innerHTML = `
        <div class="bubble">
            <div class="bubble-text">${formattedText}</div>
            ${audioHtml}
            <span class="time">${getFormattedTime(timestamp)} ${ticksHtml}</span>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Custom Audio Player Controller
function initAudioPlayer(uniqueId, audioUrl) {
    const playBtn = document.getElementById(`play_btn_${uniqueId}`);
    const slider = document.getElementById(`slider_${uniqueId}`);
    const timeDisplay = document.getElementById(`time_${uniqueId}`);
    
    if (!playBtn || !slider || !timeDisplay) return;

    const audio = new Audio(audioUrl);
    let isPlaying = false;

    playBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isPlaying) {
            audio.pause();
        } else {
            audio.play().catch(e => console.error("Audio playback failed:", e));
        }
    });

    audio.addEventListener("play", () => {
        isPlaying = true;
        playBtn.innerHTML = `<i class="fa-solid fa-pause"></i>`;
    });

    audio.addEventListener("pause", () => {
        isPlaying = false;
        playBtn.innerHTML = `<i class="fa-solid fa-play"></i>`;
    });

    audio.addEventListener("ended", () => {
        isPlaying = false;
        playBtn.innerHTML = `<i class="fa-solid fa-play"></i>`;
        slider.value = 0;
        timeDisplay.textContent = formatTime(audio.duration || 0);
    });

    audio.addEventListener("timeupdate", () => {
        if (audio.duration) {
            const progress = (audio.currentTime / audio.duration) * 100;
            slider.value = progress;
            timeDisplay.textContent = formatTime(audio.currentTime);
        }
    });

    audio.addEventListener("loadedmetadata", () => {
        timeDisplay.textContent = formatTime(audio.duration);
    });

    slider.addEventListener("input", () => {
        if (audio.duration) {
            const seekTime = (slider.value / 100) * audio.duration;
            audio.currentTime = seekTime;
        }
    });
}

function formatTime(secs) {
    if (isNaN(secs) || secs === Infinity) return "0:00";
    const minutes = Math.floor(secs / 60);
    const seconds = Math.floor(secs % 60);
    return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
}

// Global listener for chat-draft-btn
document.addEventListener("click", (e) => {
    const btn = e.target.closest(".chat-draft-btn");
    if (btn) {
        const sku = btn.getAttribute("data-id");
        chatInput.value = `Create draft for ${sku}`;
        if (typeof chatForm.requestSubmit === "function") {
            chatForm.requestSubmit();
        } else {
            chatForm.dispatchEvent(new Event("submit"));
        }
    }
});

// Simulates humanized typing indicator and display delay
async function simulateTypingAndAppend(responseMsg) {
    typingIndicator.classList.remove("hidden");
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    const delayTime = Math.max(600, Math.min(2200, responseMsg.length * 30));
    await new Promise(resolve => setTimeout(resolve, delayTime));
    
    typingIndicator.classList.add("hidden");
    appendMessage("bot", responseMsg);
}

// State to keep track if we are in voice mode (auto-synth replies)
let voiceModeActive = false;

// Chat Form submit action
chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const messageText = chatInput.value.trim();
    if (!messageText) return;
    
    appendMessage("user", messageText);
    chatInput.value = "";
    
    const langMsgs = THINKING_MESSAGES[currentLang] || THINKING_MESSAGES["English"];
    let thinkingStatus = langMsgs.default;
    const lowerText = messageText.toLowerCase();
    if (lowerText.includes("buy") || lowerText.includes("order") || lowerText.includes("checkout") || lowerText.includes("yes")) {
        thinkingStatus = langMsgs.order;
    } else if (lowerText.includes("price") || lowerText.includes("cost") || lowerText.includes("stock") || lowerText.includes("available") || lowerText.includes("have")) {
        thinkingStatus = langMsgs.search;
    } else if (lowerText.match(/\d+/) && (lowerText.includes("name") || lowerText.includes("number") || lowerText.includes("phone") || lowerText.includes("contact"))) {
        thinkingStatus = langMsgs.crm;
    }

    const thinkingDiv = document.createElement("div");
    thinkingDiv.className = "message bot thinking-bubble animate-fade-in";
    thinkingDiv.id = "jishan-thinking-status";
    thinkingDiv.innerHTML = `
        <div class="bubble glass-bubble" style="color: var(--text-secondary); font-style: italic; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-circle-notch fa-spin" style="color: var(--accent-color);"></i> ${thinkingStatus}
        </div>
    `;
    chatMessages.appendChild(thinkingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    typingIndicator.classList.remove("hidden");
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                message: messageText,
                language: currentLang,
                voice_reply: voiceModeActive
            })
        });
        
        const data = await response.json();
        
        const activeThinking = document.getElementById("jishan-thinking-status");
        if (activeThinking) activeThinking.remove();
        typingIndicator.classList.add("hidden");
        
        if (data.bubbles && data.bubbles.length > 0) {
            for (const bubble of data.bubbles) {
                appendMessage("bot", bubble.text, bubble.audio_url);
                
                if (bubble.audio_url) {
                    const audio = new Audio(bubble.audio_url);
                    audio.play().catch(e => console.log("Voice autoplay blocked:", e));
                }
            }
        } else {
            appendMessage("bot", "Sorry, something went wrong on my end.");
        }
        
        await updateLeadProfile();
        await fetchProducts();
        
    } catch (e) {
        const activeThinking = document.getElementById("jishan-thinking-status");
        if (activeThinking) activeThinking.remove();
        typingIndicator.classList.add("hidden");
        appendMessage("bot", "Oh, I hit a snag checking that. Try sending again?");
        console.error("Chat error:", e);
    }
});

let initialHistoryLoaded = false;

// Fetch and load existing chat history once on page load
async function loadChatHistory() {
    if (initialHistoryLoaded) return;
    try {
        const res = await fetch(`/api/chat/${sessionId}`);
        const data = await res.json();
        const messages = data.messages || [];
        
        if (messages.length > 0) {
            chatMessages.innerHTML = "";
            messages.forEach(msg => {
                appendMessage(msg.role, msg.content, msg.audio_url, msg.timestamp);
                if (msg.audio_url) {
                    voiceModeActive = true;
                }
            });
            initialHistoryLoaded = true;
        } else {
            const welcomeEl = document.getElementById("welcome-message-bubble");
            if (welcomeEl) {
                welcomeEl.textContent = WELCOME_MESSAGES[currentLang];
            }
            initialHistoryLoaded = true;
        }
    } catch (e) {
        console.error("Error loading chat history:", e);
    }
}

// Web Audio MediaRecorder Voice recording
let mediaRecorder = null;
let audioChunks = [];
const micBtn = document.getElementById("mic-btn");

if (micBtn) {
    micBtn.addEventListener("click", async () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstart = () => {
                micBtn.classList.add("recording");
                chatInput.placeholder = "Listening... Click mic again to send";
                chatInput.disabled = true;
            };

            mediaRecorder.onstop = async () => {
                micBtn.classList.remove("recording");
                chatInput.placeholder = "Type a message...";
                chatInput.disabled = false;

                // Stop all tracks to release hardware mic
                stream.getTracks().forEach(track => track.stop());

                const audioBlob = new Blob(audioChunks, { type: "audio/ogg; codecs=opus" });
                if (audioBlob.size > 1000) { // Ensure it's not empty/tapped accidentally
                    voiceModeActive = true;
                    await uploadAndProcessVoiceMsg(audioBlob);
                }
            };

            mediaRecorder.start();
        } catch (err) {
            console.error("Microphone access denied:", err);
            alert("Microphone access is required to send voice notes.");
        }
    });
}

async function uploadAndProcessVoiceMsg(blob) {
    const thinkingDiv = document.createElement("div");
    thinkingDiv.className = "message bot thinking-bubble animate-fade-in";
    thinkingDiv.id = "jishan-thinking-status";
    thinkingDiv.innerHTML = `
        <div class="bubble glass-bubble" style="color: var(--text-secondary); font-style: italic; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-circle-notch fa-spin" style="color: var(--accent-color);"></i> Transcribing and thinking...
        </div>
    `;
    chatMessages.appendChild(thinkingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    typingIndicator.classList.remove("hidden");
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const formData = new FormData();
    formData.append("audio", blob, "voice.ogg");
    formData.append("session_id", sessionId);
    formData.append("language", currentLang);

    try {
        const res = await fetch("/api/chat-audio", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        
        const activeThinking = document.getElementById("jishan-thinking-status");
        if (activeThinking) activeThinking.remove();
        typingIndicator.classList.add("hidden");

        if (res.status === 422) {
            appendMessage("bot", data.error || "Could not transcribe audio.");
            return;
        }

        if (data.transcription) {
            appendMessage("user", `🎙️ ${data.transcription}`, data.customer_audio_url);
        }

        if (data.bubbles && data.bubbles.length > 0) {
            for (const bubble of data.bubbles) {
                typingIndicator.classList.remove("hidden");
                chatMessages.scrollTop = chatMessages.scrollHeight;
                
                await new Promise(resolve => setTimeout(resolve, bubble.delay * 1000));
                
                typingIndicator.classList.add("hidden");
                appendMessage("bot", bubble.text, bubble.audio_url);
                
                if (bubble.audio_url) {
                    const audio = new Audio(bubble.audio_url);
                    audio.play().catch(e => console.log("Voice autoplay blocked:", e));
                }
                
                await new Promise(resolve => setTimeout(resolve, 300));
            }
        }
        
        await updateLeadProfile();
        await fetchProducts();
        
    } catch (e) {
        const activeThinking = document.getElementById("jishan-thinking-status");
        if (activeThinking) activeThinking.remove();
        typingIndicator.classList.add("hidden");
        appendMessage("bot", "Oh, I hit a snag checking that. Try sending again?");
        console.error("Audio upload error:", e);
    }
}

// Reset Session (New Chat) button action
const newChatBtn = document.getElementById("new-chat-btn");
if (newChatBtn) {
    newChatBtn.addEventListener("click", () => {
        localStorage.removeItem("sales_ai_session_id");
        window.location.reload();
    });
}

// Inject Dynamic CSS Styles for WhatsApp audio player and mic recording pulse
const styleBlock = document.createElement("style");
styleBlock.textContent = `
.whatsapp-audio-player {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    min-width: 250px;
    max-width: 320px;
    margin-top: 6px;
}
.audio-play-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    border: none;
    color: white;
    font-size: 0.95rem;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 0.2s, background-color 0.2s;
    box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);
}
.audio-play-btn:hover {
    transform: scale(1.05);
}
.audio-track-container {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.audio-slider {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 4px;
    border-radius: 2px;
    background: rgba(255, 255, 255, 0.2);
    outline: none;
    cursor: pointer;
}
.audio-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #10b981;
    cursor: pointer;
    box-shadow: 0 0 4px rgba(0,0,0,0.5);
}
.audio-slider::-moz-range-thumb {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #10b981;
    cursor: pointer;
    border: none;
    box-shadow: 0 0 4px rgba(0,0,0,0.5);
}
.audio-time-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: var(--text-muted, #8b9bb4);
    font-family: monospace;
}
.audio-avatar {
    font-size: 1.1rem;
    color: var(--text-muted, #8b9bb4);
    display: flex;
    align-items: center;
    padding-right: 4px;
}
#mic-btn.recording {
    background: #ef4444 !important;
    color: #ffffff !important;
    border-color: #ef4444 !important;
    animation: mic-pulse 1.2s infinite;
}
@keyframes mic-pulse {
    0% {
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
    }
    70% {
        box-shadow: 0 0 0 10px rgba(239, 68, 68, 0);
    }
    100% {
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
    }
}
`;
document.head.appendChild(styleBlock);

// Image Lightbox Modal Logic
window.openImageLightbox = function(src, caption) {
    const modal = document.getElementById("image-lightbox-modal");
    const img = document.getElementById("lightbox-img");
    const cap = document.getElementById("lightbox-caption");
    if (!modal || !img) return;
    img.src = src;
    if (cap) cap.textContent = caption || "";
    modal.style.display = "flex";
    modal.style.zIndex = "999999";
};

window.closeImageLightbox = function() {
    const modal = document.getElementById("image-lightbox-modal");
    const img = document.getElementById("lightbox-img");
    if (!modal) return;
    modal.style.display = "none";
    if (img) img.src = "";
};

document.addEventListener("DOMContentLoaded", () => {
    const closeBtn = document.getElementById("close-lightbox-btn");
    const modal = document.getElementById("image-lightbox-modal");
    if (closeBtn) closeBtn.addEventListener("click", window.closeImageLightbox);
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) window.closeImageLightbox();
        });
    }
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") window.closeImageLightbox();
});

// Delegate click on any product image or card image
document.addEventListener("click", (e) => {
    const imgTarget = e.target.closest(".product-card img, .card-image-wrap img, .product-img, #products-list img");
    if (imgTarget && imgTarget.src) {
        const card = imgTarget.closest(".product-card") || imgTarget.closest(".card");
        let title = imgTarget.alt || "";
        if (!title && card) {
            const heading = card.querySelector("h4, h3, .product-title, strong");
            if (heading) title = heading.textContent.trim();
        }
        openImageLightbox(imgTarget.src, title);
    }
});

// Initializations
applyLanguage(currentLang);
fetchProducts();
loadChatHistory();
setInterval(() => {
    updateLeadProfile();
    fetchProducts();
    loadChatHistory();
}, 3000);
