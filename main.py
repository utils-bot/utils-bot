"""---------------------------------------------
Check .env.example to setup the bot.
---------------------------------------------"""
from discord import Intents, Client, Interaction, Object, Embed, File, Game, Status, Member, Webhook
from discord.app_commands import CommandTree, Group, command, Choice, choices, describe, Range
from jsondb import check_bot_version, get_user_whitelist, update_user_whitelist, check_user_whitelist
import logging, json, typing, functools, traceback, asyncio, json
from aiohttp import ClientSession
from logger import CustomFormatter, ilog
from os import system
from time import time
from keep_alive import ka
from io import BytesIO
from configs import configurations
# from enum import Enum

discord_logger = logging.getLogger('discord')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
discord_logger.addHandler(ch)
del discord_logger

"""
NỎTES
- Embeds must include timestamp = datetime.now(), all Embed() object must have .set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar) with it.
"""

"""
-------------------------------------------------
DEFINING VARS
-------------------------------------------------
"""

    # ipinfo_api_key: str = environ.get('ipinfo_api_key', '')
    # chromedriver_path = environ.get('chromedriver_path', '/nix/store/i85kwq4r351qb5m7mrkl2grv34689l6b-chromedriver-108.0.5359.71/bin/chromedriver')

intents = Intents.default()
intents.members = True
# intents.message_content = True
client = Client(intents=intents)
tree = CommandTree(client)

async def antiblock(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    func = functools.partial(blocking_func, *args, **kwargs)
    return await client.loop.run_in_executor(None, func)

async def get_screenshot(url, resolution, delay, debugmsg: Webhook, api_url=configurations.screenshotapi, token=configurations.screenshotsecret):
    success = True
    error: str = ""
    params = {'resolution': resolution, 'delay': delay} #, 'authorization': token}
    headers = {'url': url, 'authorization': token}
    debugem = Embed(title="Processing your request...")
    debugem.description = "[...] Validating data\n[] Connect to the API\n[] Fetch image\n[] Return image"
    await debugmsg.edit(embed = debugem)
    debugem.description = "[OK] Validate data\n[...] Waiting API to finish\n[] Fetch image\n[] Return image"
    await debugmsg.edit(embed = debugem)
    async with ClientSession() as session:
        async with session.get(api_url, params=params, headers=headers) as response:
            try:
                response.raise_for_status()
                debugem.description = "[OK] Validate data\n[OK] Connect to the API\n[...] Fetching image\n[] Return image"
                await debugmsg.edit(embed = debugem)
                image_data = await response.read()
                api_elapsed = response.headers.get("X-Elapsed-Time")
            except Exception as e:
                success = False
                image_data = None
                api_elapsed = 0
                error = e
    debugem.description = "[OK] Validate data\n[OK] Connect to the API\n[OK] Fetch image\n[...] Returning image"
    await debugmsg.edit(embed = debugem)
    return {"success": success, "image_data": image_data, "error": error, "api_elapsed": api_elapsed}

async def get_redirect_history_aiohttp(url: str):
    return

def build_mode():
    with open('version.json', 'w+') as f:
        json.dump({'current_version': configurations.bot_version}, f)
        ilog(f'Finished updating version to {configurations.bot_version}', 'build', 'info')

def clean_traceback(traceback_str: str) -> str:
    result = ''
    lines = traceback_str.splitlines()
    for i, line in enumerate(lines):
        if any(i in line for i in ["The above exception was the direct cause of the following exception:", "Stacktrace:"]):
            result = "\n".join(lines[:i])
            break
    if not result: result = traceback_str
    result = "\n".join(filter(lambda x: x.strip() != "", result.splitlines()))
    return result
"""-------------------------------------------------
APPLICATION ERROR HANDLER
-------------------------------------------------"""
@tree.error
async def on_error(interaction: Interaction, error):
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Exception occurred:", description= 'Ask the developer of the bot for more information.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        return
    full_err = traceback.format_exc()
    cleaned = clean_traceback(full_err)
    minlog = cleaned[:cleaned.rfind('\n')]
    minlog_under800 = minlog[-800:] 
    es = ('Check the console for more information.' if len(minlog) > 1000 else '') + f"```py\n{('...' if minlog_under800 != minlog else '') + minlog_under800}```" + f"```py\n{cleaned.splitlines()[-1]}```"
    # if (i:=interaction.user.id) in configurations.owner_guild_id or i in get_whitelist():
    ilog('Exception in a application command: ' + full_err + '--------------------end of exception--------------------', logtype= 'error', flag = 'command')
    await interaction.followup.send(embed=Embed(title="Exception occurred:", description= es, ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
    # else:
        # await interaction.followup.send(embed=Embed(title="Exception occurred", description='Contact the bot owner(s) for more information.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

"""-------------------------------------------------
BASE COMMANDS
/sync
/sys
|-- eval
|-- guilds
|-- whitelist
    |-- list
    |-- modify

/locsys
|-- update
|-- version
|-- restart
|-- maintenance
-------------------------------------------------""" 

@tree.command(name='sync', description='system - sync all commands to all guilds manually')#, guild=Object(id=configurations.owner_guild_id))
async def sync(interaction: Interaction, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You are not allowed to use this command.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    await client.change_presence(activity=Game('syncing...'), status=Status.dnd)
    tree.copy_global_to(guild = Object(id = configurations.owner_guild_id))
    await asyncio.sleep(5)
    await tree.sync()
    ilog(f'Command tree synced via /sync by {interaction.user.id} ({interaction.user.display_name}', logtype = 'info', flag = 'tree')
    await asyncio.sleep(5)
    await interaction.followup.send(embed=Embed(title="Command tree synced", description='Successfully synced the global command tree to all guilds').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
    await client.change_presence(activity=Game('synced. reloading...'), status=Status.dnd)
    await asyncio.sleep(5)
    await client.change_presence(activity=Game('version ' + configurations.bot_version + ' [outdated]' if not check_bot_version(configurations.bot_version) else ""), status=Status.online)

class sys(Group):
    async def is_authorized(self, interaction: Interaction):
        i = interaction.user.id in configurations.owner_ids
        if not i:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You are not allowed to use this command.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return i

    @command(name='eval', description='system - execute python scripts via eval()')
    async def scripteval(self, interaction: Interaction, script: str, awaited: bool = False, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if not await self.is_authorized(interaction): return
        await interaction.followup.send(embed=Embed(title='Executing...', description='Executing the script...').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), wait=True)
        await asyncio.sleep(0.5)
        ilog(f'{interaction.user.name}#{interaction.user.discriminator} ({interaction.user.id}) eval-ed: {script}', 'eval', 'warning')
        if not awaited:
            result = eval(script)
        else:
            async def temp():
                return await eval(script)
            result = await temp()
            del temp
        if not result:
            await interaction.followup.send(embed=Embed(title="Script executed", description='Script executed successfully, the result, might be `None` or too long to fill in here.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        else:
            await interaction.followup.send(embed=Embed(title="Result", description= "```py\n" + str(result) + "```", ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
    @command(name = 'guilds', description= 'system - list guilds that the bot are currently in.')
    async def guilds(self, interaction: Interaction, ephemeral: bool = True):
        await interaction.response.defer(ephemeral=ephemeral)
        if not await self.is_authorized(interaction): return
        embed = Embed(title = 'Guilds list:', description= 'Here is the list of guilds that have this bot in:')
        if len(k:=client.guilds) <= 30:
            current_list = ""
            for i in k:
                current_list += f'{i.id}: {i.name}\n'
        else:
            current_list = "<too many guilds>"
        embed.add_field(name = 'Guilds:', value = f"`{current_list}`")
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    
    whitelist = Group(name='whitelist', description='Get and modify the beta whitelist in the database')
    @whitelist.command(name = 'list', description ='system - Get beta whitelist list in whitelist.json')
    async def whitelist_list(self, interaction: Interaction, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if not await self.is_authorized(interaction): return

        embed = Embed(title='Whitelist list', description='Here is the list of beta-whitelisted user IDs:').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
        current_list = ""
        for i in await get_user_whitelist():
            current_list += f'<@{i}> ({i})\n'
        embed.add_field(name='Users:', value = current_list)
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)

    # @tree.command(name = 'whitelist_modify', description='Modify beta whitelist list in database.json')
    @whitelist.command(name = 'modify', description='system - Modify beta whitelist list in database.json')
    @describe(user = 'User that will be modified in the whitelist database', mode = 'add/remove the user from the database')
    async def whitelist_modify(self, interaction: Interaction, user: Member, mode: typing.Literal['add', 'remove'] = 'add', ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if not await self.is_authorized(interaction): return
        
        try:
            update_status = await update_user_whitelist(user = user.id, add = mode == 'add')
            await interaction.followup.send(embed=Embed(title='Done', description=f'Successfully {"added" if mode == "add" else "removed"} this user in the list: {user.mention} ({user.id})').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar) if update_status else Embed(title='Failed', description='A error occured').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
        except Exception as e:
            ilog('Exception in command /whitelist_modify:' + e, logtype= 'error', flag = 'command')
            await interaction.followup.send(ephemeral= True, embed=Embed(title="Exception occurred", description=str(e), ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

class locsys(Group):
    async def is_authorized(self, interaction: Interaction):
        i = interaction.user.id in configurations.owner_ids
        if not i:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You are not allowed to use this command.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return i
    
    @command(name='update', description='system - update bot repo')
    async def update_bot(self, interaction: Interaction, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if (not configurations.is_replit) or (not configurations.no_git_automation): await interaction.followup.send(embed=Embed(title="Unsupported", description='The bot is deployed on a system that can auto-update itself.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral); return
        if not await self.is_authorized(interaction): return
        
        ilog("Updating git repo...", 'git', 'warning')
        system('git fetch --all')
        system('git reset --hard origin/main')
        
        await interaction.followup.send(embed=Embed(title="Done", description='Successfully updated the bot repo on Github.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)

    @command(name='version', description='system - check the code version')
    async def version(self, interaction: Interaction, ephemeral: bool = False):
        if (not configurations.is_replit) or (not configurations.no_git_automation): await interaction.followup.send(embed=Embed(title="Unsupported", description='The bot is deployed on a system that can auto-update itself.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral); return
        await interaction.response.defer(ephemeral=ephemeral)
        if not await self.is_authorized(interaction): return
        await interaction.followup.send(ephemeral=ephemeral, embed=Embed(title = 'Bot version:', description= f'Bot version {configurations.bot_version} {"[outdated]" if not check_bot_version(configurations.bot_version) else "[up-to-date]"}').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

    @command(name='restart', description='system - Restart the bot')
    async def restartbot(self, interaction: Interaction, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if not await self.is_authorized(interaction): return
        if (not configurations.is_replit): await interaction.followup.send(embed=Embed(title="Unsupported", description='The bot is deployed on non-docker system.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral); return
        await interaction.followup.send(embed=Embed(title="Received", description="Restart request received, killing docker container...", ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
        ilog(f'[+] Restart request by {interaction.user.id} ({interaction.user.display_name})', 'command', 'info')
        ilog('Restarting...', 'system', 'critical')
        await client.change_presence(status=Status.dnd, activity=Game('restarting...'))
        await asyncio.sleep(5)
        system('kill 1')

    @command(name = 'maintenance', description='Toggle maintenance mode for supported commands')
    @describe(status_to_set = 'Status of maintenance to set into the database')
    async def maintenance(self, interaction: Interaction, status_to_set: bool = False):
        await interaction.response.defer(ephemeral = True)
        if not await self.is_authorized(interaction): return
        global maintenance_status
        old = maintenance_status
        maintenance_status = status_to_set
        await interaction.followup.send(embed=Embed(title='Success', description=f'Maintenance status changed: {old} -> {maintenance_status}').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))


tree.add_command(locsys(), guild=Object(id=configurations.owner_guild_id))
tree.add_command(sys())


"""
-------------------------------------------------
FEATURE COMMANDS (beta)
/screenshot
/rps
-------------------------------------------------
"""



class net(Group):
    async def is_authorized(self, interaction: Interaction):
        if maintenance_status:
            await interaction.followup.send(embed = Embed(title='Maintaining', description='Maintenance status is set to True.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
            return False
        i = (await check_user_whitelist(user = interaction.user.id))
        l = (interaction.user.id in configurations.owner_ids)
        k = interaction.guild_id is not None
        p = interaction.guild_id in [guild.id for guild in client.guilds]
        if l:
            return True
        elif not k:
            await interaction.followup.send(embed=Embed(title='Error', description='This command can only be used in a server.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
            return False
        elif not p:
            await interaction.followup.send(embed=Embed(title='Error', description='This server is trying to use this bot as a integration for application commands, which is NOT allowed. Please consider adding the bot to the server.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
            return False
        elif not (i or l):
            await interaction.followup.send(embed = Embed(title='Unauthorized', description='This command is in beta mode, only whitelisted user can access.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
            return False
        return True
    async def get_ip_info(ip) -> dict:
        async with ClientSession() as session:
            async with session.get(f'https://api.iprisk.info/v1/{ip}') as response:
                data = await response.json()
            return data
    @command(name='screenshot', description='BETA - Take a screenshot of a website')
    @describe(url='URL of the website you want to screenshot. (Include https:// or http://)', delay='Delays for the driver to wait after the website stopped loading (in seconds, max 20s) (default: 0)', resolution = 'Resolution of the driver window (Default: 720p)', ephemeral = 'If you want to make the response only visible to you. (default: False)')
    @choices(resolution = [Choice(value=i, name=k) for i, k in [(240, '240p - Minimum'), (360, '360p - Website'), (480, '480p - Standard'), (720, '720p - HD'), (1080, '1080p - Full HD'), (1440, '1440p - 2K'), (2160, '2160p - 4K')]]) # , ('undetected_selenium', 'Selenium + Undetected Chromium (for bypassing)') # engine = [Choice(value=i, name=k) for i, k in [('selenium', 'Selenium + Chromium'), ('playwright', 'Playwright + Chromium')]]
    async def screenshot(self, interaction: Interaction, url: str, delay: Range[int, 1, 20] = 0, resolution: int = 720, ephemeral: bool = False):
        global global_ratelimit
        await interaction.response.defer(ephemeral = ephemeral)
        # conditions to stop executing the command
        if not await self.is_authorized(interaction): return 
        if not url.startswith('http'):
            await interaction.followup.send(embed=Embed(title='Error', description='Please provide a valid URL, including http or https.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
            return
        if any(url.startswith(i) for i in [x + y for x in ['http://', 'https://'] for y in ['0.0.0.0', '127.0.0.1', 'localhost']]):
            await interaction.followup.send(embed=Embed(title='Error', description='Please do not try to access localhost.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
            return
        if global_ratelimit >= configurations.max_global_ratelimit:
            await interaction.followup.send(embed=Embed(title='Rate-limited', description='Bot is currently global rate-limited, please try again later').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral= True)
            return
        msg = await interaction.followup.send(embed=Embed(title = 'Processing your request...'))
        await asyncio.sleep(1)
        global_ratelimit += 1 # get_screenshot_undetected_chromedriver
        els = time()
        data = await get_screenshot(url=url, resolution=resolution, delay=delay, debugmsg=msg)
        global_ratelimit += -1
        global_elapsed = round(1000*(time() - els))
        await msg.edit(embed=Embed(title="Finished", description="Your request has been processed.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        if data["success"]:
            image_bytes = data["image_data"]
            embed = Embed(title='Success',description=f'Here is the website screenshot of {url} \n||*(took {global_elapsed}ms globally, {data["api_elapsed"]}ms for the API to work, elapsed times including requested delays)*||', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
            embed.set_image(url='attachment://screenshot.png')
            await interaction.followup.send(ephemeral = ephemeral, embed=embed, file=File(BytesIO(image_bytes), filename='screenshot.png'))
        else:
            await interaction.followup.send(ephemeral = ephemeral, embed=Embed(title='Error', description=f'Failed to get the screenshot from the API, ask developers for more details... [API error?] ```{data["error"]}```'))
            
    @command(name = 'ip', description='Use APIs to fetch information about a IPv4 address.')
    @describe(ipv4 = "The IPv4 address you want to fetch.")
    # @choices(ipv4 = [Choice(value = i) for i in [f"{x}.{y}.{z}.{t}" for x in range(0, 255) for y in range(0, 255) for z in range(0, 255) for t in range(0, 255)]])
    async def ip(self, interaction: Interaction, ipv4: str, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if not await self.is_authorized(interaction): return
        if not (lambda ip: len(x:= ip.split('.')) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in x))(ipv4):
            await interaction.followup.send(embed=Embed(title='Error', description='Input IPv4 address is invalid.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
            return
        ipdata = await self.get_ip_info(ipv4)
        embed = Embed(title=f"IP information", description= f"Here's the information for `{ipv4}`:")
        # embed.add_field(name, ipdata[val])
        fieldlist = [
            ("IP", ipdata.get("ip", None)),
            ("Data Center", ipdata.get("data_center", None)),
            ("Continent", f'{ipdata["geo"].get("continent", "_")} | {ipdata["geo"].get("continent_code", "_")}'),
            ("Country", f'{ipdata["geo"].get("country", "_")} | {ipdata["geo"].get("country_code", "_")} {ipdata["geo"].get("country_flag_emoji", "?")}'),
            ("City", ipdata["geo"].get("city", None)),
            ("Region", f'{ipdata["geo"].get("region", "_")} | {ipdata["geo"].get("region_code", "_")}'),
            ("\u200B", "\n"),  # blank field separator
            ("Network Route", ipdata["network"].get("route", None)),
            ("AS Number", ipdata["network"].get("as_number", None)),
            ("AS Organization", f'{ipdata["network"].get("as_org", "_")} | {ipdata["network"].get("as_org_alt", "?")}')
        ]
        for field_name, field_value in fieldlist:
            if field_value == None: continue
            embed.add_field(name=field_name, value=f'`{field_value}`' if field_value else "", inline=False)
        embed.set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
        await interaction.followup.send(embed = embed, ephemeral=ephemeral)

tree.add_command(net())
"""
-------------------------------------------------
FEATURE COMMANDS (official)
-------------------------------------------------
/echo
/uptime
"""

# @tree.command(name='echo', description='removing soon - Echo the provided string to the user')
# @describe(string='String to echo')
# async def echo(interaction: Interaction, string: str, ephemeral: bool = True):
#     if interaction.user.id not in configurations.owner_ids:
#         ephemeral = True
#     await interaction.response.defer(ephemeral=ephemeral)
#     await interaction.followup.send(string, ephemeral=ephemeral)

@tree.command(name='uptime', description='Returns the bot uptime.')
async def uptime(interaction: Interaction):
    global unix_uptime
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(embed=Embed(title="Current bot uptime", description=f"Bot was online <t:{unix_uptime}:R> (<t:{unix_uptime}:T> <t:{unix_uptime}:d>) ", ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)

"""
-------------------------------------------------
CLIENT EVENTS
on_ready()
-------------------------------------------------
"""
@client.event
async def on_ready():
    global global_ratelimit
    global maintenance_status
    global unix_uptime
    unix_uptime = round(time())
    global_ratelimit = 0
    maintenance_status = configurations.default_maintenance_status
    await client.change_presence(activity=Game('starting...'), status=Status.idle)
    await asyncio.sleep(2)
    ilog("Syncing commands to the main guild...", 'init', 'info')
    tree.copy_global_to(guild=Object(id=configurations.owner_guild_id))
    ilog("Done! bot is now ready!", 'init', 'info')
    ilog(f"Bot is currently on version {configurations.bot_version}", 'init', 'info')
    ilog(str(client.user) + ' has connected to Discord.', 'init', 'info')
    guilds_num = len(client.guilds)
    members_num = len(set(member for guild in client.guilds for member in guild.members))
    ilog('Connected to ' + str(guilds_num) + ' guilds and ' + str(members_num)  + ' users.', 'init', 'info')
    await asyncio.sleep(5)
    await client.change_presence(activity=Game('version ' + configurations.bot_version), status=Status.online)


"""
-------------------------------------------------
BOOT
-------------------------------------------------
"""
def run():
    # some checks before run, soonTM
    if configurations.is_replit:
        ilog('Starting flask keep-alive server...', 'init', 'info')
        ka()
    ilog('Starting Discord client...', 'init', 'info')
    client.run(configurations.bot_token)
build = not configurations.not_builder
if __name__ == '__main__':
    if not build:
        run()
    else:
        ilog('Running build mode', 'build', 'info')
        build_mode()
