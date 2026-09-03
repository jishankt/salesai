/**
 * Kepler Sales Agent — Embeddable Floating Chat Widget Loader
 * Injects a floating launcher button and a pop-up chat iframe onto any webpage.
 */
(function () {
    if (window.KeplerChatWidgetLoaded) return;
    window.KeplerChatWidgetLoaded = true;

    // Detect Host Origin
    const scriptTag = document.currentScript || (function() {
        const scripts = document.getElementsByTagName('script');
        return scripts[scripts.length - 1];
    })();

    let serverOrigin = window.location.origin;
    if (scriptTag && scriptTag.src) {
        try {
            const urlObj = new URL(scriptTag.src);
            if (urlObj.origin && urlObj.origin !== "null") {
                serverOrigin = urlObj.origin;
            }
        } catch (e) {}
    }
    if (!serverOrigin || serverOrigin === "null" || serverOrigin.startsWith("file:")) {
        serverOrigin = "https://compression-outstanding-citations-madrid.trycloudflare.com";
    }

    // 1. Inject Stylesheet
    const linkEl = document.createElement("link");
    linkEl.rel = "stylesheet";
    linkEl.href = `${serverOrigin}/static/css/widget.css?v=2`;
    document.head.appendChild(linkEl);

    // 2. Inject FontAwesome Icons if not already present
    if (!document.querySelector("link[href*='font-awesome']")) {
        const faLink = document.createElement("link");
        faLink.rel = "stylesheet";
        faLink.href = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css";
        document.head.appendChild(faLink);
    }

    // 3. Create DOM Elements for Launcher and Popup
    const launcher = document.createElement("div");
    launcher.id = "kepler-chat-launcher";
    launcher.title = "Chat with Kepler Sales Agent";
    launcher.innerHTML = `
        <i class="fa-solid fa-comments chat-icon"></i>
        <i class="fa-solid fa-xmark close-icon"></i>
        <span class="kepler-pulse-dot"></span>
    `;

    const tooltip = document.createElement("div");
    tooltip.id = "kepler-launcher-tooltip";
    tooltip.textContent = "Chat with Kepler Sales Agent 🖨️";

    const popup = document.createElement("div");
    popup.id = "kepler-popup-widget";
    popup.innerHTML = `
        <iframe id="kepler-widget-iframe" src="${serverOrigin}/?embed=1" allow="microphone"></iframe>
    `;

    document.body.appendChild(launcher);
    document.body.appendChild(tooltip);
    document.body.appendChild(popup);

    // 4. Toggle Interaction Handlers
    let isOpen = false;

    function toggleChat(forceState) {
        isOpen = typeof forceState === "boolean" ? forceState : !isOpen;
        if (isOpen) {
            popup.classList.add("active");
            launcher.classList.add("open");
            tooltip.style.display = "none";
            const pulse = launcher.querySelector(".kepler-pulse-dot");
            if (pulse) pulse.style.display = "none";
        } else {
            popup.classList.remove("active");
            launcher.classList.remove("open");
            tooltip.style.display = "";
        }
    }

    launcher.addEventListener("click", () => toggleChat());
    
    const closeBtn = document.getElementById("kepler-widget-close-btn");
    if (closeBtn) {
        closeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleChat(false);
        });
    }

    // Allow window to be toggled from external links: e.g. <a href="javascript:window.openKeplerChat()">
    window.openKeplerChat = function() {
        toggleChat(true);
    };
    window.closeKeplerChat = function() {
        toggleChat(false);
    };

})();
