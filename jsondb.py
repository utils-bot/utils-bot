import json
from os import path
def get_whitelist() -> list:
    if not path.exists('whitelist.json'):
        with open('whitelist.json', 'w+') as f:
            json.dump({'whitelisted_beta_users': []}, f)
    with open('whitelist.json', 'r') as f:
        database = json.load(f)
    return database.get('whitelisted_beta_users', [])

def update_whitelist(id: int, add: bool = True) -> bool:
    if not path.exists('whitelist.json'):
        with open('whitelist.json', 'w+') as f:
            json.dump({'whitelisted_beta_users': []}, f)
    database = get_whitelist()
    if add:
        if id not in database:
            database.append(id)
    else:
        if id in database:
            database.remove(id)
    with open('whitelist.json', 'w') as f:
        json.dump({'whitelisted_beta_users': database}, f)
    return True

def beta_check(user: int, beta_bool: bool) -> bool:
    if not beta_bool:
        return True
    return user in get_whitelist()
