"""---------------------------------------------
Check .env.example to setup the bot.
---------------------------------------------"""

import typing, traceback, asyncio, json, sentry_sdk, sys as sysio, os, platform, psutil, binascii
from discord import Intents, Client, Interaction, Object, Embed as discordEmbed, File, Game, Status, Member, Webhook, ButtonStyle, TextStyle, Activity, ActivityType, Color
from discord.app_commands import CommandTree, Group, command, Choice, choices, describe, Range, AppCommandError
from discord.app_commands.checks import cooldown
from discord.app_commands.errors import CommandOnCooldown
from discord.gateway import DiscordWebSocket
from discord.ui import button, View, Modal, Button, TextInput
from discord.ext import tasks
from jsondb import get_user_whitelist, update_user_whitelist, check_user_whitelist
from aiohttp import ClientSession
from logger import CustomFormatter, ilog
from time import time
from io import BytesIO
from configs import configurations
from pyotp import TOTP

"""
-------------------------------------------------
DEFINING VARS
-------------------------------------------------
"""

class MyDiscordWebSocket(DiscordWebSocket):
    async def send_as_json(self, data):
        if (data.get('op') == self.IDENTIFY) and (data.get('d', {}).get('properties', {}).get('browser') is not None):
                data['d']['properties']['browser'] = data['d']['properties']['device'] = 'Discord iOS'
        await super().send_as_json(data)

class MyClient(Client):
    def __init__(self, *, intents: Intents = Intents.default()) -> None:
        super().__init__(intents=intents)
        self.tree = CommandTree(self)
        return
    @tasks.loop(seconds=30)
    async def presence_update(self):
        "Update bot presence"
        global unix_uptime
        # Block this loop until the bot is ready
        await self.wait_until_ready()
        # Do loops
        await self.change_presence(activity=Activity(type=ActivityType.watching, name=f'{len(self.guilds)} guilds'), status=Status.online)
        await asyncio.sleep(30)
        await self.change_presence(activity=Game('version ' + configurations.bot_version), status=Status.online)
        await asyncio.sleep(30)
        # change presence to latency {round(client.latency*1000)}ms
        await self.change_presence(activity=Activity(type=ActivityType.watching, name=f'latency {round(self.latency*1000)}ms'), status=Status.online)
    def taskloops(self): return [self.presence_update]

    async def setup_hook(self):
        "Do value resets, pre-sync to development guild, start loop tasks"
        # varible reset
        global unix_uptime
        global global_ratelimit
        global maintenance_status
        global_ratelimit = 0
        maintenance_status = configurations.default_maintenance_status
        unix_uptime = round(time())
        # do syncs
        ilog("Syncing commands to the main guild...", 'client.setup_hook', 'info')
        # self.tree.copy_global_to(guild = Object(id=configurations.owner_guild_id))
        await self.tree.sync(guild = Object(id=configurations.owner_guild_id))
        # start looptasks
        ilog("Starting loop tasks...", 'client.setup_hook', 'info')
        try: 
            for task in self.taskloops(): task.start()
        except BaseException: pass
        ilog("Done! Bot will be ready soon", 'client.setup_hook', 'info')
        await asyncio.sleep(3)
        return
    
    async def on_ready(self):
        "Set status, Return bot statistics"
        ilog("Bot is ready. Getting informations...", 'client.on_ready', 'info')
        await self.change_presence(activity=Game('starting...'), status=Status.idle)
        await asyncio.sleep(2)
        ilog(f"Bot is currently on version {configurations.bot_version}", 'client.on_ready', 'info')
        ilog(str(self.user) + ' has connected to Discord.', 'client.on_ready', 'info')
        guilds_num = len(self.guilds)
        members_num = len(set(member for guild in self.guilds for member in guild.members))
        ilog('Connected to ' + str(guilds_num) + ' guilds', 'client.on_ready', 'info')
        await asyncio.sleep(5)
        await self.change_presence(activity=Game('version ' + configurations.bot_version), status=Status.online)
        ilog('Done! Successfully started the bot!', 'client.on_ready', 'info')

    async def on_error(self, event_method, *args, **kwargs):
        "Handle exceptions"
        ilog(f"Exception occurred in {event_method}:", 'client.on_error', 'error')
        ilog(traceback.format_exc(), 'client.on_error', 'error')
        return

intents = Intents.default()
DiscordWebSocket.from_client = MyDiscordWebSocket.from_client
client = MyClient(intents=intents)
tree = client.tree


class Embed(discordEmbed):
    def uniform(self, interaction):
        self.set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
        return self

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
async def on_error(interaction: Interaction, error: AppCommandError):
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Exception occurred:", description= 'Ask the developer of the bot for more information.').uniform(interaction)) if not interaction.is_expired() else ilog("discord.Interaction expired on exception message.", flag = "command", logtype = 'warning')
        return
    if isinstance(error, CommandOnCooldown):
        if not interaction.response.is_done(): await interaction.response.defer()
        await interaction.followup.send(embed=Embed(title="You can't use this command right now", description= "Command on cooldown. Try again in " + str(round(error.retry_after, 2)) + " seconds.").uniform(interaction)) if not interaction.is_expired() else ilog("discord.Interaction expired on exception message.", flag = "command", logtype = 'warning')
        return
    full_err = traceback.format_exc()
    cleaned = clean_traceback(full_err)
    minlog = cleaned[:cleaned.rfind('\n')]
    minlog_under800 = minlog[-800:] 
    es = ('Check the console for more information.' if len(minlog) > 800 else '') + f"```py\n{('...' if minlog_under800 != minlog else '') + minlog_under800}```" + f"```py\n{cleaned.splitlines()[-1]}```"
    # if (i:=interaction.user.id) in configurations.owner_guild_id or i in get_whitelist():
    ilog('Exception in a application command: \n' + full_err + '> END OF TRACEBACK <', logtype= 'error', flag = 'command')
    await interaction.followup.send(embed=Embed(title="Exception occurred:", description= es).uniform(interaction)) if not interaction.is_expired() else ilog("discord.Interaction expired on exception message.", flag = "command", logtype = 'warning')
    # else:
        # await interaction.followup.send(embed=Embed(title="Exception occurred", description='Contact the bot owner(s) for more information.', ).uniform(interaction))

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
@describe(silent = 'Whether you want the output to be sent to you alone or not')
async def sync(interaction: Interaction, delay: Range[int, 0, 60] = 30, silent: bool = False):
    global maintenance_status
    elapsed = time()
    await interaction.response.defer(ephemeral=silent)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You are not allowed to use this command.").uniform(interaction), ephemeral=True)
        return
    await interaction.followup.send(embed=Embed(title="Syncing job requested", description=f'A sync job for this bot has been queued. All functions of the bot will be disabled to prevent ratelimit. The current version of the bot is ``{configurations.bot_version}``.').uniform(interaction), ephemeral=silent)
    await client.change_presence(activity=Game('syncing...'), status=Status.dnd)
    ilog(f'Sync job requested, working on the sync...', logtype = 'warning', flag = 'tree')
    ilog(f'Locking the bot', logtype = 'info', flag = 'tree sync')
    maintenance_status = True
    ilog(f'Canceling looptasks', logtype = 'info', flag = 'tree sync')
    for task in client.taskloops(): task.cancel()
    ilog(f'Waiting for anti-ratelimit', logtype = 'info', flag = 'tree sync')
    await asyncio.sleep(delay)
    ilog(f'Sync-ing', logtype = 'warning', flag = 'tree sync')
    await tree.sync()
    ilog(f'Command tree synced via /sync by {interaction.user.id} ({interaction.user.display_name}#{interaction.user.discriminator})', logtype = 'warning', flag = 'tree')
    ilog('Unlocking the bot', logtype = 'info', flag = 'tree sync')
    maintenance_status = configurations.default_maintenance_status
    await asyncio.sleep(20)
    ilog('Restarting looptasks', logtype = 'info', flag = 'tree sync')
    for task in client.taskloops(): task.start()
    await interaction.followup.send(embed=Embed(title="Command tree synced", description='Successfully synced the global command tree to all guilds').uniform(interaction), ephemeral=silent)
    await client.change_presence(activity=Game('synced. reloading...'), status=Status.dnd)
    elapsed = time() - elapsed
    elapsed = int(elapsed * 1000)
    ilog(f'Finished syncing in {elapsed}ms', logtype = 'info', flag = 'tree sync')
class sys(Group):
    @staticmethod
    async def is_authorized(interaction: Interaction, followup: bool = True):
        i = interaction.user.id in configurations.owner_ids
        if not i:
            embed = Embed(title="Unauthorized", description="You are not allowed to use this command.").uniform(interaction)
            await interaction.followup.send(embed=embed, ephemeral=True) if followup else await interaction.response.send_message(embed=embed, ephemeral=True)
        return i
    class evalModal(Modal, title='System eval()'):
        def __init__(self, main) -> None:
            super().__init__()
            self.main = main
            self.result = ""
        script = TextInput(label = 'Enter the script', style = TextStyle.paragraph, max_length = 2000, required=True, placeholder="Enter your script here...")
        async def on_submit(self, interaction: Interaction):
            await interaction.response.defer()
            guess = str(self.script)
            self.result = guess
            self.stop()

    @command(name='eval', description='system - execute python scripts via eval()')
    @describe(silent = 'Whether you want the output to be sent to you alone or not', script = 'The script you want to execute, leave blank if you want a modal ask for the code. (which can be multi-line-ed)', awaited = '(default: False) If you want to turn the script into a coroutine that runs asynchronously')
    async def scripteval(self, interaction: Interaction, script: str = '', awaited: bool = False, silent: bool = False):
        if script == '':
            if not await self.is_authorized(interaction, False): return
            modal = self.evalModal(self)
            await interaction.response.send_modal(modal)
            await modal.wait()
            script = modal.result
        else:
            await interaction.response.defer(ephemeral=silent)
            if not await self.is_authorized(interaction): return
        await interaction.followup.send(embed=Embed(title='Executing...', description='Executing the script...').uniform(interaction), wait=True, ephemeral=True)
        await asyncio.sleep(0.5)
        ilog(f'{interaction.user.name}#{interaction.user.discriminator} ({interaction.user.id}) eval-ed: {script}', 'eval', 'warning')
        if not awaited: result = eval(script)
        else: result = await eval(script)
        if not result: await interaction.followup.send(ephemeral=silent, embed=Embed(title="Script executed", description='Script executed successfully, the result, might be `None` or too long to fill in here.').uniform(interaction))
        else: await interaction.followup.send(ephemeral=silent, embed=Embed(title="Result", description= "```py\n" + str(result) + "```", ).uniform(interaction))
    @command(name = 'guilds', description= 'system - list guilds that the bot are currently in.')
    @describe(silent = 'Whether you want the output to be sent to you alone or not')
    async def guilds(self, interaction: Interaction, silent: bool = True):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        embed = Embed(title = 'Guilds list:', description= 'Here is the list of guilds that have this bot in:')
        if len(k:=client.guilds) <= 30:
            current_list = ""
            for i in k:
                current_list += f'{i.id}: {i.name}\n'
        else:
            current_list = "<too many guilds>"
        embed.add_field(name = 'Guilds:', value = f"`{current_list}`")
        await interaction.followup.send(embed=embed, ephemeral=silent)
    whitelist = Group(name='whitelist', description='Get and modify the beta whitelist in the database')
    @whitelist.command(name = 'list', description ='system - Get beta whitelist list in whitelist.json')
    @describe(silent = 'Whether you want the output to be sent to you alone or not')
    async def whitelist_list(self, interaction: Interaction, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return

        embed = Embed(title='Whitelist list', description='Here is the list of beta-whitelisted user IDs:').uniform(interaction)
        current_list = ""
        for i in await get_user_whitelist():
            current_list += f'<@{i}> ({i})\n'
        embed.add_field(name='Users:', value = current_list)
        await interaction.followup.send(embed=embed, ephemeral=silent)

    # @tree.command(name = 'whitelist_modify', description='Modify beta whitelist list in database.json')
    @whitelist.command(name = 'modify', description='system - Modify beta whitelist list in database.json')
    @describe(user = 'User that will be modified in the whitelist database', mode = 'add/remove the user from the database', silent = 'Whether you want the output to be sent to you alone or not')
    async def whitelist_modify(self, interaction: Interaction, user: Member, mode: typing.Literal['add', 'remove'] = 'add', silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        
        try:
            update_status = await update_user_whitelist(user = user.id, add = mode == 'add')
            await interaction.followup.send(embed=Embed(title='Done', description=f'Successfully {"added" if mode == "add" else "removed"} this user in the list: {user.mention} ({user.id})').uniform(interaction) if update_status else Embed(title='Failed', description='A error occured').uniform(interaction), ephemeral=silent)
        except Exception as e:
            ilog('Exception in command /whitelist_modify:' + e, logtype= 'error', flag = 'command')
            await interaction.followup.send(ephemeral= True, embed=Embed(title="Exception occurred", description=str(e), ).uniform(interaction))

class locsys(Group):
    @staticmethod
    async def is_authorized(interaction: Interaction):
        i = interaction.user.id in configurations.owner_ids
        if not i:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You are not allowed to use this command.").uniform(interaction), ephemeral=True)
        return i
    @command(name='version', description='system - check the code version')
    @describe(silent = 'Whether you want the output to be sent to you alone or not')
    async def version(self, interaction: Interaction, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if (not configurations.is_replit) or (not configurations.no_git_automation): await interaction.followup.send(embed=Embed(title="Unsupported", description='The bot is deployed on a system that can auto-update itself.').uniform(interaction), ephemeral=silent); return
        if not await self.is_authorized(interaction): return
        await interaction.followup.send(ephemeral=silent, embed=Embed(title = 'Bot version:', description= f'Bot version {configurations.bot_version}').uniform(interaction))

    @command(name = 'maintenance', description='Toggle maintenance mode for supported commands')
    @describe(status_to_set = 'Status of maintenance to set into the database', silent = 'Whether you want the output to be sent to you alone or not')
    async def maintenance(self, interaction: Interaction, status_to_set: bool = False, silent: bool = True):
        await interaction.response.defer(ephemeral = silent)
        if not await self.is_authorized(interaction): return
        global maintenance_status
        old = maintenance_status
        maintenance_status = status_to_set
        await interaction.followup.send(embed=Embed(title='Success', description=f'Maintenance status changed: {old} -> {maintenance_status}').uniform(interaction))


tree.add_command(locsys(), guild=Object(id=configurations.owner_guild_id))
tree.add_command(sys())


"""
-------------------------------------------------
FEATURE COMMANDS (beta)
/game
    |-- wordle
/net
    |-- screenshot
    |-- ip
    |-- deshorten
-------------------------------------------------
"""

class game_wordle():
    "This class is used for the command /game wordle; the only method should be used is .start() -> return the ui.View to the user"
    # TODO: analysis: word difficulty,  word length, word frequency...
    def __init__(this, interaction: Interaction) -> None:
        this.interaction = interaction
        this.tries = 6
        this.secret_word = None
        this.tried = []
        this.tried_efficiency = []

    async def gameplay(this):
        if this.secret_word is None: this.secret_word = (await this.get_word()).get("word", "smhhh")
        embed = Embed(title="Wordle")
        embed.description = "Make a guess by click the green guess button below!\n`Your guesses:` ```\n" + "\n".join(this.tried) + "```"
        embed.uniform(this.interaction)
        await this.interaction.edit_original_response(embed=embed, view=this.play())
    
    @staticmethod
    async def compare_word(word: str, secret: str, forced: bool = False):
        "This method is used to compare 2 words."
        'response format: {"invalid": invalid, "invalid_type": invalid_type, "comparision": comparision, "efficiency": efficiency, "won": won}'
        "invalid types: 0 - nothing; 2 - contain non-letter; 3 - not in the dictionary"
        invalid = False
        invalid_type = 0
        comparision = ""
        won = False
        efficiency = 0 # 0 -> 100
        while True:
            if not forced:
                # check if the word contain non-alphabet characters
                if any(letter not in "abcdefghijklmnopqrstuvwxyz" for letter in word): invalid_type = 2; invalid = True; break
                # check if the word is not in the dictionary
                querystring = {"term": word}
                headers = {
                    "X-RapidAPI-Key": configurations.rapidapi_key,
                    "X-RapidAPI-Host": "mashape-community-urban-dictionary.p.rapidapi.com"
                }
                async with ClientSession(headers = headers) as session:
                    async with session.get(f'https://mashape-community-urban-dictionary.p.rapidapi.com/define', params = querystring) as response:
                        data = await response.json()
                        if len(data.get("list", [])) == 0: invalid_type = 3; invalid = True; break
            # compare the word (valid) to the secret word
            if word == secret: won = True; efficiency = 100; break
            word = list(word)
            temp = list(word)[:]
            secret = list(secret)
            for i in range(5):
                if word[i] == secret[i]:
                    temp[i] = f"[{word[i]}]"
                    secret[i] = "_"
                    efficiency += 20
            for i in range(5):
                if word[i] in secret and temp[i] == word[i]: # in case the letter is already checked
                    temp[i] = f"<{word[i]}>"
                    secret[secret.index(word[i])] = "_"
                    efficiency += 10
            comparision = "".join(temp)
            break
        return {"invalid": invalid, "invalid_type": invalid_type, "comparision": comparision, "efficiency": efficiency, "won": won}
    
    @staticmethod
    async def get_word():
        "This method is used to get a random 5 letter word from the API"
        word = None
        success = True
        async with ClientSession() as session:
            async with session.get('https://random-word-api.herokuapp.com/word?length=5') as response: 
                try:
                    response.raise_for_status()
                    word = (await response.json())[0]
                except Exception as e:
                    success = False
        return {"word": word, "success": success}
    
    def start(this) -> None:
        return this.startView(this)
    def play(this) -> None:
        return this.gameplayView(this)
    def guess(this) -> None:
        return this.guessModal(this)
    async def won(this) -> None:
        embed = Embed(title="Wordle")
        embed.description = f"**You won with {this.tries} trie(s) left!** :heart:\nThe secret word was: `{this.secret_word}`\nYour guesses: ```\n" + "\n".join(this.tried) + "```"
        underline = "\n"
        embed.add_field(name = "*Analysis*", value = f"""*Secret word difficulty*: *<comming soon>*\n*Guess efficiency*: \n```{underline.join(map(lambda x: str(x) + "%", this.tried_efficiency))}```""")
        embed.uniform(this.interaction)
        await this.interaction.edit_original_response(embed = embed, view = None)
        # GAME ENdED
    async def lost(this) -> None:
        embed = Embed(title="Wordle")
        embed.description = f"**You lost!** :joy: \nThe secret word was: `{this.secret_word}`\nYour guesses: ```\n" + "\n".join(this.tried) + "```"
        underline = '\n'
        embed.add_field(name = "*Analysis*", value = f"""- *Secret word difficulty*: *<comming soon>*\n- *Guess efficiency*: ```{underline.join(map(lambda x: str(x) + "%", this.tried_efficiency))}```""")
        embed.uniform(this.interaction)
        await this.interaction.edit_original_response(embed = embed, view = None)
    
    class guessModal(Modal, title='Guess your Wordle'):
        def __init__(self, main) -> None:
            super().__init__()
            self.main = main
        word = TextInput(label = 'Enter your guess', style = TextStyle.short, min_length=5, max_length = 5, required=True, placeholder="Only enter lowercase letters from a-z...")
        async def on_submit(self, interaction: Interaction):
            await interaction.response.defer()
            guess = str(self.word).lower()
            compared = await self.main.compare_word(guess, self.main.secret_word)
            if compared.get("invalid", True):
                match compared["invalid_type"]:
                    case 1:
                        error_msg = "Your guess should be a 5-letter word."
                    case 2:
                        error_msg = "Your guess should only contain letters."
                    case 3:
                        error_msg = "Your guess-ed word is not in the dictionary."
                await interaction.followup.send(error_msg, ephemeral = True)
                return
            self.main.tries -= 1
            self.main.tried.append(compared.get("comparision"))
            self.main.tried_efficiency.append(compared.get("efficiency"))
            if compared.get("won", False):
                await self.main.won() # END GAME
                return
            if self.main.tries > 0:
                await self.main.gameplay() # back to gameplay
                return
            else:
                await self.main.lost() # END GAME
                return

    class gameplayView(View):
        def __init__(self, main) -> None:
            super().__init__(timeout=240)
            self.main = main
        async def on_timeout(self):
            for child in self.children: child.disabled = True
            await self.main.interaction.edit_original_response(content = "This message is now disabled due to inactivity.", view=None)
        @button(label='Guess', style=ButtonStyle.green)
        async def guess(self, interaction: Interaction, button: Button):
            if self.main.interaction.user.id != interaction.user.id:
                await interaction.followup.send("This is not your game, you can't make a guess.", ephemeral=True)
                return
            await interaction.response.send_modal(self.main.guess())
            return
        
    class startView(View):
        def __init__(self, main) -> None:
            super().__init__()
            self.main = main
        async def on_timeout(self):
            return
        @button(label = 'Start', style = ButtonStyle.green)
        async def start(self, interaction: Interaction, button: Button):
            if self.main.interaction.user.id  != interaction.user.id:
                await interaction.followup.send("This is not your game, you can't start it.", ephemeral=True)
                return
            await self.main.gameplay()
            await interaction.response.defer()
            return
        @button(label = 'Cancel', style = ButtonStyle.gray)
        async def cancel(self, interaction: Interaction, button: Button):
            if self.interaction.user.id != interaction.user.id:
                await interaction.followup.send("This is not your game, you can't cancel it.", ephemeral=True)
            for child in self.children: child.disabled = True
            return

class game(Group):
    @staticmethod
    async def is_authorized(interaction: Interaction):
        if maintenance_status:
            await interaction.followup.send(embed = Embed(title='Maintaining', description='The bot is not ready to use yet, please wait a little bit.').uniform(interaction))
            return False
        if interaction.user.id in configurations.owner_ids:
            return True
        elif not interaction.guild_id is not None:
            await interaction.followup.send(embed=Embed(title='Error', description='This command can only be used in a server.').uniform(interaction))
            return False
        elif not interaction.guild_id in [guild.id for guild in client.guilds]:
            await interaction.followup.send(embed=Embed(title='Error', description='This server is trying to use this bot as a integration for application commands, which is NOT allowed. Please consider adding the bot to the server.').uniform(interaction))
            return False
        elif not await check_user_whitelist(user = interaction.user.id):
            await interaction.followup.send(embed = Embed(title='Unauthorized', description='This command is in beta mode, only whitelisted user can access; try asking a developer to whitelist you.').uniform(interaction))
            return False
        return True

    @command(name='wordle', description='BETA - Play Wordle in Discord.')
    @describe(silent = 'Whether you want the output to be sent to you alone or not')
    async def wordle(self, interaction: Interaction, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        instance = game_wordle(interaction)
        view = instance.start()
        await interaction.followup.send(embed=Embed(title='Wordle', description='- Guess the Wordle in 6 tries.\n- Each guess must be a valid 5-letter word.\n- The letter indicators will change to show how close your guess was to the word. Examples:\n```[W]EARY\nW is in the word and in the correct spot.\nP<I>LLS\nI is in the word but in the wrong spot.```')\
                                        .uniform(interaction), view=view, ephemeral=silent)

tree.add_command(game())

class tool(Group):
    @staticmethod
    async def is_authorized(interaction: Interaction):
        if maintenance_status:
            await interaction.followup.send(embed = Embed(title='Maintaining', description='The bot is not ready to use yet, please wait a little bit.').uniform(interaction))
            return False
        if interaction.user.id in configurations.owner_ids:
            return True
        elif not interaction.guild_id is not None:
            await interaction.followup.send(embed=Embed(title='Error', description='This command can only be used in a server.').uniform(interaction))
            return False
        elif not interaction.guild_id in [guild.id for guild in client.guilds]:
            await interaction.followup.send(embed=Embed(title='Error', description='This server is trying to use this bot as a integration for application commands, which is NOT allowed. Please consider adding the bot to the server.').uniform(interaction))
            return False
        elif not await check_user_whitelist(user = interaction.user.id):
            await interaction.followup.send(embed = Embed(title='Unauthorized', description='This command is in beta mode, only whitelisted user can access; try asking a developer to whitelist you.').uniform(interaction))
            return False
        return True
    @staticmethod
    def getTOTP(secret: str):
        try:
            result = TOTP(secret).now()
        except binascii.Error:
            result = 'Invalid secret'
        return result
    @command(name='totp', description='BETA - Instantly generate a TOTP code from your secret.') 
    @describe(secret = 'The secret key for TOTP', silent = 'Whether you want the output to be sent to you alone or not')
    async def totp(self, interaction: Interaction, secret: str, silent: bool = True):
        secret = secret.replace(' ', '')
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        await interaction.followup.send(embed=Embed(title='TOTP', description=f'`{self.getTOTP(secret)}`').uniform(interaction), ephemeral=silent)

tree.add_command(tool())

class net(Group):
    @staticmethod
    async def is_authorized(interaction: Interaction):
        if maintenance_status:
            await interaction.followup.send(embed = Embed(title='Maintaining', description='The bot is not ready to use yet, please wait a little bit.').uniform(interaction))
            return False
        if interaction.user.id in configurations.owner_ids:
            return True
        elif not interaction.guild_id is not None:
            await interaction.followup.send(embed=Embed(title='Error', description='This command can only be used in a server.').uniform(interaction))
            return False
        elif not interaction.guild_id in [guild.id for guild in client.guilds]:
            await interaction.followup.send(embed=Embed(title='Error', description='This server is trying to use this bot as a integration for application commands, which is NOT allowed. Please consider adding the bot to the server.').uniform(interaction))
            return False
        elif not await check_user_whitelist(user = interaction.user.id):
            await interaction.followup.send(embed = Embed(title='Unauthorized', description='This command is in beta mode, only whitelisted user can access; try asking a developer to whitelist you.').uniform(interaction))
            return False
        return True
    @staticmethod
    async def get_ip_info(ip) -> dict:
        async with ClientSession() as session:
            async with session.get(f'https://beta.iprisk.info/v1/{ip}') as response:
                data = await response.json()
            return data
    @staticmethod
    async def get_unshortened(url: str, debugmsg: Webhook, api_url=configurations.unshortenapi, token=configurations.unshortensecret):
        'response example: {"success": success, "redirect_list": redirect_list, "error": error, "api_elapsed": api_elapsed}'
        success = True
        redirect_list = []
        error = ""
        api_elapsed = 0
        headers = {'url': url, 'authorization': token}
        while True:
            debugem = Embed(title="Processing your request...")
            debugem.description = "[...] Validating data\n[] Connect to the API\n[] Fetch redirect list\n[] Return redirect list"
            await debugmsg.edit(embed = debugem)
            debugem.description = "[OK] Validate data\n[...] Waiting API to finish\n[] Fetch redirect list\n[] Return redirect list"
            await debugmsg.edit(embed = debugem)
            async with ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    try:
                        response.raise_for_status()
                        'data example: Response({"redirects": redirect_list}, headers={"X-Elapsed-Time": str(elapsed)})'
                        data = await response.json()
                        debugem.description = "[OK] Validate data\n[OK] Connect to the API\n[...] Fetch redirect list\n[] Return redirect list"
                        await debugmsg.edit(embed = debugem)
                        redirect_list = data.get('redirects', ['unspecified error'])
                        api_elapsed = str(data.get('elapsed', 'unspecified error'))
                    except Exception as e:
                        success = False
                        error = str(e)
                        debugem.description = "ERROR"
                        await asyncio.sleep(1)
                        await debugmsg.edit(embed = debugem)
                        break
            debugem.description = "[OK] Validate data\n[OK] Connect to the API\n[OK] Fetch redirect list\n[...] Returning redirect list"
            await debugmsg.edit(embed = debugem)
            break
        return {"success": success, "redirect_list": redirect_list, "error": error, "api_elapsed": api_elapsed}

    @staticmethod
    async def get_screenshot(url, resolution, delay, debugmsg: Webhook, api_url=configurations.screenshotapi, token=configurations.screenshotsecret):
        'response example: {"success": success, "image_data": image_data, "error": error, "api_elapsed": api_elapsed}'
        success = True
        error: str = ""
        image_data = None
        api_elapsed = 0
        params = {'resolution': resolution, 'delay': delay} #, 'authorization': token}
        headers = {'url': url, 'authorization': token}
        while True:
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
                        api_elapsed = float(response.headers.get("X-Elapsed-Time"))
                    except Exception as e:
                        success = False
                        error = e
                        break
            debugem.description = "[OK] Validate data\n[OK] Connect to the API\n[OK] Fetch image\n[...] Returning image"
            await debugmsg.edit(embed = debugem)
            break
        return {"success": success, "image_data": image_data, "error": error, "api_elapsed": api_elapsed}
    @staticmethod
    async def get_domaininfo(url: str, apikey: configurations = configurations.webresolverapi):
        async with ClientSession() as session:
            async with session.get(f'https://webresolver.nl/api.php?key={apikey}&action=dns&string={url}') as response:
                dns = await response.text()
            async with session.get(f'https://webresolver.nl/api.php?key={apikey}&action=geoip&string={url}') as response:
                geoip = await response.text()
        return dns, geoip

    #@command(name='rayso', description='BETA - Create beautiful images of your code using ray.so')
    #@describe(title="The title of the code snippet", theme="The color scheme of the code you want to use", background="Whether you want a background or not", darkMode="Whether you want dark mode or not", padding="The padding around the content of the code snippet", language="The language the code is in", silent="Whether you want the output to be sent to you alone or not")
    #@choices(theme=[Choice(value=i, name=k) for i, k in [('breeze', 'Breeze'), ('candy', 'Candy'), ('crimson', 'Crimson'), ('falcon', 'Falcon'), ('meadow', 'Meadow'), ('midnight', 'Midnight'), ('raindrop', 'Raindrop'), ('sunset', 'Sunset')]], padding=[Choice(value=i, name=k) for i, k in [(16, 'small: 16'), (32, 'medium: 32'), (64, 'large: 64'), (128, 'xtralarge: 128')]], language=None)
    async def rayso(self, interaction: Interaction, title: str = 'main', theme: str = 'breeze', background: bool = True, darkMode: bool = True, padding: int = 32, language: str = 'auto', silent: bool = False):
        # await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        # TODO: send a modal/view to get the code, process it and send it to the API, and then return the image.

    @command(name='screenshot', description='BETA - Take a screenshot of a website')
    @describe(url='URL of the website you want to screenshot. (Include https:// or http://)', delay='Delays for the driver to wait after the website stopped loading (in seconds, max 20s) (default: 0)', resolution = 'Resolution of the driver window (Default: 720p)', silent = 'Whether you want the output to be sent to you alone or not')
    @choices(resolution = [Choice(value=i, name=k) for i, k in [(240, '240p - Minimum'), (360, '360p - Website'), (480, '480p - Standard'), (720, '720p - HD'), (1080, '1080p - Full HD'), (1440, '1440p - 2K'), (2160, '2160p - 4K')]]) # , ('undetected_selenium', 'Selenium + Undetected Chromium (for bypassing)') # engine = [Choice(value=i, name=k) for i, k in [('selenium', 'Selenium + Chromium'), ('playwright', 'Playwright + Chromium')]]
    @cooldown(1, 60, key = lambda interaction: (interaction.user.id, time() if interaction.user.id in configurations.owner_ids else 0)) # unique cooldown object if the user is the owner
    async def screenshot(self, interaction: Interaction, url: str, delay: Range[int, 1, 20] = 0, resolution: int = 720, silent: bool = False):
        global global_ratelimit
        await interaction.response.defer(ephemeral = True)
        # conditions to stop executing the command
        if not await self.is_authorized(interaction): return 
        if not url.startswith('http'):
            await interaction.followup.send(embed=Embed(title='Error', description='Please provide a valid URL, including http or https.', ).uniform(interaction), ephemeral = silent)
            return
        if any(url.startswith(i) for i in [x + y for x in ['http://', 'https://'] for y in ['0.0.0.0', '127.0.0.1', 'localhost']]):
            await interaction.followup.send(embed=Embed(title='Error', description='Please do not try to access localhost.', ).uniform(interaction), ephemeral = silent)
            return
        if global_ratelimit >= configurations.max_global_ratelimit:
            await interaction.followup.send(embed=Embed(title='Rate-limited', description='Bot is currently global rate-limited, please try again later').uniform(interaction), ephemeral= True)
            return
        msg = await interaction.followup.send(embed=Embed(title = 'Processing your request...'), ephemeral=True)
        await asyncio.sleep(1)
        global_ratelimit += 1 # get_screenshot_undetected_chromedriver
        els = time()
        data = await self.get_screenshot(url=url, resolution=resolution, delay=delay, debugmsg=msg)
        global_ratelimit += -1
        global_elapsed = round(1000*(time() - els))
        await msg.edit(embed=Embed(title="Finished", description="Your request has been processed.").uniform(interaction))
        if data["success"]:
            image_bytes = data["image_data"]
            local_elapsed = data["api_elapsed"]
            embed = Embed(title='Success',description=f'Here is the website screenshot of {url} \n||*(took {f"{global_elapsed}ms" if global_elapsed < 2000 else f"{round(global_elapsed/1000)}s"} globally, {f"{local_elapsed}ms" if local_elapsed < 2000 else f"{round(local_elapsed/1000)}s"} for the API to work, elapsed times including requested delays)*||', ).uniform(interaction)
            embed.set_image(url='attachment://screenshot.png')
            await interaction.followup.send(ephemeral = silent, embed=embed, file=File(BytesIO(image_bytes), filename='screenshot.png'))
        else:
            await interaction.followup.send(ephemeral = silent, embed=Embed(title='Error', description=f'Failed to get the screenshot from the API, ask developers for more details... [API error?]').uniform(interaction))   
    @command(name = 'ip', description='Use APIs to fetch information about a IPv4 address.')
    @describe(ipv4 = "The IPv4 address you want to fetch.", silent = 'Whether you want the output to be sent to you alone or not')
    @cooldown(1, 60, key = lambda interaction: (interaction.user.id, time() if interaction.user.id in configurations.owner_ids else 0))
    # @choices(ipv4 = [Choice(value = i) for i in [f"{x}.{y}.{z}.{t}" for x in range(0, 255) for y in range(0, 255) for z in range(0, 255) for t in range(0, 255)]])
    async def ip(self, interaction: Interaction, ipv4: str, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        if not (lambda ip: len(x:= ip.split('.')) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in x))(ipv4):
            await interaction.followup.send(embed=Embed(title='Error', description='Input IPv4 address is invalid.', ).uniform(interaction), ephemeral = silent)
            return
        ipdata = await self.get_ip_info(ipv4)
        embed = Embed(title=f"IP information", description= f"Here's the information for `{ipv4}`:")
        fieldlist = [("null", "null")]
        if "error" in ipdata:
            err = ipdata.get("error")
            fieldlist = [
                ("Error", err.get("message", None)),
                ("Status", err.get("status", None)),
            ]
            #   "data_center": false, "public_proxy": false, "tor_exit_relay": false,
            # This address may be anonymised and belongs to a data-center or related
        else:
            if ipdata.get("data_center", False) or ipdata.get("public_proxy", False) or ipdata.get("tor_exit_relay", False):
                embed.color = Color.yellow()
                specialip = ["belongs to a data-center" if ipdata.get("data_center", False) else "",\
                            "be a public proxy" if ipdata.get("public_proxy", False) else "",\
                                "be a Tor exit relay" if ipdata.get("tor_exit_relay", False) else ""]
                notes = "This IP might " + "/ ".join([i for i in specialip if i != ""])
            else:
                notes = None
            fieldlist = [
                ("Notes", notes),
                ("IP", ipdata.get("ip", None)),
                ("Continent", f'{ipdata.get("continent_name", "null")} | {ipdata.get("continent_code", "null")}'),
                ("Country", f'{ipdata.get("country_name", "null")} | {ipdata.get("country_code", "null")} {ipdata.get("country_flag_emoji", "?")}'),
                ("City", ipdata.get("city_name", None)),
                ("Region", f'{ipdata.get("region_name", "null")} | {ipdata.get("region_code", "null")}'),
                ("\u200B", "\n"),  # blank field separator
                ("Network Route", ipdata.get("ip_range", None)),
                ("AS Number", ipdata.get("autonomous_system_number", None)),
                ("AS Organization", f'{ipdata.get("autonomous_system_organization", "null")} | {ipdata.get("autonomous_system_organization_alt", "?")}'),
                ("Location (lat, long)", f'{ipdata.get("latitude", "null")}, {ipdata.get("longitude", "null")}'),
                ("Time Zone", ipdata.get("time_zone", None))
            ]
        for field_name, field_value in fieldlist:
            if field_value is None or "null" in str(field_value): continue
            embed.add_field(name=field_name, value=f'`{field_value}`' if field_value else "", inline=False)
        embed.uniform(interaction)
        await interaction.followup.send(embed = embed, ephemeral=silent)
    @command(name = 'unshortener', description='Capture redirects from a URL and return the final URL.')
    @describe(url = "The URL you want to unshorten.", silent = 'Whether you want the output to be sent to you alone or not')
    async def unshorten_url(self, interaction: Interaction, url: str, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        if not url.startswith('http'):
            await interaction.followup.send(embed=Embed(title='Error', description='Please provide a valid URL, including http or https.', ).uniform(interaction), ephemeral = silent)
            return
        if any(url.startswith(i) for i in [x + y for x in ['http://', 'https://'] for y in ['0.0.0.0', '127.0.0.1', 'localhost']]):
            await interaction.followup.send(embed=Embed(title='Error', description='Please do not try to access localhost.', ).uniform(interaction), ephemeral = silent)
            return
        msg = await interaction.followup.send(embed=Embed(title = 'Processing your request...'), ephemeral=True)
        await asyncio.sleep(1)
        global global_ratelimit
        global_ratelimit += 1
        els = time()
        data = await self.get_unshortened(url=url, debugmsg=msg)
        global_ratelimit += -1
        global_elapsed = round(1000*(time() - els))
        await msg.edit(embed=Embed(title="Finished", description="Your request has been processed.").uniform(interaction))
        if data["success"]:
            redirects = data.get("redirect_list", [])
            if len(redirects) > 1 :
                local_elapsed = data["api_elapsed"]
                embed = Embed(title='Success',description=f'Here is the information you need got from {url} \n||*(took {f"{global_elapsed}ms" if global_elapsed < 2000 else f"{round(global_elapsed/1000)}s"} globally, {f"{local_elapsed}ms" if local_elapsed < 2000 else f"{round(local_elapsed/1000)}s"} for the API to work, elapsed times including requested delays)*||', ).uniform(interaction)
                embed.add_field(name = 'Final URL', value = f'**{redirects[-1]}**')
                if len(redirects) != 2:
                    embed.add_field(name = 'Traceroute', value = f'[{redirects[0]}]' + '\n' + '\n-> [passive]'.join([f'({i})' for i in redirects[1:-1]]) + '\n=> ' + redirects[-1])
                else:
                    embed.add_field(name = 'Traceroute', value = f'[{redirects[0]}]' + '\n=> ' + redirects[-1])
            else:
                embed = Embed(title='Success', description="There's no redirect for this URL.").uniform(interaction)
            await interaction.followup.send(ephemeral = silent, embed=embed)
        else:
            await interaction.followup.send(ephemeral = silent, embed=Embed(title='Error', description=f'Failed to get redirects from the URL, ask developers for more details... [API error?]').uniform(interaction))   


tree.add_command(net())

@tree.command(name='info', description='Returns the bot information.')
@describe(silent = 'Whether you want the output to be sent to you alone or not')
async def info(interaction: Interaction, silent: bool = False):
    await interaction.response.defer(ephemeral=silent)
    embed = Embed(title="Bot information: ")
    embed.description = f'```ansi\nPython {sysio.version} on {sysio.platform}\nType "help", "copyright", "credits" or "license" for more information.\n>>>\n```'
    embed.add_field(name = 'OS, Architecture', value = f"{platform.system()} ({os.name}) {platform.release()}", inline = False)
    embed.add_field(name = 'CPU load', value = f"{psutil.cpu_percent()}% ({psutil.cpu_count()} cores)", inline = True)
    embed.add_field(name = 'Memory usage', value = f"{psutil.virtual_memory().percent}% ({round(psutil.virtual_memory().used/1024/1024/1024, 2)}GB/{round(psutil.virtual_memory().total/1024/1024/1024, 2)}GB)", inline = True)
    embed.add_field(name = 'Disk usage', value = f"{psutil.disk_usage('/').percent}% ({round(psutil.disk_usage('/').used/1024/1024/1024, 2)}GB/{round(psutil.disk_usage('/').total/1024/1024/1024, 2)}GB)", inline = True)
    embed.add_field(name = 'Bot username, ID', value = f"{client.user} ({client.user.id})", inline = False)
    embed.add_field(name = 'Uptime', value = f"<t:{unix_uptime}:R> (<t:{unix_uptime}:T> <t:{unix_uptime}:d>)", inline = True)
    embed.add_field(name = 'Guilds/Servers', value = f"{len(client.guilds)}", inline = True)
    embed.add_field(name = 'API latency', value = f"{round(client.latency*1000)}ms", inline = True)
    embed.uniform(interaction)
    await interaction.followup.send(embed = embed, ephemeral=silent)

"""
-------------------------------------------------
BOOT
-------------------------------------------------
"""


def run():
    # some checks before run, soonTM
    if configurations.using_sentry:
        ilog('Initializing Sentry...', 'init', 'info')
        sentry_sdk.init(dsn=configurations.sentry_dsn, traces_sample_rate=1.0)
        ilog('Sentry is ready!', 'init', 'info')
    ilog('Starting Discord client...', 'init', 'info')
    client.run(token = configurations.bot_token, log_formatter=CustomFormatter())
if __name__ == '__main__':
    run()