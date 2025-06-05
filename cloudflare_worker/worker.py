import json
import httpx
from html.parser import HTMLParser
from patreon_tier_alerter.src.alerter import check_tiers

# Global cache used across invocations
alerted_tiers_cache = {}

async def scrape_patreon_page_async(creator_url: str, user_agent: str, client: httpx.AsyncClient):
    """Asynchronously fetch and parse a Patreon creator page."""
    headers = {"User-Agent": user_agent}
    try:
        resp = await client.get(creator_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as e:
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
        parser.feed(resp.text)
    except Exception as e:
        print(f"Error parsing HTML from {creator_url}: {e}")
        return None

    return parser.tiers

async def send_sms_alerts_async(alerts_to_send: list, env: dict, client: httpx.AsyncClient):
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
        try:
            await client.post(sms_url, json=payload, timeout=10)
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
    async with httpx.AsyncClient() as client:
        for creator in creators:
            scraped = await scrape_patreon_page_async(creator.get("url"), user_agent, client)
            if scraped is None:
                continue
            new_alerts = check_tiers(scraped, creator, alerted_tiers_cache)
            alerts.extend(new_alerts)
        await send_sms_alerts_async(alerts, env, client)
    return {"alerts": alerts}


async def on_fetch(request, env, ctx):
    """Cloudflare Workers fetch handler."""
    return await main(request, env)
