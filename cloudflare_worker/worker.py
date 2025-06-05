import json
import asyncio
import urllib.request
from html.parser import HTMLParser

# Python workers run on Pyodide, which does not include third-party packages by
# default. Patch HTTP libraries to use the runtime's fetch API if available.
try:  # noqa: E402 - ensure patching before importing urllib
    import pyodide_http

    pyodide_http.patch_all()
except Exception:  # pragma: no cover - patching is best-effort
    pass

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from patreon_tier_alerter.src.alerter import check_tiers

# Global cache used across invocations
alerted_tiers_cache = {}

async def scrape_patreon_page_async(creator_url: str, user_agent: str):
    """Asynchronously fetch and parse a Patreon creator page."""
    headers = {"User-Agent": user_agent}

    def _fetch() -> str:
        req = urllib.request.Request(creator_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode()

    try:
        text = await asyncio.to_thread(_fetch)
    except Exception as e:
        print(f"Error fetching URL {creator_url}: {e}")
        return None

    class TierParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tiers = []
            self.current = None
            self.in_btn_div = False

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "a" and attrs.get("data-tag") == "patron-checkout-continue-button":
                aria_label = attrs.get("aria-label", "")
                if not aria_label:
                    return
                tier_name = " ".join(aria_label.split()[:-1])
                disabled = attrs.get("aria-disabled") == "true"
                self.current = {"name": tier_name, "disabled": disabled, "button": ""}
            elif self.current and tag == "div" and attrs.get("class") == "cm-oHFIQB":
                self.in_btn_div = True

        def handle_data(self, data):
            if self.current and self.in_btn_div:
                self.current["button"] += data.strip()

        def handle_endtag(self, tag):
            if tag == "div" and self.in_btn_div:
                self.in_btn_div = False
            elif tag == "a" and self.current:
                text = self.current.get("button", "")
                if self.current["disabled"] or text == "Sold Out":
                    status = "sold_out"
                elif text == "Join":
                    status = "available"
                else:
                    status = "unknown"
                if self.current["name"]:
                    self.tiers.append({"name": self.current["name"], "status": status})
                self.current = None

    parser = TierParser()
    try:
        parser.feed(text)
    except Exception as e:
        print(f"Error parsing HTML from {creator_url}: {e}")
        return None

    return parser.tiers

async def send_sms_alerts_async(alerts_to_send: list, env: dict):
    """Send SMS alerts using a generic HTTP API."""
    sms_url = env.get("SMS_API_URL")
    sms_token = env.get("SMS_API_TOKEN")
    phone = env.get("RECIPIENT_PHONE_NUMBER")
    if not alerts_to_send or not all([sms_url, sms_token, phone]):
        return
    for alert in alerts_to_send:
        message = (
            f"Patreon Alert: Tier '{alert['tier_name']}' for creator '{alert['creator_name']}' "
            f"is now available! Check at: {alert['url']}"
        )
        payload = {"to": phone, "token": sms_token, "message": message}
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            sms_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
        except Exception as e:
            print(f"Error sending SMS: {e}")

async def main(request, env):
    """Entry point for the Cloudflare Worker."""
    config_text = env.get("CONFIG_JSON")
    if not config_text and hasattr(env, "KV_CONFIG"):
        config_text = await env.KV_CONFIG.get("config", "text")
    if not config_text:
        return {"error": "missing configuration"}
    config = json.loads(config_text)
    creators = config.get("creators", [])
    user_agent = config.get("user_agent", "Mozilla/5.0")
    alerts = []
    for creator in creators:
        scraped = await scrape_patreon_page_async(creator.get("url"), user_agent)
        if scraped is None:
            continue
        new_alerts = check_tiers(scraped, creator, alerted_tiers_cache)
        alerts.extend(new_alerts)
    await send_sms_alerts_async(alerts, env)
    return {"alerts": alerts}


async def on_fetch(request, env, ctx):
    """Cloudflare Workers fetch handler."""
    return await main(request, env)
