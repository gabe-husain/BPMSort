'''
Smoke tests: the app boots, pages render and the Spotify OAuth flow
works end to end with the Spotify token endpoint mocked out.

Run from the BPMSort directory with: python -m pytest tests/test_smoke.py
'''
import base64
import hashlib
import time
from unittest import mock
from urllib.parse import urlsplit, parse_qs

from routesFolder import authScripts


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP %s" % self.status_code)


TOKEN_PAYLOAD = {
    "access_token": "access-123",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "refresh-123",
    "scope": authScripts.scope,
}


def startLogin(client):
    response = client.get("/login")
    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["Location"]).query)
    return response, {key: value[0] for key, value in query.items()}


def test_index_renders(client):
    assert client.get("/").status_code == 200
    assert client.get("/index").status_code == 200


def test_protected_page_redirects_to_login_without_token(client):
    response = client.get("/UserPlaylists")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_redirects_to_spotify_with_pkce_and_state(client):
    response, query = startLogin(client)

    assert response.headers["Location"].startswith(authScripts.AUTH_URL)
    assert query["response_type"] == "code"
    assert query["client_id"] == "test-client-id"
    assert query["redirect_uri"] == "http://127.0.0.1:5000/callback"
    assert query["scope"] == authScripts.scope
    assert query["code_challenge_method"] == "S256"

    with client.session_transaction() as sess:
        assert sess["oauth_state"] == query["state"]
        digest = hashlib.sha256(sess["code_verifier"].encode()).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert query["code_challenge"] == expected


def test_callback_rejects_bad_state(client):
    startLogin(client)
    with mock.patch.object(authScripts.requests, "post") as post:
        response = client.get("/callback?code=abc&state=wrong")
    assert response.status_code == 400
    post.assert_not_called()


def test_callback_handles_denied_access(client):
    _, query = startLogin(client)
    response = client.get("/callback?error=access_denied&state=" + query["state"])
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "req_token" not in sess


def test_callback_exchanges_code_for_token(client):
    _, query = startLogin(client)
    with client.session_transaction() as sess:
        code_verifier = sess["code_verifier"]

    with mock.patch.object(authScripts.requests, "post", return_value=FakeResponse(TOKEN_PAYLOAD)) as post:
        response = client.get("/callback?code=abc&state=" + query["state"])

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/getProfile")

    sent = post.call_args.kwargs
    assert post.call_args.args[0] == authScripts.TOKEN_URL
    assert sent["data"]["grant_type"] == "authorization_code"
    assert sent["data"]["code"] == "abc"
    assert sent["data"]["code_verifier"] == code_verifier
    assert sent["data"]["redirect_uri"] == "http://127.0.0.1:5000/callback"
    assert sent["auth"] == ("test-client-id", "test-client-secret")

    with client.session_transaction() as sess:
        assert sess["req_token"] == "access-123"
        assert sess["token_refresh"] == "refresh-123"
        assert sess["headers"] == {"Authorization": "Bearer access-123"}
        assert "oauth_state" not in sess


def test_expired_token_is_refreshed(app):
    from routesFolder.oauth2 import getToken

    refreshed = {"access_token": "access-456", "expires_in": 3600, "refresh_token": "refresh-456"}
    with app.test_request_context():
        from flask import session
        session.update({
            "token_info": TOKEN_PAYLOAD,
            "req_token": "access-123",
            "token_refresh": "refresh-123",
            "expires_at": int(time.time()) - 10,
        })
        with mock.patch.object(authScripts.requests, "post", return_value=FakeResponse(refreshed)) as post:
            assert getToken() == "access-456"
        assert post.call_args.kwargs["data"] == {"grant_type": "refresh_token", "refresh_token": "refresh-123"}
        assert session["token_refresh"] == "refresh-456"


def test_localhost_callback_is_rewritten_to_loopback(monkeypatch):
    monkeypatch.setenv("CURRENT_URL", "http://localhost:5000")
    assert authScripts.getCallbackUri() == "http://127.0.0.1:5000/callback"


def test_hosted_callback_is_upgraded_to_https(monkeypatch):
    monkeypatch.setenv("CURRENT_URL", "http://gawesome13.pythonanywhere.com/")
    assert authScripts.getCallbackUri() == "https://gawesome13.pythonanywhere.com/callback"
