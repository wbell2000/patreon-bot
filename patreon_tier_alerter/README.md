# Patreon Tier Alerter Bot

## Description

The Patreon Tier Alerter Bot is a Python application designed to monitor Patreon creator pages for the availability of specific membership tiers. When a desired tier becomes available, it sends an alert to the console. This is particularly useful for tiers that have limited slots or are not always open for new patrons.

## Features

*   Monitors multiple Patreon creators and specific tiers simultaneously.
*   Configurable check intervals to control how often pages are scraped.
*   Console-based alerts for newly available tiers.
*   Containerized with Docker for easy setup and deployment.
*   Customizable User-Agent for requests.

## Prerequisites

*   **Docker:** You must have Docker installed on your system to build and run this application. Visit [docker.com](https://www.docker.com/get-started) for installation instructions.
*   **Python and Pip:** Ensure you have Python 3 and pip installed.

## Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository-url>
    cd patreon-tier-alerter
    ```

2.  **Install dependencies:**
    Install the required Python packages using pip for running the bot locally:
    ```bash
    pip install -r requirements.txt
    ```
    These packages are only needed for local development. The Cloudflare
    Worker runtime does not support installing arbitrary dependencies.

## Setup and Configuration

Configuration for the bot is managed through the `config/config.json` file located within the project directory.

**1. Edit `config/config.json`:**

You need to edit this file to tell the bot which creators and tiers to monitor. Below is the structure of the `config.json` file with explanations:

```json
{
  "creators": [
    {
      "name": "CreatorNameExample1",
      "url": "https://www.patreon.com/ReplaceWithRealCreatorPageName1",
      "tiers_to_watch": ["Specific Tier Name Alpha", "Another Tier Beta"]
    },
    {
      "name": "CreatorNameExample2",
      "url": "https://www.patreon.com/ReplaceWithRealCreatorPageName2",
      "tiers_to_watch": ["Only This Tier Gamma"]
    }
  ],
  "check_interval_seconds": 3600,
  "user_agent": "Patreon Tier Alerter Bot/1.0 (YourNameOrProjectContact/YourPurpose)"
}
```

**Field Explanations:**

*   `creators` (list): An array of objects, where each object represents a Patreon creator to monitor.
    *   `name` (string): A descriptive name for the creator. This name is used in alert messages (e.g., "TestCreator1").
    *   `url` (string): The full URL to the creator's main Patreon page (e.g., `https://www.patreon.com/actualcreatorpagename`). This is the page where their tiers are listed.
    *   `tiers_to_watch` (list of strings): A list of the exact names of the tiers you want to be alerted for. These names must match the tier names on Patreon precisely (case-sensitive).
*   `check_interval_seconds` (integer): The frequency, in seconds, at which the bot will check the Patreon pages. For example, `3600` means the bot will check once every hour. Choose a reasonable interval to avoid excessive requests.
*   `user_agent` (string): The User-Agent string the bot will use when making HTTP requests to Patreon. It's good practice to customize this with your contact information or project purpose, e.g., `"Patreon Tier Alerter Bot/1.0 (yourname@example.com/PersonalUse)"`.

**Note:** The application was initialized with a sample `config/config.json`. You should edit this file directly with your desired configuration.

## SMS Alert Configuration

The bot supports sending SMS alerts via AWS Simple Notification Service (SNS) when a desired tier becomes available. To enable SMS alerts, you need to configure the `sms_settings` section in the `config/config.json` file.

```json
{
  // ... other configurations ...
  "sms_settings": {
    "provider": "aws_sns",
    "aws_access_key_id": "YOUR_AWS_ACCESS_KEY_ID",
    "aws_secret_access_key": "YOUR_AWS_SECRET_ACCESS_KEY",
    "aws_region": "YOUR_AWS_REGION (e.g., us-east-1)",
    "recipient_phone_number": "YOUR_RECIPIENT_PHONE_NUMBER (e.g., +11234567890)"
  }
}
```

**Field Explanations:**

*   `provider` (string): Specifies the SMS provider. Currently, only `"aws_sns"` is supported. This tells the bot to use AWS SNS for sending SMS messages.
*   `aws_access_key_id` (string): Your AWS Access Key ID. This is part of the credentials for an AWS IAM (Identity and Access Management) user. You can generate these credentials in the AWS Management Console under IAM.
*   `aws_secret_access_key` (string): Your AWS Secret Access Key. This is the other part of the credentials for an AWS IAM user. It's shown only once when you create an access key pair, so store it securely.
*   `aws_region` (string): The AWS region where your SNS service is configured (e.g., "us-east-1", "eu-west-2"). This is necessary for the AWS SDK to send requests to the correct regional endpoint.
*   `recipient_phone_number` (string): The phone number to which the SMS alerts will be sent. It should be in E.164 format (e.g., `+11234567890`).

**IMPORTANT:** Storing AWS credentials directly in `config.json` is convenient for personal use but is not recommended for production or shared environments. For better security, consider using environment variables or AWS IAM roles if deploying this script in an AWS environment.

### Testing SMS Alerts

After configuring your SMS settings (especially for AWS SNS):

1.  **Ensure Credentials are Correct:** Double-check your `aws_access_key_id`, `aws_secret_access_key`, `aws_region`, and `recipient_phone_number` in `config/config.json`. Ensure they are not placeholders.
2.  **Valid Recipient Number:** Make sure the `recipient_phone_number` is a valid phone number in E.164 format (e.g., `+11234567890`) that can receive SMS messages.
3.  **Trigger an Alert:**
    *   The easiest way to test is to temporarily modify your `config/config.json` to watch for a tier that you know is currently available on a Patreon page you are monitoring.
    *   Alternatively, you can adjust the `alerted_tiers_cache` logic in `alerter.py` for a one-time test if you are comfortable modifying the code (not recommended for normal use).
    *   Run the script: `python patreon_tier_alerter/src/alerter.py`
4.  **Check Console Output:** Look for messages indicating that an SMS was attempted (e.g., "SMS sent for tier..." or any error messages like "Error sending SMS...").
5.  **Check Your Phone:** Verify if you received the SMS message.
6.  **Troubleshooting:**
    *   If you don't receive an SMS, check the console output for errors from AWS SNS.
    *   Ensure the IAM user associated with your AWS credentials has the necessary permissions to publish to SNS (e.g., `sns:Publish`).
    *   Check your AWS SNS console for any delivery logs or errors for the message.
    *   Some regions or countries might have specific requirements for sending SMS (e.g., pre-registering sender IDs). For personal use to your own number, this is often less of an issue, but be aware of it if messages fail to deliver.

## How to Run (Using Docker)

These commands should be run from the root directory of the `patreon_tier_alerter` project (where the `Dockerfile` is located).

**1. Build the Docker Image:**

First, build the Docker image. This packages the application and its dependencies.

```bash
docker build -t patreon-tier-alerter .
```

**2. Run the Docker Container:**

Once the image is built, you can run it as a container.

*   **Using the built-in configuration:**
    If you edited the `config/config.json` file within the project directory *before* building the Docker image, that configuration is now part of the image.

    ```bash
    docker run -d --name patreon-alerter patreon-tier-alerter
    ```
    The `-d` flag runs the container in detached mode (in the background).

*   **Using a custom/external configuration (Recommended for flexibility):**
    This method allows you to manage your `config.json` outside the Docker image, making it easier to update without rebuilding the image.

    ```bash
    docker run -d --name patreon-alerter -v /path/to/your/local/config.json:/app/config/config.json patreon-tier-alerter
    ```
    **Important:** Replace `/path/to/your/local/config.json` with the absolute path to your `config.json` file on your local machine. For example, on Linux or macOS, this might be `/home/user/patreon_configs/config.json`, or on Windows, `C:\Users\YourUser\Documents\patreon_configs\config.json` (adjust Docker path syntax for Windows if needed, e.g., `//c/Users/...`).

**3. Viewing Logs:**

To see the bot's output, including alerts and status messages:

*   To view current logs and exit:
    ```bash
    docker logs patreon-alerter
    ```
*   To view live logs (follow mode):
    ```bash
    docker logs -f patreon-alerter
    ```
    Press `Ctrl+C` to stop following logs.

## How it Works (Briefly)

The bot operates by:
1.  Loading the configuration from `config/config.json`.
2.  Periodically making HTTP requests to the specified Patreon creator URLs using the `requests` library.
3.  Parsing the HTML content of these pages using `BeautifulSoup`.
4.  Attempting to identify tier elements, their names, and their availability status based on predefined (and somewhat guessed) HTML selectors.
5.  Comparing the found available tiers against the `tiers_to_watch` list in the configuration.
6.  If a watched tier becomes available and hasn't been alerted for recently, it prints an alert to the console.
7.  Sleeping for the configured `check_interval_seconds` before repeating the process.

## Deploying to Cloudflare Workers

An experimental Cloudflare Worker is included for running the tier checker
without managing your own server. You will need the [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) installed.

1.  Edit or provide a JSON configuration via the `CONFIG_JSON` environment variable or store it in a KV namespace named `KV_CONFIG` under the key `config`.
2.  Set SMS credentials (e.g. `SMS_API_URL`, `SMS_API_TOKEN` and `RECIPIENT_PHONE_NUMBER`) as Worker environment variables.
3.  Deploy with:
    ```bash
    wrangler publish
    ```
4.  Ensure your `wrangler.toml` includes `compatibility_flags = ["python_workers"]`.

The Worker uses an async HTTP client compatible with the runtime and cannot read local files. AWS SNS via `boto3` is **not** available; SMS must be sent through an HTTP API. Third-party Python packages are not supported, so only the standard library is available at runtime. `requirements.txt` is solely for running the bot locally.

## Important Notes / Limitations

*   **Web Scraping Reliance:** This bot relies on web scraping the structure of Patreon pages. **If Patreon significantly changes its website layout, the bot's ability to find tier information may break.** The HTML selectors used for scraping are based on observations at the time of writing and might need updates if issues arise.
*   **Selector Guesses:** The current HTML selectors in `src/alerter.py` for identifying tiers (names, availability, join buttons, sold-out status) are based on general web patterns and **may not be universally accurate for all Patreon pages or future Patreon designs.** If you encounter issues where tiers are not correctly identified, these selectors are the primary area to investigate and update.
*   **Be Respectful:** Set a reasonable `check_interval_seconds`. Very frequent checks (e.g., every few seconds or minutes) could put an undue load on Patreon's servers and may lead to your IP being rate-limited or blocked. This bot is intended for personal, considerate use.
*   **No Guarantee:** This tool is provided as-is, with no guarantee of functionality or accuracy. Use it at your own risk.
*   **Single Point of Failure:** If the script or the machine it's running on crashes, monitoring will stop.

## License
This project is released under the Apache 2.0 License.
