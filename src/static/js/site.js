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

    var THEME_KEY = "northstar-theme";
    var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

    var activeTheme = function () {
        var explicit = document.documentElement.getAttribute("data-theme");
        if (explicit === "dark" || explicit === "light") {
            return explicit;
        }
        return darkQuery.matches ? "dark" : "light";
    };

    // Delegated so the controls survive every HTMX swap.
    document.addEventListener("click", function (event) {
        var toggle = event.target.closest("[data-theme-toggle]");
        if (!toggle) {
            return;
        }
        var next = activeTheme() === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        try {
            localStorage.setItem(THEME_KEY, next);
        } catch (error) {
            /* The choice still applies to this page; it just will not persist. */
        }
    });

    document.addEventListener("click", function (event) {
        var button = event.target.closest("[data-step]");
        if (!button) {
            return;
        }
        var input = document.getElementById(button.getAttribute("data-step-target"));
        if (!input || input.disabled) {
            return;
        }
        var min = Number(input.getAttribute("min")) || 1;
        var max = Number(input.getAttribute("max")) || 999;
        var current = Number(input.value) || min;
        var next = Math.min(max, Math.max(min, current + Number(button.getAttribute("data-step"))));
        if (next === current) {
            return;
        }
        input.value = String(next);
        // The form listens for change, so this is what posts the new quantity.
        input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    if (!window.htmx) {
        document.documentElement.classList.add("no-htmx");
    }

    var readSubtotal = function () {
        var node = document.querySelector("#cart-content .summary__total dd");
        return node ? node.textContent.trim() : null;
    };

    // HTMX replaces the node, so the old figure has to be read before the
    // swap for the mark below to know whether the money actually moved.
    var previousSubtotal = null;

    document.body.addEventListener("htmx:beforeSwap", function (event) {
        var target = event.detail && event.detail.target;
        if (target && target.id === "cart-content") {
            previousSubtotal = readSubtotal();
        }
    });

    // The swapped fragment cannot host its own live region, because HTMX
    // replaces the element itself. This one lives outside #cart-content.
    document.body.addEventListener("htmx:afterSwap", function (event) {
        var target = event.detail && event.detail.target;
        if (!target || target.id !== "cart-content") {
            return;
        }
        // outerHTML swaps leave event.detail.target detached, so read the
        // fresh node out of the document rather than the swapped-out one.
        var fresh = document.getElementById("cart-content");
        var total = fresh && fresh.querySelector(".summary__total dd");

        var status = document.getElementById("cart-status");
        if (status) {
            status.textContent = total
                ? "Cart updated. Subtotal " + total.textContent.trim() + "."
                : "Cart updated.";
        }

        // State indication, and only when there is a state change to indicate:
        // the figure inverts instantly, then releases over 420ms via CSS.
        if (total && previousSubtotal !== null && total.textContent.trim() !== previousSubtotal) {
            total.classList.add("is-updated");
            // Two frames, so the inverted state is painted before it releases.
            requestAnimationFrame(function () {
                requestAnimationFrame(function () {
                    total.classList.remove("is-updated");
                });
            });
        }
        previousSubtotal = null;
    });

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

    // A cart line updated after it was removed elsewhere (another tab, or placed as an order) answers 404,
    // which HTMX does not swap. Reload so the current cart is shown instead of a stale one.
    document.body.addEventListener("htmx:responseError", function (event) {
        var detail = event.detail || {};
        var target = detail.target;
        if (detail.xhr && detail.xhr.status === 404 && target && target.id === "cart-content") {
            window.location.reload();
        }
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

    // 3D product tiles: reveal once loaded, and ease the spin speed up while
    // the pointer is over the card rather than snapping between speeds.
    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    var IDLE_SPIN = 20;
    var HOVER_SPIN = 120;

    document.querySelectorAll(".tile__model").forEach(function (viewer) {
        var markLoaded = function () {
            viewer.classList.add("is-loaded");
        };
        if (viewer.loaded) {
            markLoaded();
        } else {
            viewer.addEventListener("load", markLoaded, { once: true });
        }

        if (reduceMotion.matches) {
            viewer.removeAttribute("auto-rotate");
            return;
        }

        var card = viewer.closest(".product-card");
        var speed = IDLE_SPIN;
        var target = IDLE_SPIN;
        var frame = null;

        var step = function () {
            speed += (target - speed) * 0.1;
            if (Math.abs(target - speed) < 0.5) {
                speed = target;
            }
            viewer.setAttribute("rotation-per-second", speed.toFixed(1) + "deg");
            frame = speed === target ? null : requestAnimationFrame(step);
        };
        var spinTo = function (value) {
            target = value;
            if (!frame) {
                frame = requestAnimationFrame(step);
            }
        };

        card.addEventListener("pointerenter", function (event) {
            if (event.pointerType === "mouse") {
                spinTo(HOVER_SPIN);
            }
        });
        card.addEventListener("pointerleave", function () {
            spinTo(IDLE_SPIN);
        });
    });
}());
