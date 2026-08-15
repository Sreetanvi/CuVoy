from app.providers.osm_filters import (
    is_industrial_place,
    is_industrial_tags,
    is_residential_place,
    is_residential_tags,
    osm_display_name,
    should_drop_candidate,
)


def test_osm_display_name_prefers_name_then_name_en() -> None:
    assert osm_display_name({"name": "Meenakshi Temple", "name:en": "English"}) == "Meenakshi Temple"
    assert osm_display_name({"name:en": "Cubbon Park"}) == "Cubbon Park"
    assert osm_display_name({"amenity": "restaurant"}) is None


def test_rejects_industrial_factory_tags() -> None:
    assert is_industrial_tags(
        {"name": "Lion Brand Appalam Manufacturers", "industrial": "yes", "craft": "manufacturer"}
    )
    assert is_industrial_place("Lion Brand Appalam Manufacturers", "attraction")
    assert is_industrial_tags({"tourism": "museum", "office": "company"})
    assert is_industrial_tags({"tourism": "attraction", "man_made": "works"})
    assert is_industrial_place("Sterling Industries Pvt Ltd", "museum")
    assert is_industrial_place("City Steel Works", "historic")
    assert not is_industrial_tags({"name": "Meenakshi Temple", "historic": "temple"})


def test_rejects_residential_tags_and_hostel_operator() -> None:
    assert is_residential_tags({"tourism": "attraction", "building": "residential"})
    assert is_residential_tags({"amenity": "dormitory", "name": "Campus Block"})
    assert is_residential_tags({"amenity": "social_facility", "name": "Care Home"})
    assert is_residential_tags({"leisure": "park", "landuse": "residential"})
    assert is_residential_tags({"tourism": "attraction", "operator": "City Boys Hostel"})
    assert is_residential_tags({"tourism": "hostel", "name": "Backpackers"})
    assert not is_residential_tags({"name": "Meenakshi Temple", "historic": "temple"})


def test_rejects_residential_names_but_keeps_hotels() -> None:
    assert is_residential_place("Greenview Boys Hostel", "attraction")
    assert is_residential_place("Sri Sai PG", "poi")
    assert is_residential_place("Comfort P.G.", "lodging")
    assert is_residential_place("Lakeview Apartment", "attraction")
    assert is_residential_place("Oakwood Residency", "poi")
    assert is_residential_place("12, 4th Main", "attraction")
    assert not is_residential_place("Taj West End Hotel", "hotel")
    assert not is_residential_place("Seaside Resort Apartment", "resort")
    assert not is_residential_place("Hotel Lake Residency", "hotel")
    assert not is_residential_place("Lalbagh Botanical Garden", "park")
    assert should_drop_candidate("Sunrise Girls Hostel", "museum")
    assert not should_drop_candidate("Cubbon Park", "park")
