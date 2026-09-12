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

    document.body.addEventListener("htmx:afterSwap", function (event) {
        var target = event.detail && event.detail.target;
        if (!target || target.id !== "design-note") {
            return;
        }

        var heading = target.querySelector("h3");
        if (heading) {
            heading.focus();
        }
    });
}());
