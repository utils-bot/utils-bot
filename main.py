from discord import app_commands, Intents, Client, Interaction, Object, Embed, File, Game, Status, Color, Member
from selenium.webdriver.support import expected_conditions as EC
from jsondb import get_whitelist, update_whitelist, beta_check
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from logger import CustomFormatter, ilog
from os import environ, system, path
from selenium import webdriver
from keep_alive import ka
from time import sleep, time
from io import BytesIO
import logging, json, typing, functools
from datetime import datetime
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
class configurations:
    bot_token = environ.get('bot_token', '') 
    owner_ids = [806432782111735818]
    owner_guild_id = environ.get('owner_guild_id', 0)
    beta = True
    max_global_ratelimit = 2
    default_maintenance_status = False
    bot_version = 'v0.1.13b' # ignore

intents = Intents.default()
intents.members = True
intents.message_content = True
client = Client(intents=intents)
tree = app_commands.CommandTree(client)

async def antiblock(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    func = functools.partial(blocking_func, *args, **kwargs)
    return await client.loop.run_in_executor(None, func)

def get_screenshot(url, window_height: int, window_width: int, delay: int):
    options = Options()
    for arg in ['--no-sandbox', '--disable-dev-shm-usage', '--headless', '--disable-gpu', '--window-position=0,0', f'--window-size={window_height},{window_width}']: options.add_argument(arg)
    with webdriver.Chrome(options=options) as driver:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.XPATH, "//body[not(@class='loading')]")))
        sleep(3 + delay)
        image_bytes = driver.get_screenshot_as_png()
    return image_bytes

"""
-------------------------------------------------
BASE COMMANDS
-------------------------------------------------
"""  
@tree.command(name='eval', description='OWNER ONLY - execute python scripts via eval()', guild=Object(id=configurations.owner_guild_id))
async def scripteval(interaction: Interaction, script: str, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    msg = await interaction.followup.send(embed=Embed(color=Color.blue(), title='Executing...', description='Executing the script, if there is a reply this message will be edited', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), wait=True)
    sleep(2)
    try:
        result = eval(script)
    except Exception as e:
        ilog('Exception in command /eval:' + e, logtype= 'error', flag = 'command')
        await msg.edit(embed=Embed(title="Exception occurred", description=str(e), color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
    else:
        if result is not None:
            await msg.edit(embed=Embed(title="Result", description=str(result), color=Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        else:
            await msg.edit(embed=Embed(title="Script executed", color=Color.green(), description='Script executed successfully, the result, might be `None` or too long to fill in here.', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

@tree.command(name='update', description='OWNER ONLY - update bot repo', guild=Object(id=configurations.owner_guild_id))
async def update_bot(interaction: Interaction, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    
    try:
        system('git fetch --all')
        system('git reset --hard origin/main')
    except Exception as e:
        ilog('Exception in command /update:' + e, logtype= 'error', flag = 'command')
        await interaction.followup.send(embed=Embed(title="Exception occurred", description=str(e), color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
    else:
        await interaction.followup.send(embed=Embed(title="Done", color=Color.green(), description='Successfully updated the bot repo on Github.', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)

@tree.command(name='version', description='OWNER ONLY - check the code version', guild=Object(id=configurations.owner_guild_id))
async def sync(interaction: Interaction, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    
    await interaction.followup.send(ephemeral=ephemeral, embed=Embed(color=Color.green(), title = 'Bot version:', description= f'Bot version {configurations.bot_version}', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

@tree.command(name='sync', description='OWNER ONLY - sync all commands to all guilds manually', guild=Object(id=configurations.owner_guild_id))
async def sync(interaction: Interaction, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    try:
        await client.change_presence(activity=Game('syncing...'), status=Status.dnd)
        tree.copy_global_to(guild=Object(id=configurations.owner_guild_id))
        await tree.sync()
        ilog(f'[+] Command tree synced via /sync by {interaction.user.id} ({interaction.user.display_name}', logtype = 'info', flag = 'tree')
        await interaction.followup.send(embed=Embed(title="Command tree synced", color=Color.green(), description='Successfully synced the global command tree to all guilds', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
        await client.change_presence(activity=Game('synced. reloading...'), status=Status.dnd)
        sleep(2)
        await client.change_presence(activity=Game('utils-bot'), status=Status.online)
    except Exception as e:
        ilog('Exception in command /sync:' + e, logtype= 'error', flag = 'command')
        await interaction.followup.send(embed=Embed(title="Exception occurred", description=str(e), color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)



@tree.command(name='restartbot', description='OWNER ONLY - Restart the bot', guild=Object(id=configurations.owner_guild_id))
async def restartbot(interaction: Interaction, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.discriminator), ephemeral=ephemeral)
        return

    await interaction.followup.send(embed=Embed(title="Received", description="Restart request received, killing docker container...", color=Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
    ilog(f'[+] Restart request by {interaction.user.id} ({interaction.user.display_name})', 'command', 'info')
    ilog('Restarting...', 'system', 'critical')
    await client.change_presence(status=Status.dnd, activity=Game('restarting...'))
    sleep(5)
    system('kill 1')

@tree.command(name = 'whitelist_list', description ='OWNER ONLY - Get beta whitelist list in database.json', guild=Object(id=configurations.owner_guild_id))
async def whitelist_list(interaction: Interaction, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    
    try:
        embed = Embed(title='Whitelist list', description='Here is the list of beta-whitelisted user IDs:', color = Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
        current_list = ""
        for i in get_whitelist():
            current_list += f'<@{i}> ({i})'
        embed.add_field(name='Users:', value = current_list)
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    except Exception as e:
        ilog('Exception in command /whitelist_list:' + e, logtype= 'error', flag = 'command')
        await interaction.followup.send(embed=Embed(title="Exception occurred", description=str(e), color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)

@tree.command(name = 'whitelist_modify', description='OWNER ONLY - Modify beta whitelist list in database.json', guild=Object(id=configurations.owner_guild_id))
@app_commands.describe(user = 'User that will be modified in the whitelist database', add = 'Mode to modify, True = add / False = remove')
async def whitelist_modify(interaction: Interaction, user: Member, add: bool = True, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    
    try:
        update_status = update_whitelist(id = user.id, add = add)
        await interaction.followup.send(embed=Embed(title='Done', description=f'Successfully {"added" if bool else "removed"} this user in the list: {user.mention} ({user.id})', color = Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar) if update_status else Embed(title='Failed', description='A error occured', color = Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
    except Exception as e:
        ilog('Exception in command /whitelist_modify:' + e, logtype= 'error', flag = 'command')
        await interaction.followup.send(ephemeral= True, embed=Embed(title="Exception occurred", description=str(e), color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))



"""GENERATED BY CHATGPT
async def set_bot_avatar(interaction: Interaction, url: str = ''):
    # Check if the user provided an attachment
    if len(interaction.message.attachments) > 0:
        attachment = interaction.message.attachments[0]
        if attachment.content_type.startswith('image/'):
            avatar_bytes = await attachment.read()
            avatar_file = BytesIO(avatar_bytes)
            try:
                await client.user.edit(avatar=avatar_file.read())
                embed = Embed(title='Bot Avatar Changed', 
                              description='The bot avatar has been changed successfully!', 
                              color=Color.green())
            except Exception as e:
                embed = Embed(title='Error', 
                              description=f'Failed to change bot avatar: {str(e)}', 
                              color=Color.red())
        else:
            embed = Embed(title='Error', 
                          description='Please provide an image file as an attachment!', 
                          color=Color.red())
    # If no attachment was provided, try to fetch the image from the provided URL
    elif url != '':
        try:
            response = requests.get(url)
            if response.status_code == 200 and response.headers.get('content-type', '').startswith('image/'):
                avatar_bytes = response.content
                avatar_file = BytesIO(avatar_bytes)
                await client.user.edit(avatar=avatar_file.read())
                embed = Embed(title='Bot Avatar Changed', 
                              description='The bot avatar has been changed successfully!', 
                              color=Color.green())
            else:
                embed = Embed(title='Error', 
                              description='Please provide a valid image URL!', 
                              color=Color.red())
        except Exception as e:
            embed = Embed(title='Error', 
                          description=f'Failed to change bot avatar: {str(e)}', 
                          color=Color.red())
    else:
        embed = Embed(title='Error', 
                      description='Please provide an image file as an attachment or a valid image URL!', 
                      color=Color.red())

    await interaction.send(embed=embed)
"""

# @tree.command(name = 'bot_avatar', description='OWNER ONLY - Change the bot avatar with a png link or a image')

@tree.command(name = 'maintenance', description='OWNER ONLY - Toggle maintenance mode for supported commands')
@app_commands.describe(status_to_set = 'Status of maintenance to set into the database')
async def maintenance(interaction: Interaction, status_to_set: bool = False):
    await interaction.response.defer(ephemeral = True)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    global maintenance_status
    old = maintenance_status
    maintenance_status = status_to_set
    await interaction.followup.send(embed=Embed(color=Color.green(), title='Success', description=f'Maintenance status changed: {old} -> {maintenance_status}', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

"""
-------------------------------------------------
FEATURE COMMANDS (beta)
-------------------------------------------------
"""
@tree.command(name='screenshot', description='Take a screenshot of a website')
@app_commands.describe(url='URL of the website you want to screenshot. (Include https:// or http://)', delay='Delays for the driver to wait after the website stopped loading (in seconds, max 20s)', resolution = 'Resolution of the driver window. Format height:width')
async def screenshot(interaction: Interaction, url: str, delay: int = 0, resolution: str = '1280:720'):
    global global_ratelimit
    await interaction.response.defer(ephemeral=True)
    # conditions to stop executing the command
    if not beta_check(user = interaction.user.id, beta_bool = configurations.beta) or not interaction.user.id in configurations.owner_ids:
        await interaction.followup.send(embed = Embed(title='Unauthorized', description='This command is in beta mode, only whitelisted user can access.', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = True)
        return
    if interaction.guild_id is None:
        await interaction.followup.send(embed=Embed(title='Error', description='This command can only be used in a server.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    if not url.startswith('http'):
        await interaction.followup.send(embed=Embed(title='Error', description='Please provide a valid URL, including http or https.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    if delay > 20:
        await interaction.followup.send(embed=Embed(title='Error', description='Delay must be less than 20s.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    if interaction.user.id not in configurations.owner_ids:
        resolution = '1280:720'
    if global_ratelimit >= configurations.max_global_ratelimit:
        await interaction.followup.send(embed=Embed(color=Color.red(), title='Rate-limited', description='Bot is currently global rate-limited, please try again later', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral= True)
        return
    sleep(2)
    global_ratelimit += 1
    try:
        i = resolution.split(':')
        window_height, window_width = i[0], i[1]
        image_bytes = await antiblock(get_screenshot, url=url, window_height=window_height, window_width=window_width, delay = delay)
        embed = Embed(title='Success',description=f'Here is the website screenshot of {url}', color=Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
        embed.set_image(url='attachment://screenshot.png')
        await interaction.followup.send(embed=embed, file=File(BytesIO(image_bytes), filename='screenshot.png'))
    except Exception as e:
        ilog('Exception in command /screenshot:' + e, logtype= 'error', flag = 'command')
        if interaction.user.id in configurations.owner_ids:
            await interaction.followup.send(embed=Embed(title='Exception Occurred', description=f'Exception occurred: {e}', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        else:
            await interaction.followup.send(embed = Embed(title='Error', description='Exception occurred, we are trying to fix asap', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
    global_ratelimit += -1

"""
-------------------------------------------------
FEATURE COMMANDS (official)
-------------------------------------------------
"""
@tree.command(name='echo', description='Echo the provided string to the user')
@app_commands.describe(string='String to echo')
async def echo(interaction: Interaction, string: str, ephemeral: bool = True):
    if interaction.user.id not in configurations.owner_ids:
        ephemeral = True
    await interaction.response.defer(ephemeral=ephemeral)
    await interaction.followup.send(string, ephemeral=ephemeral)

@tree.command(name='uptime', description='Returns the bot uptime.')
async def uptime(interaction: Interaction):
    global unix_uptime
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(embed=Embed(title="Current bot uptime", description=f"Bot was online <t:{unix_uptime}:R> (<t:{unix_uptime}:T> <t:{unix_uptime}:d>) ", color=Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)

"""
-------------------------------------------------
CLIENT EVENTS
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
    await client.change_presence(activity=Game('starting...'), status=Status.dnd)
    sleep(2)
    ilog("Syncing commands to the owner guild...", 'init', 'info')
    await tree.sync(guild=Object(id=configurations.owner_guild_id))
    ilog("Done! bot is now ready!", 'init', 'info')
    ilog(f"Bot is currently on version {configurations.bot_version}", 'init', 'info')
    ilog(str(client.user) + ' has connected to Discord.', 'init', 'info')
    ilog('Connected to ' + str(len(client.guilds)) + ' guilds and ' + str(len(client.guilds)) + ' users.', 'init', 'info' )
    await client.change_presence(activity=Game('version ' + configurations.bot_version), status=Status.online)
"""
-------------------------------------------------
BOOT
-------------------------------------------------
"""
if __name__ == '__main__':
    ka()
    client.run(configurations.bot_token)