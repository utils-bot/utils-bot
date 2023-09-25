from os import environ
class configurations:
    bot_version = 'v0.7.1' # ignore
    bot_token = environ.get('bot_token', 'replace_with_your_own_token')
    bot_support_server = environ.get('bot_support_server', 'https://discord.gg/')
    owner_ids = [806432782111735818]
    owner_guild_id = 1070724751284256939
    beta = False
    max_global_ratelimit = 2
    default_maintenance_status = False  # ignore
    using_sentry = environ.get('USING_SENTRY', 'leave_blank_for_false/anything_else_for_true') == "YES"
    sentry_dsn = environ.get('SENTRY_DSN', 'leave_blank_if_not_using_sentry')
    screenshotapi = environ.get('SCREENSHOT_API_URL', 'https://example.com/replace/with/your/own/endpoint/')
    screenshotsecret = environ.get("SCREENSHOT_API_SECRET", 'blablablathisisaAPIkey')
    database_url = environ.get("DATABASE_URL", "https://example.com/")
    database_secret = environ.get("DATABASE_SECRET", 'APIkey')
    rapidapi_key = environ.get("RAPIDAPI_KEY", "APIkey")
    unshortensecret = environ.get("UNSHORTEN_API_SECRET", "apikey_goes_here")
    unshortenapi = environ.get("UNSHORTEN_API_URL", "https://example.com/replace/with/your/own/endpoint/")
    webresolverapi = environ.get("WEBRESOLVERNL_API_KEY", "replace_with_your_own_api_key")
    bardapi_1psid_token = environ.get("BARDAPI_TOKEN", "replace_with_your_own_token")


class assets:
    google_bard_avatar = "https://cdn.discordapp.com/attachments/1143096931569107005/1143098606161772615/Google_Bard_logo.svg.png"