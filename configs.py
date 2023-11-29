from os import environ
from json import loads
from typing import Literal
class configurations:
    bot_version = 'v0.10' # ignore
    logging_level: Literal['debug', 'info', 'warning', 'error', 'critical'] = environ.get('logging_level', 'info').lower()

    bot_token = environ.get('bot_token', 'replace_with_your_own_token')
    bot_support_server = environ.get('bot_support_server', 'https://discord.gg/')
    dev_ids = list(map(int, environ.get('dev_ids', '806432782111735818, 906844267870314577').split(', ')))
    dev_guild_id = int(environ.get('dev_guild_id', '1070724751284256939'))
    beta = environ.get('closed_beta', 'NO') == "YES"

    max_global_ratelimit = 2
    default_maintenance_status = False  # ignore

    using_sentry = environ.get('USING_SENTRY', '') == "YES"
    sentry_dsn = environ.get('SENTRY_DSN', 'leave_blank_if_not_using_sentry')

    screenshotapi = environ.get('SCREENSHOT_API_URL', 'https://example.com/replace/with/your/own/endpoint/')
    screenshotsecret = environ.get("SCREENSHOT_API_SECRET", 'blablablathisisaAPIkey')
    database_url = environ.get("DATABASE_URL", "https://example.com/")
    database_secret = environ.get("DATABASE_SECRET", 'APIkey')
    unshortensecret = environ.get("UNSHORTEN_API_SECRET", "apikey_goes_here")
    unshortenapi = environ.get("UNSHORTEN_API_URL", "https://example.com/replace/with/your/own/endpoint/")
    
    rapidapi_key = environ.get("RAPIDAPI_KEY", "APIkey")
    # webresolverapi = environ.get("WEBRESOLVERNL_API_KEY", "replace_with_your_own_api_key")
    bardapi_1psid_token = environ.get("BARD__Secure-1PSID", "replace_with_your_own_token")
    bardapi_1psidts_token = environ.get("BARD__Secure-1PSIDTS", "replace_with_your_own_token")

    mongo_uri = environ.get("mongo_uri", "replace_with_your_own_mongo_uri")

class assets:
    google_bard_avatar = "https://cdn.discordapp.com/attachments/1143096931569107005/1143098606161772615/Google_Bard_logo.svg.png"
    utils_bot_banner = "https://media.discordapp.net/attachments/1143096931569107005/1169530235155386449/Presentation1.png"

class text:
    blacklisted = "Dear {user},\n\nWe hope this message finds you well. We regret to inform you that {subject} has been flagged and blacklisted on our Discord bot due to {reason}. This decision was made in accordance with our [bot/server] policies to ensure a fair and enjoyable environment for all users.\n\nIf you believe this action was taken in error or if you would like to appeal, we encourage you to join our official support server. Our support team will review your case promptly.\n\nPlease note that any misuse of the appeal process may result in further action. We appreciate your understanding and cooperation in this matter.\n\nThank you for your attention to this issue.\n\nBest regards, utils-bot dev team."
    unblacklisted = "Dear {user},\n\nWe hope this message finds you well. We are writing to inform you that, following a careful review of your appeal, {subject} has been successfully unblacklisted on our Discord bot.\n\n{subject} got unblacklisted because: {reason}\n\nWe appreciate your cooperation throughout this process and want to assure you that our team takes each case seriously. If you have any questions or concerns, please feel free to reach out to us in the support server or through our support channels.\n\nThank you for your understanding, and we look forward to having you back as a valued member of our community.\n\nBest regards, utils-bot."