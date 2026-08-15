from app.geo.timezone import iana_timezone


def test_tokyo_coordinates_are_jst() -> None:
    assert iana_timezone(35.6762, 139.6503) == "Asia/Tokyo"


def test_bengaluru_coordinates_are_kolkata() -> None:
    assert iana_timezone(12.9716, 77.5946) == "Asia/Kolkata"


def test_timezone_is_cached() -> None:
    a = iana_timezone(48.8566, 2.3522)
    b = iana_timezone(48.8566, 2.3522)
    assert a == b == "Europe/Paris"
