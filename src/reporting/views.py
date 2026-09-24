"""Operator dashboard integration; all metric reads stay in reporting.queries."""
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from itertools import zip_longest

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.generic import View
from django.views.defaults import permission_denied

from accounts.mixins import HtmxLoginRequiredMixin

from . import queries, ranges
from .forms import DashboardRangeForm
from .models import AnalyticsRun


class AnalyticsAccessMixin(HtmxLoginRequiredMixin, PermissionRequiredMixin):
    permission_required = "reporting.view_analytics"


@method_decorator([never_cache, require_GET], name="dispatch")
class AnalyticsDashboardView(AnalyticsAccessMixin, View):
    http_method_names = ["get"]

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied as exc:
            # Return the normal forbidden page through never_cache as well.
            return permission_denied(request, exception=exc)

    def get(self, request):
        form = DashboardRangeForm({"range": request.GET.get("range", ranges.DEFAULT_RANGE)})
        valid = form.is_valid()
        range_key = form.cleaned_data["range"] if valid else ranges.DEFAULT_RANGE
        compare = request.GET.get("compare") == "1"
        # Retention can prune a selected run between reads. Discard every value
        # from that attempt, then select again; never render a partial/mixed run.
        for attempt in range(3):
            run = queries.latest_completed_run(settings.DEMO_NAMESPACE)
            context = {
                "run": run,
                "range_key": range_key,
                "range_keys": ranges.RANGE_KEYS,
                "range_message": "" if valid else "Invalid reporting range; showing the last 30 complete dates.",
                "compare": compare,
                "empty_message": "No completed analytics run is available." if run is None else "",
            }
            if run is not None:
                latest = ranges.latest_complete_date(run.cutoff)
                span = ranges.resolve_span(range_key, latest)
                mode = ranges.granularity(span)
                buckets = ranges.buckets(span, mode)
                coverage = queries.coverage(run)
                counts = Counter(row.status for row in coverage)
                context.update(
                    latest_complete_date=latest,
                    span=span,
                    granularity=mode,
                    summary=queries.sales_summary(run, span),
                    series=queries.bucket_sales(run, buckets),
                    categories=queries.category_sales(run, span),
                    top_sellers=queries.top_sellers(run, span, limit=10),
                    # The query owns ordering and flags. Hide the numeric partial-history
                    # average at the presentation boundary, without changing its formula.
                    coverage=[row._replace(avg_daily_units=None) if row.status == "insufficient_history" else row
                              for row in coverage[:25]],
                    coverage_counts={status: counts[status] for status in
                                     ("flagged", "ok", "unavailable", "insufficient_history")},
                    comparison_span=None,
                    comparison_available=False,
                    comparison_summary=None,
                    comparison_series=[],
                    comparison_categories=[],
                    comparison_top_sellers=[],
                    segment_overview=queries.customer_segment_overview(run),
                    segment_customers=[],
                )
                if context["segment_overview"] is not None:
                    context["segment_customers"] = queries.customer_segment_customers(
                        run, model_version=context["segment_overview"].model_version, limit=50)
                if compare:
                    previous = ranges.comparison_span(span)
                    available = ranges.comparison_available(
                        previous, run.window_start.astimezone(ranges.BUSINESS_TZ).date(), queries.history_start(run))
                    context.update(comparison_span=previous, comparison_available=available)
                    if available:
                        context.update(
                            comparison_summary=queries.sales_summary(run, previous),
                            comparison_series=queries.bucket_sales(run, ranges.shift_buckets(buckets, span.length)),
                            comparison_categories=queries.category_sales(run, previous),
                            comparison_top_sellers=queries.top_sellers(run, previous, limit=10),
                        )
                category_rows = _category_rows(
                    context["categories"], context["comparison_categories"], context["comparison_available"])
                context.update(
                    sales_cards=_sales_cards(context["summary"], context["comparison_summary"], compare,
                                             context["comparison_available"]),
                    trend_chart=_trend_chart_payload(context["series"], context["comparison_series"]),
                    category_chart=_category_chart_payload(category_rows, context["comparison_available"]),
                    trend_rows=[{"selected": selected, "comparison": previous}
                                for selected, previous in zip_longest(context["series"], context["comparison_series"] or [])],
                    category_rows=category_rows,
                    run_short_id=str(run.summary_version).split("-")[0],
                    cutoff_label=run.cutoff.astimezone(ranges.BUSINESS_TZ).strftime("%d %b %Y, %H:%M SGT"),
                    refreshed_label=(run.finished_at.astimezone(ranges.BUSINESS_TZ).strftime("%d %b %Y, %H:%M SGT")
                                     if run.finished_at else "Unknown"),
                )
            if run is None or AnalyticsRun.objects.filter(pk=run.pk).exists():
                break
        else:
            return HttpResponse("Analytics refreshed repeatedly during this request. Please retry.", status=503)
        template = "reporting/_panel.html" if request.headers.get("HX-Request") == "true" else "reporting/dashboard.html"
        return TemplateResponse(request, template, context)


def _comparison_metric(value, previous, enabled, available, kind):
    """Prepare presentation-only comparison labels; aggregation remains in queries.py."""
    if not enabled:
        return {"state": "off", "value": value, "previous": None, "delta": None, "percent": None, "kind": kind}
    if not available:
        return {"state": "insufficient", "value": value, "previous": None, "delta": None, "percent": None, "kind": kind}
    if previous == 0:
        return {"state": "na", "value": value, "previous": previous, "delta": None, "percent": None, "kind": kind}
    if kind == "units":
        delta = int(value) - int(previous)
        percent = (Decimal(delta) / Decimal(previous) * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    else:
        value = Decimal(value)
        previous = Decimal(previous)
        delta = value - previous
        percent = (delta / previous * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return {"state": "available", "value": value, "previous": previous, "delta": delta, "percent": percent, "kind": kind}


def _sales_cards(summary, comparison_summary, compare, comparison_available):
    previous_units = comparison_summary.units if comparison_summary else 0
    previous_amount = comparison_summary.sales_amount if comparison_summary else Decimal("0")
    return [
        {"label": "Sales value", "value": summary.sales_amount,
         "metric": _comparison_metric(summary.sales_amount, previous_amount, compare,
                                       comparison_available, "money")},
        {"label": "Units sold", "value": summary.units,
         "metric": _comparison_metric(summary.units, previous_units, compare,
                                       comparison_available, "units")},
    ]


def _trend_chart_payload(series, comparison):
    payload = {
        "labels": [item.start.isoformat() if item.start == item.end else f"{item.start.isoformat()} – {item.end.isoformat()}"
                   for item in series],
        "values": [float(item.sales_amount) for item in series],
        "units": [item.units for item in series],
        "comparison": None,
    }
    if comparison:
        payload["comparison"] = {
            "values": [float(item.sales_amount) for item in comparison],
            "units": [item.units for item in comparison],
        }
    return payload


def _category_chart_payload(rows, comparison_available):
    return {
        "labels": [row["selected"].category for row in rows],
        "values": [float(row["selected"].sales_amount) for row in rows],
        "units": [row["selected"].units for row in rows],
        "comparison": {
            "values": [float(row["comparison"].sales_amount) for row in rows],
            "units": [row["comparison"].units for row in rows],
        } if comparison_available else None,
    }


def _category_rows(categories, comparison, comparison_available):
    selected = {item.category: item for item in categories}
    previous = {item.category: item for item in comparison}
    # Preserve selected sales ordering, then append prior-only categories in their
    # query order. This aligns presentation values without re-aggregating sales.
    return [{
        "selected": selected.get(category, queries.CategorySales(category, 0, Decimal("0"))),
        "comparison": previous.get(category, queries.CategorySales(category, 0, Decimal("0")))
                      if comparison_available else None,
    } for category in dict.fromkeys([*selected, *previous])]
