import os

import httpx


def main() -> None:
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    webhook_url = os.environ["TELEGRAM_WEBHOOK_URL"]
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

    response = httpx.post(
        f"https://api.telegram.org/bot{bot_token}/setWebhook",
        json={"url": webhook_url, "secret_token": secret},
        timeout=30.0,
    )
    response.raise_for_status()
    print(response.text)


if __name__ == "__main__":
    main()
