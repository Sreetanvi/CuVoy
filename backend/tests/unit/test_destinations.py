from app.geo.destinations import allocate_days, parse_city_names, query_matches_place_name


def test_parse_comma_separated_rajasthan_circuit() -> None:
    cities = parse_city_names(
        "Jaipur, Jodhpur, Udaipur",
        "Weekend in Kolkata",
    )
    assert cities == ["Jaipur", "Jodhpur", "Udaipur"]


def test_destination_box_beats_prompt_cities() -> None:
    cities = parse_city_names("Ooty and Coonoor", "2 weeks in Kolkata for food")
    assert cities == ["Ooty", "Coonoor"]


def test_parse_single_city_prompt() -> None:
    cities = parse_city_names("Bengaluru", "3 days in Bengaluru for museums and food")
    assert cities == ["Bengaluru"]


def test_allocate_five_days_three_cities() -> None:
    assert allocate_days(5, 3) == [2, 2, 1]


def test_parse_kerala_circuit_strips_state() -> None:
    cities = parse_city_names(
        "Munnar, Thekkady, Alappuzha in Kerala",
        "Plan a trip to Munnar, Thekkady and Alappuzha in Kerala",
    )
    assert cities == ["Munnar", "Thekkady", "Alappuzha"]


def test_corridor_orders_nearest_neighbor_from_first_city() -> None:
    from app.geo.destinations import order_cities_corridor

    cities = [
        {"query": "Munnar", "name": "Munnar", "lat": 10.0889, "lng": 77.0595},
        {"query": "Alappuzha", "name": "Alappuzha", "lat": 9.4981, "lng": 76.3388},
        {"query": "Thekkady", "name": "Thekkady", "lat": 9.6031, "lng": 77.1615},
    ]
    ordered = order_cities_corridor(cities)
    assert [row["query"] for row in ordered] == ["Munnar", "Thekkady", "Alappuzha"]


def test_rejects_far_hub_that_does_not_match_query() -> None:
    from app.geo.destinations import accept_geocoded_city

    munnar = {"query": "Munnar", "name": "Munnar", "lat": 10.0889, "lng": 77.0595}
    hyderabad = {
        "lat": 17.3850,
        "lng": 78.4867,
        "name": "Hyderabad, Telangana, India",
    }
    assert not accept_geocoded_city("Thekkady", hyderabad, [munnar])
    assert accept_geocoded_city(
        "Thekkady",
        {"lat": 9.6031, "lng": 77.1615, "name": "Kumily, Kerala, India"},
        [munnar],
    )
    assert not accept_geocoded_city(
        "Ooty",
        {"lat": 22.5726, "lng": 88.3639, "name": "Kolkata, West Bengal, India"},
        [],
    )
    assert query_matches_place_name("Ooty", "Udhagamandalam, Tamil Nadu, India")
    assert query_matches_place_name("Coonoor", "Coonoor, Tamil Nadu, India")


def test_geocode_picker_rejects_unrelated_hub() -> None:
    from app.providers.mapbox_geocoding import pick_geocode_feature

    features = [
        {"text": "Kolkata", "place_name": "Kolkata, West Bengal, India", "center": [88.36, 22.57], "place_type": ["place"], "context": [{"id": "country.1", "short_code": "in"}]},
        {"text": "Ooty", "place_name": "Ooty, Tamil Nadu, India", "center": [76.69, 11.41], "place_type": ["place"], "context": [{"id": "country.1", "short_code": "in"}]},
    ]
    picked = pick_geocode_feature(features, "Ooty", country="in")
    assert picked is not None
    assert picked["text"] == "Ooty"
    assert pick_geocode_feature(features[:1], "Ooty", country="in") is None
