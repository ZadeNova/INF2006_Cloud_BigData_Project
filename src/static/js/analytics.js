(function () {
    "use strict";

    // Colours come from the theme's custom properties (site.css), read at draw
    // time so light and dark mode both work. Fallbacks only cover a missing
    // stylesheet; they are not a second palette.
    function themeColor(name, fallback) {
        var value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    function palette() {
        return {
            primary: themeColor("--color-text-primary", "#0a0a0a"),
            muted: themeColor("--color-text-secondary", "#525252"),
            tick: themeColor("--color-text-secondary", "#525252"),
            grid: themeColor("--color-border-subtle", "#e5e5e5"),
            surface: themeColor("--color-surface", "#fafafa")
        };
    }

    function readPayload(id) {
        var element = document.getElementById(id);
        if (!element) {
            return null;
        }
        try {
            return JSON.parse(element.textContent);
        } catch (error) {
            return null;
        }
    }

    function destroyChart(canvas) {
        if (window.Chart && window.Chart.getChart) {
            var chart = window.Chart.getChart(canvas);
            if (chart) {
                chart.destroy();
            }
        }
    }

    function trendChart(canvas, payload) {
        var c = palette();
        var datasets = [{
            label: "Selected sales value",
            data: payload.values,
            borderColor: c.primary,
            backgroundColor: "transparent",
            pointBackgroundColor: c.primary,
            pointBorderColor: c.surface,
            pointBorderWidth: 2,
            pointRadius: 4,
            tension: 0,
            fill: false
        }];
        if (payload.comparison) {
            datasets.push({
                label: "Previous period",
                data: payload.comparison.values,
                borderColor: c.muted,
                backgroundColor: "transparent",
                pointBackgroundColor: c.muted,
                pointBorderColor: c.surface,
                pointBorderWidth: 2,
                pointRadius: 3,
                borderDash: [7, 5],
                tension: 0,
                fill: false
            });
        }
        return new window.Chart(canvas, {
            type: "line",
            data: { labels: payload.labels, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: { labels: { usePointStyle: true, color: c.tick } },
                    tooltip: { callbacks: { label: function (context) { return " S$" + Number(context.parsed.y).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); } } }
                },
                scales: {
                    x: { ticks: { color: c.tick, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }, grid: { display: false } },
                    y: { beginAtZero: true, ticks: { color: c.tick, callback: function (value) { return "S$" + Number(value).toLocaleString(); } }, grid: { color: c.grid } }
                }
            }
        });
    }

    function categoryChart(canvas, payload) {
        var c = palette();
        var datasets = [{
            label: "Selected period sales value",
            data: payload.values,
            backgroundColor: c.primary,
            borderColor: c.primary,
            borderWidth: 1,
            borderRadius: 0,
            maxBarThickness: 30
        }];
        if (payload.comparison) {
            datasets.push({
                label: "Previous period sales value (outline)",
                data: payload.comparison.values,
                backgroundColor: "transparent",
                borderColor: c.muted,
                borderWidth: 2,
                borderRadius: 0,
                maxBarThickness: 30
            });
        }
        return new window.Chart(canvas, {
            type: "bar",
            data: {
                labels: payload.labels,
                datasets: datasets
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { usePointStyle: true, color: c.tick } },
                    tooltip: { callbacks: { label: function (context) { return " S$" + Number(context.parsed.x).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); } } }
                },
                scales: {
                    x: { beginAtZero: true, ticks: { color: c.tick, callback: function (value) { return "S$" + Number(value).toLocaleString(); } }, grid: { color: c.grid } },
                    y: { ticks: { color: c.tick }, grid: { display: false } }
                }
            }
        });
    }

    function drawCharts(root) {
        if (!window.Chart || !root) {
            return;
        }
        window.Chart.defaults.font.family = themeColor("--font-sans", "sans-serif");
        var trend = root.querySelector("[data-chart='trend']");
        var categories = root.querySelector("[data-chart='categories']");
        if (trend) {
            destroyChart(trend);
            var trendPayload = readPayload("analytics-trend-data");
            if (trendPayload) {
                trendChart(trend, trendPayload);
            }
        }
        if (categories) {
            destroyChart(categories);
            var categoryPayload = readPayload("analytics-category-data");
            if (categoryPayload) {
                categoryChart(categories, categoryPayload);
            }
        }
    }

    function announcePanel(panel) {
        if (!panel) {
            return;
        }
        panel.setAttribute("aria-busy", "false");
        var heading = panel.querySelector("h2, h3");
        if (heading && document.activeElement && document.activeElement !== document.body) {
            return;
        }
        if (heading) {
            heading.setAttribute("tabindex", "-1");
            heading.focus({ preventScroll: true });
        }
    }

    function panelError(event) {
        var detail = event.detail || {};
        var target = detail.target;
        if (!target && detail.elt && detail.elt.closest) {
            var hxTarget = detail.elt.getAttribute("hx-target");
            if (hxTarget === "#analytics-panel" || detail.elt.closest("#analytics-panel")) {
                target = document.getElementById("analytics-panel");
            }
        }
        if (!target && detail.requestConfig && detail.requestConfig.elt) {
            var requestElement = detail.requestConfig.elt;
            if (requestElement.getAttribute("hx-target") === "#analytics-panel") {
                target = document.getElementById("analytics-panel");
            }
        }
        if (!target && (detail.xhr || detail.requestConfig || detail.error)) {
            // HTMX versions and transport failures do not always expose the
            // resolved target on the event detail. This page has no other
            // panel requests, so retain the current dashboard as the safe
            // fallback target.
            target = document.getElementById("analytics-panel");
        }
        var xhr = detail.xhr;
        if (!target || target.id !== "analytics-panel") {
            return;
        }
        var existing = target.querySelector("[data-analytics-error]");
        if (existing) {
            existing.remove();
        }
        var notice = document.createElement("div");
        notice.className = "message message--error analytics-message";
        notice.setAttribute("role", "alert");
        notice.setAttribute("data-analytics-error", "true");
        notice.setAttribute("tabindex", "-1");
        var heading = document.createElement("strong");
        heading.textContent = xhr && xhr.status === 403 ? "Analytics access is no longer available." : "We could not refresh this panel.";
        var message = document.createElement("p");
        message.textContent = xhr && xhr.status === 403 ? "Sign in with an operator account to continue." : "The current dashboard remains visible. Please try again in a moment.";
        notice.append(heading, message);
        target.setAttribute("aria-busy", "false");
        target.insertBefore(notice, target.firstChild);
        // A failed swap leaves the old panel in place; restore its charts
        // after the pre-swap cleanup so the visible dashboard remains useful.
        drawCharts(target);
        notice.focus();
    }

    function redrawForTheme() {
        drawCharts(document.getElementById("analytics-panel"));
    }

    new MutationObserver(redrawForTheme).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"]
    });
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redrawForTheme);

    document.addEventListener("DOMContentLoaded", function () {
        drawCharts(document.getElementById("analytics-panel"));
    });

    document.body.addEventListener("htmx:beforeSwap", function (event) {
        var target = event.detail && event.detail.target;
        if (!target || target.id !== "analytics-panel") {
            return;
        }
        target.querySelectorAll("[data-chart]").forEach(destroyChart);
        target.setAttribute("aria-busy", "true");
    });

    document.body.addEventListener("htmx:load", function (event) {
        var target = event.detail && event.detail.elt;
        var panel = target && target.id === "analytics-panel" ? target : document.getElementById("analytics-panel");
        drawCharts(panel);
        announcePanel(panel);
    });

    document.body.addEventListener("htmx:responseError", panelError);
    document.body.addEventListener("htmx:sendError", panelError);
}());
