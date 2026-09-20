(function () {
    "use strict";

    var header = document.querySelector(".site-header");
    var toggle = document.querySelector(".menu-toggle");
    var navigation = document.getElementById("primary-navigation");

    if (header && toggle && navigation) {
        var closeMenu = function (restoreFocus) {
            header.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
            if (restoreFocus) {
                toggle.focus();
            }
        };

        toggle.addEventListener("click", function () {
            var isOpen = header.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", String(isOpen));
            if (isOpen) {
                var firstLink = navigation.querySelector("a");
                if (firstLink) {
                    firstLink.focus();
                }
            }
        });

        navigation.addEventListener("click", function (event) {
            if (event.target.closest("a")) {
                closeMenu(false);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && header.classList.contains("is-open")) {
                closeMenu(true);
            }
        });

        var desktopQuery = window.matchMedia("(min-width: 48rem)");
        desktopQuery.addEventListener("change", function (event) {
            if (event.matches) {
                closeMenu(false);
            }
        });
    }

    var getDesignNotesRetry = function () {
        return document.querySelector("[data-design-notes-success='true']");
    };

    var restoreDesignNotesLabel = function () {
        var retry = getDesignNotesRetry();
        if (retry) {
            retry.textContent = retry.getAttribute("data-default-label") || "Load design notes";
        }
    };

    var showDesignNotesError = function () {
        var target = document.getElementById("design-note");
        if (!target) {
            return;
        }

        target.setAttribute("role", "alert");
        target.setAttribute("aria-live", "assertive");
        target.replaceChildren();

        var note = document.createElement("div");
        note.className = "design-note design-note--error";

        var eyebrow = document.createElement("p");
        eyebrow.className = "eyebrow";
        eyebrow.textContent = "Dependency unavailable";

        var heading = document.createElement("h3");
        heading.tabIndex = -1;
        heading.textContent = "We could not load the design notes.";

        var message = document.createElement("p");
        message.textContent = "Check the connection and use the retry button below. This is a presentation-only failure preview.";

        note.append(eyebrow, heading, message);
        target.append(note);

        var retry = getDesignNotesRetry();
        if (retry) {
            retry.textContent = "Retry design notes";
        }
        heading.focus();
    };

    document.body.addEventListener("htmx:afterRequest", function (event) {
        var detail = event.detail || {};
        var trigger = detail.elt;
        if (!trigger || trigger.getAttribute("data-design-notes-trigger") !== "true" || detail.successful) {
            return;
        }
        showDesignNotesError();
    });

    // HTMX does not swap error responses, so a 503 (database temporarily unavailable) would otherwise be silent.
    document.body.addEventListener("htmx:responseError", function (event) {
        var xhr = event.detail && event.detail.xhr;
        var main = document.getElementById("main-content");
        if (!xhr || xhr.status !== 503 || !main || document.getElementById("service-unavailable")) {
            return;
        }
        var notice = document.createElement("div");
        notice.id = "service-unavailable";
        notice.className = "message message--error";
        notice.setAttribute("role", "alert");
        notice.textContent = "The service is temporarily unavailable. Please try again in a moment.";
        main.insertBefore(notice, main.firstChild);
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        var target = event.detail && event.detail.target;
        if (!target || target.id !== "design-note") {
            return;
        }

        target.setAttribute("role", "status");
        target.setAttribute("aria-live", "polite");
        restoreDesignNotesLabel();
        var heading = target.querySelector("h3");
        if (heading) {
            heading.focus();
        }
    });
}());
