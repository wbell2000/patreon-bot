import json
import httpx
from bs4 import BeautifulSoup
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

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"Error parsing HTML from {creator_url}: {e}")
        return None

    tiers_data = []
    tier_buttons = soup.find_all('a', attrs={'data-tag': 'patron-checkout-continue-button'})
    for button in tier_buttons:
        aria_label = button.get('aria-label', '')
        if not aria_label:
            continue
        tier_name = ' '.join(aria_label.split()[:-1])
        is_disabled = button.get('aria-disabled') == 'true'
        btn_div = button.find('div', class_='cm-oHFIQB')
        button_text = btn_div.get_text(strip=True) if btn_div else ''
        if is_disabled or button_text == 'Sold Out':
            tier_status = 'sold_out'
        elif button_text == 'Join':
            tier_status = 'available'
        else:
            tier_status = 'unknown'
        if tier_name:
            tiers_data.append({'name': tier_name, 'status': tier_status})
    return tiers_data

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

async def main(request, env, ctx):
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
