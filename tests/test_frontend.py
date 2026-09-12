from django.template.loader import get_template
from django.test import Client
from django.urls import reverse


def test_foundation_home_renders_live_shell_and_representative_page():
    response = Client().get(reverse("home"))

    assert response.status_code == 200
    assert "Northstar Market" in response.content.decode()
    assert "Presentation sample" in response.content.decode()
    assert response.templates[0].name == "foundation/home.html"
    assert get_template("base.html")


def test_foundation_home_is_safe_read_only_page():
    client = Client()

    assert client.head(reverse("home")).status_code == 200
    assert client.post(reverse("home")).status_code == 405
