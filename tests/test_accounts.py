"""Registration, login and logout through Django's built-in auth views."""
import re

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse

from accounts.models import CustomerProfile

pytestmark = pytest.mark.django_db


def csrf_token_from(response):
    match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())
    return match.group(1)


@pytest.mark.parametrize("route, template", [
    ("accounts:register", "accounts/register.html"),
    ("accounts:login", "registration/login.html"),
])
def test_anonymous_visitors_can_open_the_auth_pages(route, template):
    # A different path from the POST re-render tests below: this is the GET a visitor makes to reach the form.
    response = Client().get(reverse(route))

    assert response.status_code == 200
    assert response.templates[0].name == template


def test_registration_creates_user_with_usable_password_and_no_profile():
    client = Client()

    response = client.post(reverse("accounts:register"), {
        "username": "newcustomer",
        "password1": "Str0ngPass!2026",
        "password2": "Str0ngPass!2026",
    })

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")
    user = get_user_model().objects.get(username="newcustomer")
    assert user.has_usable_password()
    assert CustomerProfile.objects.count() == 0


def test_registration_rejects_duplicate_username():
    get_user_model().objects.create_user(username="existing")
    client = Client()

    response = client.post(reverse("accounts:register"), {
        "username": "existing",
        "password1": "Str0ngPass!2026",
        "password2": "Str0ngPass!2026",
    })

    assert response.status_code == 200
    assert response.templates[0].name == "accounts/register.html"
    assert "already exists" in response.content.decode()


def test_registration_enforces_the_password_validators():
    # "too common" proves AUTH_PASSWORD_VALIDATORS is wired; a mismatch is UserCreationForm's own behaviour
    response = Client().post(reverse("accounts:register"), {
        "username": "dup", "password1": "password123", "password2": "password123"})

    assert response.status_code == 200
    assert "too common" in response.content.decode()
    assert not get_user_model().objects.filter(username="dup").exists()


def test_authenticated_user_is_redirected_away_from_register():
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="already-in"))

    response = client.get(reverse("accounts:register"))

    assert response.status_code == 302
    assert response.url == "/products/"


def test_login_success_authenticates_and_redirects():
    get_user_model().objects.create_user(username="loginuser", password="Str0ngPass!2026")
    client = Client()

    response = client.post(reverse("accounts:login"), {
        "username": "loginuser",
        "password": "Str0ngPass!2026",
    })

    assert response.status_code == 302
    assert response.url == "/products/"
    assert "_auth_user_id" in client.session


def test_login_failure_rerenders_with_non_field_error():
    get_user_model().objects.create_user(username="loginuser", password="Str0ngPass!2026")
    client = Client()

    response = client.post(reverse("accounts:login"), {
        "username": "loginuser",
        "password": "wrong-password",
    })

    assert response.status_code == 200
    assert response.templates[0].name == "registration/login.html"
    assert "Please enter a correct username and password" in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_login_honours_safe_next_redirect():
    get_user_model().objects.create_user(username="loginuser", password="Str0ngPass!2026")
    client = Client()

    response = client.post(reverse("accounts:login"), {
        "username": "loginuser",
        "password": "Str0ngPass!2026",
        "next": reverse("health"),
    })

    assert response.status_code == 302
    assert response.url == reverse("health")


def test_login_ignores_unsafe_next_redirect():
    get_user_model().objects.create_user(username="loginuser", password="Str0ngPass!2026")
    client = Client()

    response = client.post(reverse("accounts:login"), {
        "username": "loginuser",
        "password": "Str0ngPass!2026",
        "next": "https://evil.example.com/",
    })

    assert response.status_code == 302
    assert response.url == "/products/"


def test_authenticated_user_is_redirected_away_from_login():
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="already-in"))

    response = client.get(reverse("accounts:login"))

    assert response.status_code == 302
    assert response.url == "/products/"


def test_logout_requires_post():
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="logoutuser"))

    assert client.get(reverse("accounts:logout")).status_code == 405


def test_logout_clears_session_and_redirects_home():
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="logoutuser"))

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert response.url == "/"
    assert "_auth_user_id" not in client.session


def test_logout_deletes_the_session_server_side_not_just_in_the_browser():
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="logoutuser"))
    session_key = client.cookies["sessionid"].value
    assert Session.objects.filter(session_key=session_key).exists()

    client.post(reverse("accounts:logout"))

    assert not Session.objects.filter(session_key=session_key).exists()
    replay = Client()                                   # the cookie a browser (or an attacker) kept
    replay.cookies["sessionid"] = session_key
    # an authenticated client is redirected away from the login page; 200 means this one is anonymous
    assert replay.get(reverse("accounts:login")).status_code == 200


def test_logout_without_csrf_token_is_rejected():
    client = Client(enforce_csrf_checks=True)
    client.force_login(get_user_model().objects.create_user(username="logoutuser"))

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 403


def test_logout_with_csrf_token_succeeds():
    client = Client(enforce_csrf_checks=True)
    client.force_login(get_user_model().objects.create_user(username="logoutuser"))
    token = csrf_token_from(client.get(reverse("home")))

    response = client.post(reverse("accounts:logout"), {"csrfmiddlewaretoken": token})

    assert response.status_code == 302
