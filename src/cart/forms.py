from django import forms

from .models import MAX_QUANTITY


class AddToCartForm(forms.Form):
    product_id = forms.IntegerField(min_value=1)
    quantity = forms.IntegerField(min_value=1, max_value=MAX_QUANTITY)


class UpdateCartItemForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=MAX_QUANTITY)
