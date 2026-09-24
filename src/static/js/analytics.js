(function () {
    "use strict";

    var chartColors = {
        green: "#0b6047",
        accent: "#137956",
        spruce: "#173d34",
        mint: "#d8ebe4",
        muted: "#78958c"
    };

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
        var datasets = [{
            label: "Selected sales value",
            data: payload.values,
            borderColor: chartColors.green,
            backgroundColor: "rgba(11, 96, 71, 0.14)",
            pointBackgroundColor: chartColors.green,
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 4,
            tension: 0.28,
            fill: true
        }];
        if (payload.comparison) {
            datasets.push({
                label: "Previous period",
                data: payload.comparison.values,
                borderColor: chartColors.muted,
                backgroundColor: "transparent",
                pointBackgroundColor: chartColors.muted,
                pointBorderColor: "#ffffff",
                pointBorderWidth: 2,
                pointRadius: 3,
                borderDash: [7, 5],
                tension: 0.28,
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
                    legend: { labels: { usePointStyle: true, color: chartColors.spruce } },
                    tooltip: { callbacks: { label: function (context) { return " S$" + Number(context.parsed.y).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); } } }
                },
                scales: {
                    x: { ticks: { color: chartColors.spruce, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }, grid: { display: false } },
                    y: { beginAtZero: true, ticks: { color: chartColors.spruce, callback: function (value) { return "S$" + Number(value).toLocaleString(); } }, grid: { color: "rgba(23, 61, 52, 0.12)" } }
                }
            }
        });
    }

    function categoryChart(canvas, payload) {
        var datasets = [{
            label: "Selected period sales value",
            data: payload.values,
            backgroundColor: chartColors.accent,
            borderColor: chartColors.green,
            borderWidth: 1,
            borderRadius: 7,
            maxBarThickness: 30
        }];
        if (payload.comparison) {
            datasets.push({
                label: "Previous period sales value (outline)",
                data: payload.comparison.values,
                backgroundColor: "transparent",
                borderColor: chartColors.muted,
                borderWidth: 2,
                borderRadius: 7,
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
                    legend: { labels: { usePointStyle: true, color: chartColors.spruce } },
                    tooltip: { callbacks: { label: function (context) { return " S$" + Number(context.parsed.x).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); } } }
                },
                scales: {
                    x: { beginAtZero: true, ticks: { color: chartColors.spruce, callback: function (value) { return "S$" + Number(value).toLocaleString(); } }, grid: { color: "rgba(23, 61, 52, 0.12)" } },
                    y: { ticks: { color: chartColors.spruce }, grid: { display: false } }
                }
            }
        });
    }

    function drawCharts(root) {
        if (!window.Chart || !root) {
            return;
        }
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
