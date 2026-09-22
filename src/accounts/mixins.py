from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import resolve_url


class HtmxLoginRequiredMixin(LoginRequiredMixin):
    def handle_no_permission(self):
        if not self.request.user.is_authenticated and self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=200, headers={"HX-Redirect": resolve_url(self.get_login_url())})
        return super().handle_no_permission()
