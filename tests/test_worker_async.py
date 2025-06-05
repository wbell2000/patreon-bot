import pytest
import httpx
import json

from cloudflare_worker.worker import scrape_patreon_page_async, send_sms_alerts_async

@pytest.mark.asyncio
async def test_scrape_patreon_page_async_parses_tier():
    html = (
        '<a data-tag="patron-checkout-continue-button" '
        'aria-label="Cool Tier Join">'
        '<div class="cm-oHFIQB">Join</div></a>'
    )

    async def handler(request: httpx.Request):
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        tiers = await scrape_patreon_page_async("http://example.com", "UA", client)

    assert tiers == [{"name": "Cool Tier", "status": "available"}]

@pytest.mark.asyncio
async def test_send_sms_alerts_async_posts(monkeypatch):
    recorded = {}

    async def handler(request: httpx.Request):
        recorded["url"] = str(request.url)
        recorded["json"] = json.loads(request.content.decode())
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        env = {
            "SMS_API_URL": "http://sms.local",
            "SMS_API_TOKEN": "token",
            "RECIPIENT_PHONE_NUMBER": "123",
        }
        alerts = [{"tier_name": "T", "creator_name": "C", "url": "u"}]
        await send_sms_alerts_async(alerts, env, client)

    assert recorded["url"] == "http://sms.local"
    assert recorded["json"]["to"] == "123"
    assert recorded["json"]["token"] == "token"
