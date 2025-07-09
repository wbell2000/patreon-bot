import json
import requests
from html.parser import HTMLParser
import time
import boto3
from twilio.rest import Client
import os

# --- HTML Structure Assumptions (to be filled/verified by inspection) ---
# Tier container selector: e.g., 'div[data-testid="tier-card"]' (This is a guess, common pattern for cards)
# Tier name selector within container: e.g., 'h2[data-testid="tier-title"], h3[data-testid="tier-title"]' (Guessing h2 or h3 for titles)
# Tier availability indicators:
#   - Join button text/selector: e.g., 'button[data-testid="join-button"], a[data-testid="join-button"]' (Guessing button or link for join)
#   - "Join" or "Select" text within button: Check button's text content.
#   - Sold out text/selector: e.g., 'span:contains("Sold out"), div:contains("No longer available")' (Guessing common sold out texts)
#   - Class for disabled/sold out: e.g., 'button[disabled], .sold-out-class' (Common patterns for disabled elements)
# -------------------------------------------------------------------------

alerted_tiers_cache = {} # Global cache for alerted tiers

def scrape_patreon_page(creator_url: str, user_agent: str):
    """Fetches a Patreon creator's page, parses it, and extracts tier information.

    Args:
        creator_url (str): The URL of the Patreon creator's page.
        user_agent (str): The User-Agent string for the request.

    Returns:
        list: A list of dictionaries, where each dictionary represents a tier
              (e.g., {'name': 'Tier Name', 'status': 'available'}).
              Returns None if a network error occurs or the page cannot be parsed.
              Returns an empty list if no tiers are found.
    """
    headers = {'User-Agent': user_agent}
    try:
        response = requests.get(creator_url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
    except requests.exceptions.RequestException as e:
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
            if tag == 'a' and attrs.get('data-tag') == 'patron-checkout-continue-button':
                aria_label = attrs.get('aria-label', '')
                if not aria_label:
                    return
                tier_name = ' '.join(aria_label.split()[:-1])
                disabled = attrs.get('aria-disabled') == 'true'
                self.current = {'name': tier_name, 'disabled': disabled, 'button': ''}
            elif self.current and tag == 'div' and attrs.get('class') == 'cm-oHFIQB':
                self.in_btn_div = True

        def handle_data(self, data):
            if self.current and self.in_btn_div:
                self.current['button'] += data.strip()

        def handle_endtag(self, tag):
            if tag == 'div' and self.in_btn_div:
                self.in_btn_div = False
            elif tag == 'a' and self.current:
                text = self.current.get('button', '')
                if self.current['disabled'] or text == 'Sold Out':
                    status = 'sold_out'
                elif text == 'Join':
                    status = 'available'
                else:
                    status = 'unknown'
                if self.current['name']:
                    self.tiers.append({'name': self.current['name'], 'status': status})
                self.current = None

    parser = TierParser()
    try:
        parser.feed(response.text)
    except Exception as e:  # Broad exception for parsing issues
        print(f"Error parsing HTML from {creator_url}: {e}")
        return None

    return parser.tiers


def check_tiers(scraped_tiers: list, creator_config: dict, alerted_tiers_cache: dict) -> list:
    """Checks scraped tiers against watched tiers and manages alert state.

    Args:
        scraped_tiers (list): List of tier dicts from scrape_patreon_page.
        creator_config (dict): Configuration for a single creator.
        alerted_tiers_cache (dict): Global cache for tracking alerted tiers.

    Returns:
        list: A list of newly available tiers that require alerting.
    """
    newly_available_alerts = []
    creator_name = creator_config['name']
    tiers_to_watch = creator_config.get('tiers_to_watch', []) # Ensure it's a list

    # Normalize scraped tier names for easier lookup (optional, but good for robustness)
    # And create a quick lookup map
    scraped_tiers_map = {tier.get('name', '').lower(): tier for tier in scraped_tiers}

    for tier_to_watch_name in tiers_to_watch:
        cache_key = f"{creator_name}_{tier_to_watch_name}"
        
        # Search for the tier_to_watch_name in scraped_tiers (case-insensitive)
        found_tier_info = scraped_tiers_map.get(tier_to_watch_name.lower())

        if found_tier_info:
            # Tier is found, check its status
            # Assuming 'available' is the status for an open tier.
            # This needs to be consistent with scrape_patreon_page's output.
            is_available = found_tier_info.get('status') == 'available'

            if is_available:
                if not alerted_tiers_cache.get(cache_key): # If not alerted before (or was False)
                    newly_available_alerts.append({
                        'creator_name': creator_name,
                        'tier_name': tier_to_watch_name, # Use original casing for alert
                        'url': creator_config['url']
                    })
                    alerted_tiers_cache[cache_key] = True
                    print(f"DEBUG: Tier '{tier_to_watch_name}' for {creator_name} is AVAILABLE. Added to alerts. Cache: {alerted_tiers_cache}")
                else:
                    print(f"DEBUG: Tier '{tier_to_watch_name}' for {creator_name} is available but already alerted. Cache: {alerted_tiers_cache}")
            else: # Tier found but not available
                if alerted_tiers_cache.get(cache_key): # Was previously alerted
                    print(f"DEBUG: Tier '{tier_to_watch_name}' for {creator_name} is NO LONGER available. Resetting cache. Cache before: {alerted_tiers_cache}")
                    alerted_tiers_cache[cache_key] = False
                else:
                    print(f"DEBUG: Tier '{tier_to_watch_name}' for {creator_name} is not available and was not alerted. Cache: {alerted_tiers_cache}")
        else:
            # Tier to watch is not found in scraped tiers
            if alerted_tiers_cache.get(cache_key): # Was previously alerted (and thus available)
                print(f"DEBUG: Tier '{tier_to_watch_name}' for {creator_name} was NOT FOUND (previously available). Resetting cache. Cache before: {alerted_tiers_cache}")
                alerted_tiers_cache[cache_key] = False
            else:
                print(f"DEBUG: Tier '{tier_to_watch_name}' for {creator_name} was not found and not alerted. Cache: {alerted_tiers_cache}")
                
    return newly_available_alerts


def send_alerts(alerts_to_send: list, sms_config: dict = None):
    """Prints alert messages to the console and sends SMS if configured.

    Args:
        alerts_to_send (list): A list of alert dictionaries.
        sms_config (dict, optional): Configuration for SMS sending. Defaults to None.
    """
    if not alerts_to_send:
        print("No new tier availabilities to report.")
        return

    # Print to console
    print("\n--- !!! NEW TIER ALERTS !!! ---")
    for alert in alerts_to_send:
        print(f"ALERT: Tier \"{alert['tier_name']}\" for creator \"{alert['creator_name']}\" is now available! Check at: {alert['url']}")
    print("--- !!! END OF ALERTS !!! ---")

    # Send SMS if configured
    if sms_config and sms_config.get("provider") == "aws_sns":
        print("\n--- Attempting to send SMS alerts via AWS SNS ---")
        aws_access_key_id = sms_config.get("aws_access_key_id")
        aws_secret_access_key = sms_config.get("aws_secret_access_key")
        aws_region = sms_config.get("aws_region")
        recipient_phone_number = sms_config.get("recipient_phone_number")

        placeholders_present = any([
            aws_access_key_id == "YOUR_AWS_ACCESS_KEY_ID",
            aws_secret_access_key == "YOUR_AWS_SECRET_ACCESS_KEY",
            aws_region == "YOUR_AWS_REGION",
            recipient_phone_number == "YOUR_RECIPIENT_PHONE_NUMBER",
        ])

        if not all([aws_access_key_id, aws_secret_access_key, aws_region, recipient_phone_number]) or placeholders_present:
            if not all([aws_access_key_id, aws_secret_access_key, aws_region, recipient_phone_number]):
                print("Warning: SMS configuration for AWS SNS is incomplete. Missing one or more of: Access Key ID, Secret Access Key, Region, or Recipient Phone Number. Cannot send SMS.")
            if placeholders_present:
                print("Warning: SMS configuration contains placeholder values. Please update your config.json.")
            return

        try:
            sns_client = boto3.client(
                "sns",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
        except Exception as e:
            print(f"Error initializing AWS SNS client: {e}")
            return

        for alert in alerts_to_send:
            message = f"Patreon Alert: Tier '{alert['tier_name']}' for creator '{alert['creator_name']}' is now available! Check at: {alert['url']}"
            # Truncate message if it's too long for SNS (max 1600 chars, but SMS itself is shorter)
            # Standard GSM-7 SMS is 160 chars, UTF-8 is 70 chars.
            # Let's aim for a reasonable limit, e.g. 320 chars (2 SMS segments)
            if len(message) > 320: 
                message = message[:317] + "..."

            try:
                response = sns_client.publish(
                    PhoneNumber=recipient_phone_number,
                    Message=message,
                    MessageAttributes={
                        'AWS.SNS.SMS.SMSType': {
                            'DataType': 'String',
                            'StringValue': 'Transactional'
                        }
                    }
                )
                print(f"SMS sent for tier '{alert['tier_name']}' to {recipient_phone_number}! Message ID: {response.get('MessageId')}")
            except Exception as e:
                print(f"Error sending SMS for tier '{alert['tier_name']}': {e}")
        print("--- SMS Sending Process Complete ---")
    elif sms_config and sms_config.get("provider") == "twilio":
        print("\n--- Attempting to send SMS alerts via Twilio ---")
        account_sid = sms_config.get("twilio_account_sid")
        auth_token = sms_config.get("twilio_auth_token")
        from_number = sms_config.get("twilio_from_number")
        recipient_phone_number = sms_config.get("recipient_phone_number")

        placeholders_present = any([
            account_sid == "YOUR_TWILIO_ACCOUNT_SID",
            auth_token == "YOUR_TWILIO_AUTH_TOKEN",
            from_number == "YOUR_TWILIO_PHONE_NUMBER (e.g., +15551234567)",
            recipient_phone_number == "YOUR_RECIPIENT_PHONE_NUMBER (e.g., +11234567890)",
        ])

        if not all([account_sid, auth_token, from_number, recipient_phone_number]) or placeholders_present:
            if not all([account_sid, auth_token, from_number, recipient_phone_number]):
                print("Warning: SMS configuration for Twilio is incomplete. Missing one or more required fields.")
            if placeholders_present:
                print("Warning: SMS configuration contains placeholder values. Please update your config.json.")
            return

        try:
            client = Client(account_sid, auth_token)
        except Exception as e:
            print(f"Error initializing Twilio client: {e}")
            return

        for alert in alerts_to_send:
            message = (
                f"Patreon Alert: Tier '{alert['tier_name']}' for creator '{alert['creator_name']}' "
                f"is now available! Check at: {alert['url']}"
            )
            if len(message) > 320:
                message = message[:317] + "..."
            try:
                sent = client.messages.create(body=message, from_=from_number, to=recipient_phone_number)
                print(f"SMS sent for tier '{alert['tier_name']}' to {recipient_phone_number}! SID: {sent.sid}")
            except Exception as e:
                print(f"Error sending SMS for tier '{alert['tier_name']}': {e}")
        print("--- SMS Sending Process Complete ---")
    elif sms_config and sms_config.get("provider") == "textbelt":
        print("\n--- Attempting to send SMS alerts via Textbelt ---")
        textbelt_api_key = sms_config.get("textbelt_api_key", "textbelt")
        recipient_phone_number = sms_config.get("recipient_phone_number")

        placeholders_present = any([
            textbelt_api_key == "YOUR_TEXTBELT_API_KEY",
            recipient_phone_number == "YOUR_RECIPIENT_PHONE_NUMBER",
        ])

        if not all([textbelt_api_key, recipient_phone_number]) or placeholders_present:
            if not all([textbelt_api_key, recipient_phone_number]):
                print("Warning: SMS configuration for Textbelt is incomplete. Missing API key or recipient phone number.")
            if placeholders_present:
                print("Warning: SMS configuration contains placeholder values. Please update your config.json.")
            return

        for alert in alerts_to_send:
            message = (
                f"Patreon Alert: Tier '{alert['tier_name']}' for creator '{alert['creator_name']}' "
                f"is now available! Check at: {alert['url']}"
            )
            if len(message) > 320:
                message = message[:317] + "..."
            try:
                resp = send_textbelt_sms(recipient_phone_number, message, textbelt_api_key)
                if resp.get("success"):
                    print(f"SMS sent for tier '{alert['tier_name']}' to {recipient_phone_number}! Textbelt ID: {resp.get('textId')}")
                else:
                    print(f"Error sending SMS for tier '{alert['tier_name']}': {resp.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Error sending SMS for tier '{alert['tier_name']}': {e}")
        print("--- SMS Sending Process Complete ---")
    elif sms_config:
        print(f"SMS provider '{sms_config.get('provider')}' is configured but not supported. No SMS will be sent.")
    else:
        print("SMS configuration not provided. Skipping SMS alerts.")


def send_textbelt_sms(phone, message, key="textbelt"):
    """Send an SMS using the Textbelt API."""
    import requests
    payload = {
        'phone': phone,
        'message': message,
        'key': key,
    }
    response = requests.post('https://textbelt.com/text', data=payload)
    return response.json()


def main():
    """Main function to run the Patreon Tier Alerter bot."""
    print("Starting Patreon Tier Alerter...")

    # Update these paths to point to the correct location
    config_path_primary = "patreon_tier_alerter/config/config.json"
    config_path_secondary = "../patreon_tier_alerter/config/config.json" # For running directly from src
    
    config = load_config(config_path_primary)
    if config is None:
        print(f"Attempting to load config from alternative path: {config_path_secondary}")
        config = load_config(config_path_secondary)

    if config is None:
        print("Error: Configuration could not be loaded. Exiting.")
        return

    creators_to_monitor = config.get('creators', [])
    check_interval_seconds = config.get('check_interval_seconds', 3600)
    user_agent = config.get('user_agent', 'Patreon Tier Alerter Bot/1.0')

    if not creators_to_monitor:
        print("No creators configured to monitor. Please check your config.json. Exiting.")
        return

    # alerted_tiers_cache is already global, so it's implicitly used by check_tiers
    sms_settings_from_config = config.get('sms_settings')

    print(f"Configuration loaded. Monitoring {len(creators_to_monitor)} creator(s).")
    print(f"Check interval: {check_interval_seconds} seconds.")
    print(f"User-Agent: {user_agent}")
    if sms_settings_from_config and sms_settings_from_config.get('provider'):
        print(f"SMS alerts configured via: {sms_settings_from_config.get('provider')}")
        placeholders_present = any([
            sms_settings_from_config.get("aws_access_key_id") == "YOUR_AWS_ACCESS_KEY_ID",
            sms_settings_from_config.get("aws_secret_access_key") == "YOUR_AWS_SECRET_ACCESS_KEY",
            sms_settings_from_config.get("aws_region") == "YOUR_AWS_REGION",
            sms_settings_from_config.get("recipient_phone_number") == "YOUR_RECIPIENT_PHONE_NUMBER",
        ])
        if placeholders_present:
            print("WARNING: SMS configuration contains placeholder values. SMS sending may fail until these are updated in config.json.")
    else:
        print("SMS alerts not configured or provider not specified.")

    while True:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting new check cycle...")
        
        for creator_config in creators_to_monitor:
            creator_name = creator_config.get('name', 'Unknown Creator')
            creator_url = creator_config.get('url')

            if not creator_url:
                print(f"Skipping creator '{creator_name}' due to missing URL.")
                continue

            print(f"Checking creator: {creator_name} at {creator_url}")
            
            scraped_tiers = None
            try:
                scraped_tiers = scrape_patreon_page(creator_url, user_agent)
            except Exception as e:
                print(f"An unexpected error occurred during scraping for {creator_name}: {e}")
                # Continue to the next creator even if one fails catastrophically during scrape function
                time.sleep(5) # Still sleep before next creator
                continue

            if scraped_tiers is None:
                print(f"Scraping failed for {creator_name} (returned None). Skipping tier check for this creator.")
            else:
                print(f"Successfully scraped {len(scraped_tiers)} tier(s) for {creator_name}.")
                newly_available_alerts = check_tiers(scraped_tiers, creator_config, alerted_tiers_cache)
                send_alerts(newly_available_alerts, sms_config=sms_settings_from_config)
            
            # Polite delay between requests to different creators
            print(f"Waiting 5 seconds before next creator...")
            time.sleep(5) 

        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Check cycle complete.")
        print(f"Next check in {check_interval_seconds // 60} minutes (at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + check_interval_seconds))}).")
        time.sleep(check_interval_seconds)


def load_config(config_path="config/config.json"):
    """Loads the configuration from a JSON file.

    Args:
        config_path (str): The path to the configuration file.

    Returns:
        dict: The parsed configuration, or None if an error occurred.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file at {config_path}")
        return None

if __name__ == '__main__':
    # The if __name__ == '__main__' block should simply call main().
    # Previous code attempted to load a configuration file here, which could
    # trigger a spurious "file not found" warning when the script was executed
    # from a different working directory. Configuration loading is already
    # handled inside main(), so we only need to invoke it.
    main()
