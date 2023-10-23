import aiohttp, json
from os import path
from configs import configurations
DATABASE_URL = configurations.database_url
DATABASE_SECRET = configurations.database_secret

async def get_user_whitelist():
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': DATABASE_SECRET}
        async with session.get(f'{DATABASE_URL}/whitelist/user/get', headers=headers) as response:
            data = await response.json()
            return data['whitelisted_beta_users']

async def update_user_whitelist(user: int, add: bool = True):
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': DATABASE_SECRET}
        async with session.put(f'{DATABASE_URL}/whitelist/user/modify/{user}?status={add}', headers=headers) as response:
            data = await response.json()
            return data['success']

async def check_user_whitelist(user: int):
    if not configurations.beta:
        return True
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': DATABASE_SECRET}
        async with session.get(f'{DATABASE_URL}/whitelist/user/check/{user}', headers=headers) as response:
            data = await response.json()
            return data['whitelisted']
