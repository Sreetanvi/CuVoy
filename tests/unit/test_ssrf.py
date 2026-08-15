from app.providers.website_verify import is_public_http_url


def test_blocks_private_and_non_http() -> None:
    assert is_public_http_url("http://127.0.0.1/hours") is False
    assert is_public_http_url("http://localhost/hours") is False
    assert is_public_http_url("http://10.0.0.5/x") is False
    assert is_public_http_url("http://192.168.1.1/x") is False
    assert is_public_http_url("http://169.254.169.254/latest") is False
    assert is_public_http_url("file:///etc/passwd") is False
    assert is_public_http_url("ftp://example.com/a") is False


def test_allowlist_host_must_match() -> None:
    assert is_public_http_url("https://museum.example/hours", allowed_host="museum.example") is True
    assert is_public_http_url("https://evil.example/hours", allowed_host="museum.example") is False
    assert is_public_http_url("https://sub.museum.example/h", allowed_host="museum.example") is True
