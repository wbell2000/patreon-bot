import json
import os
import sys

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from patreon_tier_alerter.src import alerter


class DummyResponse:
    def __init__(self, text="", status_code=200, json_data=None):
        self.text = text
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON payload")
        return self._json_data


def test_scrape_patreon_page_prefers_campaign_api(monkeypatch):
    creator_url = "https://www.patreon.com/c/example/membership"

    def fake_get(url, headers=None, timeout=10):
        if "api/campaigns/12345" in url:
            return DummyResponse(
                json_data={
                    "included": [
                        {
                            "type": "reward",
                            "attributes": {"title": "MICROBATCHES", "remaining": 2, "published": True},
                        },
                        {
                            "type": "reward",
                            "attributes": {"title": "WHISKEY DRUMMERS", "remaining": 0, "published": True},
                        },
                    ]
                }
            )
        return DummyResponse(text='<html><body><a href="/campaign/12345/">Campaign</a></body></html>')

    monkeypatch.setattr(alerter.requests, "get", fake_get)

    tiers = alerter.scrape_patreon_page(creator_url, "test-agent")
    by_name = {tier["name"]: tier["status"] for tier in tiers}

    assert by_name["MICROBATCHES"] == "available"
    assert by_name["WHISKEY DRUMMERS"] == "sold_out"


def test_scrape_patreon_page_uses_embedded_payload_when_api_unavailable(monkeypatch):
    creator_url = "https://www.patreon.com/c/example/membership"
    next_data_payload = {
        "included": [
            {
                "type": "reward",
                "attributes": {
                    "title": "The Mighty Gobble",
                    "remaining": 0,
                    "user_limit": 100,
                    "patron_count": 100,
                    "published": True,
                },
            },
            {
                "type": "reward",
                "attributes": {
                    "title": "Rare Breed",
                    "remaining": 3,
                    "user_limit": 10,
                    "patron_count": 7,
                    "published": True,
                },
            },
        ]
    }
    html = (
        "<html><body>"
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data_payload)}</script>'
        "</body></html>"
    )

    def fake_get(url, headers=None, timeout=10):
        if "api/campaigns/" in url:
            return DummyResponse(status_code=500)
        return DummyResponse(text=html)

    monkeypatch.setattr(alerter.requests, "get", fake_get)

    tiers = alerter.scrape_patreon_page(creator_url, "test-agent")
    by_name = {tier["name"]: tier["status"] for tier in tiers}

    assert by_name["The Mighty Gobble"] == "sold_out"
    assert by_name["Rare Breed"] == "available"
