import pytest
import json
import urllib.request

from cloudflare_worker.worker import (
    scrape_patreon_page_async,
    send_sms_alerts_async,
    on_fetch,
)

@pytest.mark.asyncio
async def test_scrape_patreon_page_async_parses_tier(monkeypatch):
    html = (
        '<a data-tag="patron-checkout-continue-button" '
        'aria-label="Cool Tier Join">'
        '<div class="cm-oHFIQB">Join</div></a>'
    )

    class FakeResp:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return html.encode()

    def fake_urlopen(req, timeout=10):
        return FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    tiers = await scrape_patreon_page_async("http://example.com", "UA")

    assert tiers == [{"name": "Cool Tier", "status": "available"}]

@pytest.mark.asyncio
async def test_send_sms_alerts_async_posts(monkeypatch):
    recorded = {}

    class FakeResp:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b""

    def fake_urlopen(req, timeout=10):
        recorded["url"] = req.full_url
        recorded["json"] = json.loads(req.data.decode())
        return FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    env = {
        "SMS_API_URL": "http://sms.local",
        "SMS_API_TOKEN": "token",
        "RECIPIENT_PHONE_NUMBER": "123",
    }
    alerts = [{"tier_name": "T", "creator_name": "C", "url": "u"}]
    await send_sms_alerts_async(alerts, env)

    assert recorded["url"] == "http://sms.local"
    assert recorded["json"]["to"] == "123"
    assert recorded["json"]["token"] == "token"


@pytest.mark.asyncio
async def test_on_fetch_returns_alerts(monkeypatch):
    env = {"CONFIG_JSON": json.dumps({"creators": []})}
    result = await on_fetch(None, env, None)
    assert result == {"alerts": []}
