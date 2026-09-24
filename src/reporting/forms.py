from django import forms

from . import ranges


class DashboardRangeForm(forms.Form):
    range = forms.ChoiceField(choices=[(key, key) for key in ranges.RANGE_KEYS])
