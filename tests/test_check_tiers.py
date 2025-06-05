import os
import sys
import pytest

# Ensure the package root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the check_tiers function from the package
from patreon_tier_alerter.src.alerter import check_tiers


def test_tier_available_first_time_alert_and_cache():
    creator_config = {
        "name": "CreatorX",
        "url": "http://example.com",
        "tiers_to_watch": ["Cool Tier"],
    }
    scraped_tiers = [{"name": "Cool Tier", "status": "available"}]
    cache = {}

    alerts = check_tiers(scraped_tiers, creator_config, cache)

    assert len(alerts) == 1
    assert alerts[0]["tier_name"] == "Cool Tier"
    assert cache.get("CreatorX_Cool Tier") is True


def test_tier_sold_out_resets_cache():
    creator_config = {
        "name": "CreatorX",
        "url": "http://example.com",
        "tiers_to_watch": ["Cool Tier"],
    }
    # Cache already indicates tier was available before
    cache = {"CreatorX_Cool Tier": True}
    scraped_tiers = [{"name": "Cool Tier", "status": "sold_out"}]

    alerts = check_tiers(scraped_tiers, creator_config, cache)

    assert alerts == []
    assert cache["CreatorX_Cool Tier"] is False


def test_tier_not_found_no_alert():
    creator_config = {
        "name": "CreatorX",
        "url": "http://example.com",
        "tiers_to_watch": ["Missing Tier"],
    }
    scraped_tiers = []
    cache = {}

    alerts = check_tiers(scraped_tiers, creator_config, cache)

    assert alerts == []
    assert cache == {}
