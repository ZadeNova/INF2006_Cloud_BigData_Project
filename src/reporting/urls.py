from django.urls import path

from .views import AnalyticsDashboardView

app_name = "reporting"
urlpatterns = [path("", AnalyticsDashboardView.as_view(), name="dashboard")]
