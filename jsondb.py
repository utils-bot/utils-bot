import json
from os import path
from logger import ilog
def get_whitelist() -> list:
    if not path.exists('whitelist.json'):
        with open('whitelist.json', 'w+') as f:
            json.dump({'whitelisted_beta_users': []}, f)
    with open('whitelist.json', 'r') as f:
        database = json.load(f)
    return database.get('whitelisted_beta_users', [])

def check_bot_version(to_compare: str) -> str:
    if not path.exists('version.json'):
        with open('version.json', 'w+') as f:
            json.dump({'current_version': to_compare}, f)
        return True
    with open('version.json', 'r') as f:
        version = json.load(f)
    return version.get('current_version') == to_compare

def update_whitelist(user: int, add: bool = True) -> bool:
    ilog(f'Whitelist updated for user {user} -> {add}', 'whitelist', 'warning')
    if not path.exists('whitelist.json'):
        with open('whitelist.json', 'w+') as f:
            json.dump({'whitelisted_beta_users': []}, f)
    database = set(get_whitelist())
    database.add(user) if add else database.remove(user) if user in database else None
    database = list(database)
    with open('whitelist.json', 'w') as f:
        json.dump({'whitelisted_beta_users': database}, f)
    return True

def beta_check(user: int, beta_bool: bool) -> bool:
    if not beta_bool:
        return True
    return user in get_whitelist()
