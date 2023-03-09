"""---------------------------------------------
Env:
- Bot token -> .env:bot_token
- Owner guild id -> .env:owner_guild_id
- Random quotes -> .env:not_builder
---------------------------------------------"""
from discord import app_commands, Intents, Client, Interaction, Object, Embed, File, Game, Status, Color, Member, ui, ButtonStyle
from jsondb import get_whitelist, update_whitelist, beta_check, check_bot_version
import logging, json, typing, functools, traceback, asyncio, requests
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from logger import CustomFormatter, ilog
from os import environ, system
from datetime import datetime
from time import sleep, time
from keep_alive import ka
from io import BytesIO
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
    bot_token = environ.get('bot_token') 
    owner_ids = [806432782111735818]
    owner_guild_id = environ.get('owner_guild_id', 0)
    beta = True
    max_global_ratelimit = 2
    default_maintenance_status = False
    bot_version = 'v0.2.4' # ignore
    not_builder = bool(environ.get('not_builder', False))

intents = Intents.default()
intents.members = True
# intents.message_content = True
client = Client(intents=intents)
tree = app_commands.CommandTree(client)

async def antiblock(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    func = functools.partial(blocking_func, *args, **kwargs)
    return await client.loop.run_in_executor(None, func)

async def get_screenshot(url, window_height: int, window_width: int, delay: int= 7):
    global ip
    options = Options()
    for arg in ['--no-sandbox', '--disable-dev-shm-usage', '--headless', '--disable-gpu', '--window-position=0,0', f'--window-size={window_height},{window_width}', '--enable-features=WebContentsForceDark']: options.add_argument(arg)
    prefs = {
    "download_restrictions": 3,
    "download.open_pdf_in_system_reader": False,
    "download.prompt_for_download": True,
    "download.default_directory": "/dev/null",
    "plugins.always_open_pdf_externally": False
    }
    options.add_experimental_option("prefs", prefs)
    with webdriver.Chrome(options=options) as driver:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.XPATH, "//body[not(@class='loading')]")))
        await asyncio.sleep(3 + delay)
        elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{ip}')]")
        for element in elements: driver.execute_script("arguments[0].innerText = arguments[1];", element, '<the host ip address>')
        image_bytes = driver.get_screenshot_as_png()
    return image_bytes

def build_mode():
    with open('version.json', 'w+') as f:
        json.dump({'current_version': configurations.bot_version}, f)
        ilog(f'Finished updating version to {configurations.bot_version}', 'build', 'info')
    with open('pc.py', 'wb+') as fw, open('main.py', 'rb') as fr:
        fw.write(fr.read())
        ilog(f'Finished making pc.py file that you can input your own shit', 'build', 'info')

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
    full_err = traceback.format_exc()
    cleaned = clean_traceback(full_err)
    minlog = cleaned[:cleaned.rfind('\n')]
    minlog_under800 = minlog[-800:] 
    es = ('Check the console for more information.' if len(minlog) > 1000 else '') + f"```py\n{('...' if minlog_under800 != minlog else '') + minlog_under800}```" + f"```py\n{cleaned.splitlines()[-1]}```"
    # if (i:=interaction.user.id) in configurations.owner_guild_id or i in get_whitelist():
    ilog('Exception in a application command: ' + full_err + '--------------------end of exception--------------------', logtype= 'error', flag = 'command')
    await interaction.followup.send(embed=Embed(title="Exception occurred:", description= es, color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
    # else:
        # await interaction.followup.send(embed=Embed(title="Exception occurred", description='Contact the bot owner(s) for more information.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

"""-------------------------------------------------
BASE COMMANDS
/sync
/sys
|-- eval
|-- guilds
|-- whitelist
    |-- list
    |-- modify
/localsys
|-- update
|-- version
|-- restart
|-- maintenance
-------------------------------------------------""" 

@tree.command(name='sync', description='system - sync all commands to all guilds manually')#, guild=Object(id=configurations.owner_guild_id))
async def sync(interaction: Interaction, ephemeral: bool = False):
    await interaction.response.defer(ephemeral=ephemeral)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    
    await client.change_presence(activity=Game('syncing...'), status=Status.dnd)
    tree.copy_global_to(guild = Object(id = configurations.owner_guild_id))
    await tree.sync()
    ilog(f'Command tree synced via /sync by {interaction.user.id} ({interaction.user.display_name}', logtype = 'info', flag = 'tree')
    await interaction.followup.send(embed=Embed(title="Command tree synced", color=Color.green(), description='Successfully synced the global command tree to all guilds', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
    await client.change_presence(activity=Game('synced. reloading...'), status=Status.dnd)
    sleep(5)
    await client.change_presence(activity=Game('version ' + configurations.bot_version + ' [outdated]' if not check_bot_version(configurations.bot_version) else ""), status=Status.online)

class sys(app_commands.Group):
    @app_commands.command(name='eval', description='system - execute python scripts via eval()')
    async def scripteval(self, interaction: Interaction, script: str, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if interaction.user.id not in configurations.owner_ids:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
            return
        await interaction.followup.send(embed=Embed(color=Color.blue(), title='Executing...', description='Executing the script...', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), wait=True)
        sleep(2)
        ilog(f'{interaction.user.name}#{interaction.user.discriminator} ({interaction.user.id}) eval-ed: {script}', 'eval', 'warning')
        result = eval(script)
        if not result:
            await interaction.followup.send(embed=Embed(title="Script executed", color=Color.green(), description='Script executed successfully, the result, might be `None` or too long to fill in here.', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        else:
            await interaction.followup.send(embed=Embed(title="Result", description= "```py\n" + str(result) + "```", color=Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
    @app_commands.command(name = 'guilds', description= 'system - list guilds that the bot are currently in.')
    async def guilds(self, interaction: Interaction, ephemeral: bool = True):
        await interaction.response.defer(ephemeral=ephemeral)
        if interaction.user.id not in configurations.owner_ids:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
            return
        embed = Embed(title = 'Guilds list:', description= 'Here is the list of guilds that have this bot in:')
        if len(k:=client.guilds) <= 30:
            current_list = ""
            for i in k:
                current_list += f'{i.id}: {i.name}\n'
        else:
            current_list = "<too many guilds>"
        embed.add_field(name = 'Guilds:', value = f"```{current_list}```")
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    
    whitelist = app_commands.Group(name='whitelist', description='Get and modify the beta whitelist in the database')
    @whitelist.command(name = 'list', description ='system - Get beta whitelist list in whitelist.json')
    async def whitelist_list(self, interaction: Interaction, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if interaction.user.id not in configurations.owner_ids:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
            return

        embed = Embed(title='Whitelist list', description='Here is the list of beta-whitelisted user IDs:', color = Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
        current_list = ""
        for i in get_whitelist():
            current_list += f'<@{i}> ({i})\n'
        embed.add_field(name='Users:', value = current_list)
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)

    # @tree.command(name = 'whitelist_modify', description='Modify beta whitelist list in database.json', )
    @whitelist.command(name = 'modify', description='system - Modify beta whitelist list in database.json')
    @app_commands.describe(user = 'User that will be modified in the whitelist database', mode = 'add/remove the user from the database')
    async def whitelist_modify(self, interaction: Interaction, user: Member, mode: typing.Literal['add', 'remove'] = 'add', ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if interaction.user.id not in configurations.owner_ids:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
            return
        
        try:
            update_status = update_whitelist(id = user.id, add = mode == 'add')
            await interaction.followup.send(embed=Embed(title='Done', description=f'Successfully {"added" if mode == "add" else "removed"} this user in the list: {user.mention} ({user.id})', color = Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar) if update_status else Embed(title='Failed', description='A error occured', color = Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)
        except Exception as e:
            ilog('Exception in command /whitelist_modify:' + e, logtype= 'error', flag = 'command')
            await interaction.followup.send(ephemeral= True, embed=Embed(title="Exception occurred", description=str(e), color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

class localsys(app_commands.Group):
    @app_commands.command(name='update', description='system - update bot repo')
    async def update_bot(self, interaction: Interaction, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if interaction.user.id not in configurations.owner_ids:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
            return
        
        ilog("Updating git repo...", 'git', 'warning')
        system('git fetch --all')
        system('git reset --hard origin/main')
        
        await interaction.followup.send(embed=Embed(title="Done", color=Color.green(), description='Successfully updated the bot repo on Github.', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=ephemeral)

    @app_commands.command(name='version', description='system - check the code version')
    async def version(self, interaction: Interaction, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        if interaction.user.id not in configurations.owner_ids:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
            return
        
        await interaction.followup.send(ephemeral=ephemeral, embed=Embed(color=Color.green(), title = 'Bot version:', description= f'Bot version {configurations.bot_version} {"[outdated]" if not check_bot_version(configurations.bot_version) else "[up-to-date]"}', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

    @app_commands.command(name='restart', description='system - Restart the bot')
    async def restartbot(self, interaction: Interaction, ephemeral: bool = False):
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

    @app_commands.command(name = 'maintenance', description='Toggle maintenance mode for supported commands')
    @app_commands.describe(status_to_set = 'Status of maintenance to set into the database')
    async def maintenance(self, interaction: Interaction, status_to_set: bool = False):
        await interaction.response.defer(ephemeral = True)
        if interaction.user.id not in configurations.owner_ids:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You must be the owner to use this command!", color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
            return
        global maintenance_status
        old = maintenance_status
        maintenance_status = status_to_set
        await interaction.followup.send(embed=Embed(color=Color.green(), title='Success', description=f'Maintenance status changed: {old} -> {maintenance_status}', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
tree.add_command(localsys(), guild=Object(id=configurations.owner_guild_id))
tree.add_command(sys())
# tree.add_command(grp)

"""
-------------------------------------------------
FEATURE COMMANDS (beta)
/screenshot
/rps
-------------------------------------------------
"""
@tree.command(name='screenshot', description='BETA - Take a screenshot of a website')
@app_commands.describe(url='URL of the website you want to screenshot. (Include https:// or http://)', delay='Delays for the driver to wait after the website stopped loading (in seconds, max 20s)', resolution = '(Will be overwritten if you are not botadmin.) Resolution of the driver window. Format height:width', ephemeral = 'if you want to public the bot response to all users, make this True, else False.')
async def screenshot(interaction: Interaction, url: str, delay: int = 0, resolution: str = '1280:720', ephemeral: bool = False):
    global global_ratelimit
    await interaction.response.defer(ephemeral = ephemeral)
    # conditions to stop executing the command
    if not (beta_check(user = interaction.user.id, beta_bool = configurations.beta)) and (not interaction.user.id in configurations.owner_ids):
        await interaction.followup.send(embed = Embed(title='Unauthorized', description='This command is in beta mode, only whitelisted user can access.', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
        return
    if interaction.guild_id is None:
        await interaction.followup.send(embed=Embed(title='Error', description='This command can only be used in a server.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
        return
    if not url.startswith('http'):
        await interaction.followup.send(embed=Embed(title='Error', description='Please provide a valid URL, including http or https.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
        return
    if any(url.startswith(i) for i in [x + y for x in ['http://', 'https://'] for y in ['0.0.0.0', '127.0.0.1', 'localhost']]):
        await interaction.followup.send(embed=Embed(title='Error', description='Please do not try to access localhost.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
        return
    if delay > 20:
        await interaction.followup.send(embed=Embed(title='Error', description='Delay must be less than 20s.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
        return
    if interaction.user.id not in configurations.owner_ids:
        resolution = '1280:720'
    if global_ratelimit >= configurations.max_global_ratelimit:
        await interaction.followup.send(embed=Embed(color=Color.red(), title='Rate-limited', description='Bot is currently global rate-limited, please try again later', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral= True)
        return
    i = resolution.split(':')
    if len(i) != 2: # or (len(i) == 2 and all(isinstance(k, int) for k in i)):
        await interaction.followup.send(embed=Embed(title='Error', description='Invalid resolution format. Must be str(int:int). For example "1920:1080"/"123:456"', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
        return
    sleep(2)
    global_ratelimit += 1
    window_height, window_width = i[0], i[1]
    image_bytes = await get_screenshot(url=url, window_height=window_height, window_width=window_width, delay = delay)
    embed = Embed(title='Success',description=f'Here is the website screenshot of {url}', color=Color.green(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
    embed.set_image(url='attachment://screenshot.png')
    await interaction.followup.send(embed=embed, file=File(BytesIO(image_bytes), filename='screenshot.png'))
    global_ratelimit += -1

"""class RockPaperScissorsUIView(ui.View):
    def __init__(self, interaction: Interaction):
        super().__init__()
        self.interaction = interaction
    @ui.button(label='Rock 👊')
    async def rock(self, interaction: Interaction, button: ui.Button):
        await self.play('rock')
    @ui.button(label='Paper 📃')
    async def paper(self, interaction: Interaction, button: ui.Button):
        await self.play('paper')
    @ui.button(label='Scissors ✂')
    async def scissors(self, interaction: Interaction, button: ui.Button):
        await self.play('scissors')
    
    async def play(self, user_choice: str) -> None:
        interaction = self.interaction
        computer_choice = choice(['rock', 'paper', 'scissors'])
        win_ = (user_choice == 'rock' and computer_choice == 'scissors') or (user_choice == 'paper' and computer_choice == 'rock') or (user_choice == 'scissors' and computer_choice == 'paper')
        tie_ = user_choice == computer_choice
        result = 'win 😊 How lucky are you!' if win_ else 'tie 😐 Well played!' if tie_ else 'lose 😞 Better luck next time...'
        await interaction.followup.send(embed=Embed(color = Color.red() if win_ else Color.blue() if tie_ else Color.red(), title = 'Rock Paper Scissors', description= f'Bot chose {computer_choice}. You {result}').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

@tree.command(name = 'rps', description= 'BETA - Play Rock Paper Scissors, this is a test for discord buttons.')
@app_commands.describe(ephemeral = 'Share your play result with people in the guild, defaulting to True.')
async def rps(interaction: Interaction, ephemeral: bool = True):
    await interaction.response.defer(ephemeral=ephemeral)
    if global_ratelimit >= configurations.max_global_ratelimit:
        await interaction.followup.send(embed=Embed(color=Color.red(), title='Rate-limited', description='Bot is currently global rate-limited, please try again later', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral= True)
        return
    if not beta_check(user = interaction.user.id, beta_bool = configurations.beta) or not interaction.user.id in configurations.owner_ids:
        await interaction.followup.send(embed = Embed(title='Unauthorized', description='This command is in beta mode, only whitelisted user can access.', timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
        return
    if interaction.guild_id is None:
        await interaction.followup.send(embed=Embed(title='Error', description='This command can only be used in a server.', color=Color.red(), timestamp=datetime.now()).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = ephemeral)
        return
    view = RockPaperScissorsUIView(interaction)
    await interaction.followup.send(embed=Embed(title='Rock Paper Scissors', description='Choose your move:', color=Color.red(), timestamp=datetime.now()).set_footer(text=f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), view=view)
    """

"""
-------------------------------------------------
FEATURE COMMANDS (official)
-------------------------------------------------
/echo
/uptime
"""
@tree.command(name='echo', description='removing soon - Echo the provided string to the user')
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
on_ready()
-------------------------------------------------
"""
@client.event
async def on_ready():
    global global_ratelimit
    global maintenance_status
    global unix_uptime
    global ip 
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
    ilog('Connected to ' + str(len(client.guilds)) + ' guilds and ' + str(sum(len(guild.members) for guild in client.guilds)) + ' users.', 'init', 'info')
    await client.change_presence(activity=Game('version ' + configurations.bot_version), status=Status.online)
    ip = requests.get('https://ipv4.icanhazip.com').text

"""
-------------------------------------------------
BOOT
-------------------------------------------------
"""
build = not configurations.not_builder
if __name__ == '__main__':
    if not build:
        ilog('Starting flask keep-alive server...', 'init', 'info')
        ka()
        ilog('Starting Discord client...', 'init', 'info')
        client.run(configurations.bot_token)
    else:
        ilog('Running build mode', 'build', 'info')
        build_mode()
