from django.template.loader import get_template
from django.test import Client
from django.urls import reverse


def test_foundation_home_renders_live_shell_and_representative_page():
    response = Client().get(reverse("home"))

    assert response.status_code == 200
    assert "Northstar Market" in response.content.decode()
    assert "Presentation sample" in response.content.decode()
    assert 'aria-invalid="true"' in response.content.decode()
    assert "Enter a valid email address" in response.content.decode()
    assert response.templates[0].name == "foundation/home.html"
    assert get_template("base.html")
    assert "hx-get=\"/foundation/design-notes/\"" in response.content.decode()
    assert "hx-get=\"/foundation/design-notes-unavailable/\"" in response.content.decode()


def test_foundation_home_is_safe_read_only_page():
    client = Client()

    assert client.head(reverse("home")).status_code == 200
    assert client.post(reverse("home")).status_code == 405


def test_design_notes_renders_a_presentation_fragment():
    client = Client()

    response = client.get(reverse("design-notes"), HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    assert response.templates[0].name == "foundation/_design-notes.html"
    assert "HTMX response received" in response.content.decode()
    assert client.post(reverse("design-notes")).status_code == 405


def test_design_notes_unavailable_exposes_a_presentation_failure_fragment():
    client = Client()

    response = client.get(reverse("design-notes-unavailable"), HTTP_HX_REQUEST="true")

    assert response.status_code == 503
    assert response.templates[0].name == "foundation/_design-notes-unavailable.html"
    assert "We could not load the design notes" in response.content.decode()
    assert client.post(reverse("design-notes-unavailable")).status_code == 405


def test_missing_route_uses_branded_error_state():
    response = Client().get("/not-a-live-route/")

    assert response.status_code == 404
    assert response.templates[0].name == "404.html"
    assert "This path is not ready yet." in response.content.decode()
