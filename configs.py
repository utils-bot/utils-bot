from os import environ
class configurations:
    bot_version = 'v0.3.7' # ignore
    bot_token = environ.get('bot_token') 
    owner_ids = [806432782111735818]
    owner_guild_id = 1070724751284256939
    beta = True
    max_global_ratelimit = 2
    default_maintenance_status = False  # ignore
    not_builder = bool(environ.get('not_builder', ''))
    screenshotapi = environ.get('SCREENSHOT_API_URL', 'https://example.com/replace/with/your/own/endpoint/')
    screenshotsecret = environ.get("SCREENSHOT_API_SECRET", 'blablablathisisaAPIkey')
    is_replit = environ.get("IS_REPLIT", "NO") == "YES"
    no_git_automation = environ.get("NO_GIT_AUTOMATION", "NO") == "YES"
    database_url = environ.get("DATABASE_URL", "https://example.com/")
    database_secret = environ.get("DATABASE_SECRET", 'APIkey')