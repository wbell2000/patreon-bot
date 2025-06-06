// Cloudflare Worker: Patreon Tier Alerter (KV-based)
// - Config and alert cache are stored in KV
// - SMS sent via Twilio
// - Designed for Cron Triggers

import { DOMParser } from "linkedom";

export default {
  async scheduled(event, env, ctx) {
    // 1. Load config from KV
    const configRaw = await env.PATREON_CONFIG.get('config');
    if (!configRaw) {
      console.error('No config found in KV!');
      return;
    }
    const config = JSON.parse(configRaw);

    // 2. For each creator, scrape and check tiers
    for (const creator of config.creators) {
      const tiers = await scrapePatreonTiers(creator.url, config.user_agent);
      if (!tiers) continue;
      const alerts = await checkTiers(tiers, creator, env.PATREON_ALERT_CACHE);
      if (alerts.length > 0) {
        await sendAlerts(alerts, config.sms_settings, env);
      }
    }
  },
};

// --- Patreon Scraper ---
async function scrapePatreonTiers(url, userAgent) {
  try {
    const resp = await fetch(url, { headers: { 'User-Agent': userAgent } });
    if (!resp.ok) return null;
    const html = await resp.text();
    // Use DOMParser to extract tier info
    const doc = new DOMParser().parseFromString(html, 'text/html');
    // Adjust selectors as needed for Patreon
    const tierEls = doc.querySelectorAll('a[data-tag="patron-checkout-continue-button"]');
    const tiers = [];
    tierEls.forEach(el => {
      const ariaLabel = el.getAttribute('aria-label') || '';
      const tierName = ariaLabel.split(' ').slice(0, -1).join(' ');
      const disabled = el.getAttribute('aria-disabled') === 'true';
      let buttonText = '';
      // Patreon may have a div inside the button for text
      el.childNodes.forEach(child => {
        if (child.nodeType === 3) buttonText += child.textContent.trim();
        if (child.nodeType === 1) buttonText += child.textContent.trim();
      });
      let status = 'unknown';
      if (disabled || buttonText === 'Sold Out') status = 'sold_out';
      else if (buttonText === 'Join') status = 'available';
      tiers.push({ name: tierName, status });
    });
    return tiers;
  } catch (e) {
    console.error('Error scraping Patreon:', e);
    return null;
  }
}

// --- Tier Checker ---
async function checkTiers(scrapedTiers, creator, alertCacheKV) {
  const newlyAvailable = [];
  const scrapedMap = {};
  scrapedTiers.forEach(t => scrapedMap[t.name.toLowerCase()] = t);
  for (const tierName of creator.tiers_to_watch) {
    const cacheKey = `${creator.name}_${tierName}`;
    const found = scrapedMap[tierName.toLowerCase()];
    if (found && found.status === 'available') {
      const alerted = await alertCacheKV.get(cacheKey);
      if (!alerted) {
        newlyAvailable.push({ creator_name: creator.name, tier_name: tierName, url: creator.url });
        await alertCacheKV.put(cacheKey, '1');
      }
    } else {
      // Reset alert cache if not available
      await alertCacheKV.delete(cacheKey);
    }
  }
  return newlyAvailable;
}

// --- Alert Sender (Twilio) ---
async function sendAlerts(alerts, smsConfig, env) {
  if (!alerts.length) return;
  // Log alerts
  alerts.forEach(alert => {
    console.log(`ALERT: Tier "${alert.tier_name}" for creator "${alert.creator_name}" is now available! ${alert.url}`);
  });
  // Send SMS via Twilio
  if (smsConfig.provider === 'twilio') {
    const { twilio_account_sid, twilio_auth_token, twilio_from_number, recipient_phone_number } = smsConfig;
    if (!twilio_account_sid || !twilio_auth_token || !twilio_from_number || !recipient_phone_number) {
      console.error('Twilio config incomplete.');
      return;
    }
    for (const alert of alerts) {
      const body = `Patreon Alert: Tier '${alert.tier_name}' for creator '${alert.creator_name}' is now available! ${alert.url}`;
      const creds = btoa(`${twilio_account_sid}:${twilio_auth_token}`);
      await fetch(`https://api.twilio.com/2010-04-01/Accounts/${twilio_account_sid}/Messages.json`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${creds}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          From: twilio_from_number,
          To: recipient_phone_number,
          Body: body,
        }),
      });
    }
  }
}

// --- Notes ---
// - Set up two KV namespaces: PATREON_CONFIG (for config), PATREON_ALERT_CACHE (for alert state)
// - Store your config JSON in PATREON_CONFIG with key 'config'
// - Add your Twilio credentials to the config in KV
// - Use Wrangler to bind KV namespaces in wrangler.toml
// - Set up a Cron Trigger in wrangler.toml for periodic checks 