"""---------------------------------------------
Check .env.example to setup the bot.
---------------------------------------------"""
from discord import Intents, Client, Interaction, Object, Embed, File, Game, Status, Member, Webhook, ButtonStyle, TextStyle
from discord.app_commands import CommandTree, Group, command, Choice, choices, describe, Range
from discord.ui import button, View, Modal, Button, TextInput
from jsondb import check_bot_version, get_user_whitelist, update_user_whitelist, check_user_whitelist
import logging, json, typing, functools, traceback, asyncio, json, sentry_sdk
from aiohttp import ClientSession
from logger import CustomFormatter, ilog
from os import system
from time import time
from keep_alive import ka
from io import BytesIO
from configs import configurations

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


intents = Intents.default()
intents.members = True
class MyClient(Client):
    def __init__(self, *, intents: Intents) -> None:
        super().__init__(intents=intents)
        self.tree = CommandTree(self)
        return
    async def setup_hook(self):
        # varible reset
        global unix_uptime
        global global_ratelimit
        global maintenance_status
        global_ratelimit = 0
        maintenance_status = configurations.default_maintenance_status
        unix_uptime = round(time())
        # do syncs
        ilog("Syncing commands to the main guild...", 'init', 'info')
        # self.tree.copy_global_to(guild = Object(id=configurations.owner_guild_id))
        await self.tree.sync(guild = Object(id=configurations.owner_guild_id))
        ilog("Done! Bot will be ready soon", 'init', 'info')
        await asyncio.sleep(3)
        return

client = MyClient(intents=intents)
tree = client.tree

async def antiblock(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    func = functools.partial(blocking_func, *args, **kwargs)
    return await client.loop.run_in_executor(None, func)

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
    ilog('---Exception in a application command: ' + full_err + '--------------------end of exception--------------------', logtype= 'error', flag = 'command')
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
@describe(silent = 'Whether you want the output to be sent to you alone or not')
async def sync(interaction: Interaction, delay: Range[int, 0, 60] = 30, silent: bool = False):
    global maintenance_status
    await interaction.response.defer(ephemeral=silent)
    if interaction.user.id not in configurations.owner_ids:
        await interaction.followup.send(embed=Embed(title="Unauthorized", description="You are not allowed to use this command.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return
    await interaction.followup.send(embed=Embed(title="Syncing job requested", description='A sync job for this bot has been queued. All functions of the bot will be disabled to prevent ratelimit.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=silent)
    await client.change_presence(activity=Game('syncing...'), status=Status.dnd)
    maintenance_status = True
    await asyncio.sleep(delay)
    await tree.sync()
    ilog(f'Command tree synced via /sync by {interaction.user.id} ({interaction.user.display_name}', logtype = 'info', flag = 'tree')
    maintenance_status = configurations.default_maintenance_status
    await asyncio.sleep(10)
    await interaction.followup.send(embed=Embed(title="Command tree synced", description='Successfully synced the global command tree to all guilds').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=silent)
    await client.change_presence(activity=Game('synced. reloading...'), status=Status.dnd)
    await asyncio.sleep(5)
    await client.change_presence(activity=Game('version ' + configurations.bot_version + ' [outdated]' if not check_bot_version(configurations.bot_version) else ""), status=Status.online)

class sys(Group):
    @staticmethod
    async def is_authorized(interaction: Interaction):
        i = interaction.user.id in configurations.owner_ids
        if not i:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You are not allowed to use this command.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return i

    @command(name='eval', description='system - execute python scripts via eval()')
    @describe(silent = 'Whether you want the output to be sent to you alone or not', script = 'The script you want to execute', awaited = '(default: False) If you want to turn the script into a coroutine that runs asynchronously')
    async def scripteval(self, interaction: Interaction, script: str, awaited: bool = False, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        await interaction.followup.send(embed=Embed(title='Executing...', description='Executing the script...').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), wait=True)
        await asyncio.sleep(0.5)
        ilog(f'{interaction.user.name}#{interaction.user.discriminator} ({interaction.user.id}) eval-ed: {script}', 'eval', 'warning')
        script = script.encode()
        if not awaited:
            result = eval(script)
        else:
            result = await eval(script)
        if not result:
            await interaction.followup.send(ephemeral=silent, embed=Embed(title="Script executed", description='Script executed successfully, the result, might be `None` or too long to fill in here.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        else:
            await interaction.followup.send(ephemeral=silent, embed=Embed(title="Result", description= "```py\n" + str(result) + "```", ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
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

        embed = Embed(title='Whitelist list', description='Here is the list of beta-whitelisted user IDs:').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
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
            await interaction.followup.send(embed=Embed(title='Done', description=f'Successfully {"added" if mode == "add" else "removed"} this user in the list: {user.mention} ({user.id})').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar) if update_status else Embed(title='Failed', description='A error occured').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=silent)
        except Exception as e:
            ilog('Exception in command /whitelist_modify:' + e, logtype= 'error', flag = 'command')
            await interaction.followup.send(ephemeral= True, embed=Embed(title="Exception occurred", description=str(e), ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

class locsys(Group):
    @staticmethod
    async def is_authorized(interaction: Interaction):
        i = interaction.user.id in configurations.owner_ids
        if not i:
            await interaction.followup.send(embed=Embed(title="Unauthorized", description="You are not allowed to use this command.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=True)
        return i
    
    @command(name='update', description='system - update bot repo')
    @describe(silent = 'Whether you want the output to be sent to you alone or not')
    async def update_bot(self, interaction: Interaction, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if (not configurations.is_replit) or (not configurations.no_git_automation): await interaction.followup.send(embed=Embed(title="Unsupported", description='The bot is deployed on a system that can auto-update itself.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=silent); return
        if not await self.is_authorized(interaction): return
        
        ilog("Updating git repo...", 'git', 'warning')
        system('git fetch --all')
        system('git reset --hard origin/main')
        
        await interaction.followup.send(embed=Embed(title="Done", description='Successfully updated the bot repo on Github.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=silent)

    @command(name='version', description='system - check the code version')
    @describe(silent = 'Whether you want the output to be sent to you alone or not')
    async def version(self, interaction: Interaction, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if (not configurations.is_replit) or (not configurations.no_git_automation): await interaction.followup.send(embed=Embed(title="Unsupported", description='The bot is deployed on a system that can auto-update itself.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=silent); return
        if not await self.is_authorized(interaction): return
        await interaction.followup.send(ephemeral=silent, embed=Embed(title = 'Bot version:', description= f'Bot version {configurations.bot_version} {"[outdated]" if not check_bot_version(configurations.bot_version) else "[up-to-date]"}').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))

    @command(name='restart', description='system - Restart the bot')
    @describe(silent = 'Whether you want the output to be sent to you alone or not')
    async def restartbot(self, interaction: Interaction, silent: bool = True):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        if (not configurations.is_replit): await interaction.followup.send(embed=Embed(title="Unsupported", description='The bot is deployed on non-docker system.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=silent); return
        await interaction.followup.send(embed=Embed(title="Received", description="Restart request received, killing docker container...", ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral=silent)
        ilog(f'[+] Restart request by {interaction.user.id} ({interaction.user.display_name})', 'command', 'info')
        ilog('Restarting...', 'system', 'critical')
        await client.change_presence(status=Status.dnd, activity=Game('restarting...'))
        await asyncio.sleep(5)
        system('kill 1')

    @command(name = 'maintenance', description='Toggle maintenance mode for supported commands')
    @describe(status_to_set = 'Status of maintenance to set into the database', silent = 'Whether you want the output to be sent to you alone or not')
    async def maintenance(self, interaction: Interaction, status_to_set: bool = False, silent: bool = True):
        await interaction.response.defer(ephemeral = silent)
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
    def __init__(ego, interaction: Interaction) -> None:
        ego.interaction = interaction
        ego.tries = 6
        ego.secret_word = None
        ego.tried = []
        ego.tried_efficiency = []

    async def gameplay(ego):
        if ego.secret_word is None: ego.secret_word = (await ego.get_word()).get("word", "smhhh")
        embed = Embed(title="Wordle")
        embed.description = "Make a guess by click the green guess button below!\n`Your guesses:` ```\n" + "\n".join(ego.tried) + "```"
        embed.set_footer(text = f'Requested by {ego.interaction.user.name}#{ego.interaction.user.discriminator}', icon_url=ego.interaction.user.avatar)
        await ego.interaction.edit_original_response(embed=embed, view=ego.play())
    
    @staticmethod
    async def compare_word(word: str, secret: str):
        'response format: {"invalid": invalid, "invalid_type": invalid_type, "comparision": comparision, "efficiency": efficiency, "won": won}'
        "invalid types: 0 - nothing; 2 - contain non-letter; 3 - not in the dictionary"
        invalid = False
        invalid_type = 0
        comparision = ""
        won = False
        efficiency = 0 # 0 -> 100
        while True:
            if any(letter not in "abcdefghijklmnopqrstuvwxyz" for letter in word): invalid_type = 2; invalid = True; break
            querystring = {"term": word}
            headers = {
                "X-RapidAPI-Key": configurations.rapidapi_key,
                "X-RapidAPI-Host": "mashape-community-urban-dictionary.p.rapidapi.com"
            }
            async with ClientSession(headers = headers) as session:
                async with session.get(f'https://mashape-community-urban-dictionary.p.rapidapi.com/define', params = querystring) as response:
                    data = await response.json()
                    if len(data.get("list", [])) == 0: invalid_type = 3; invalid = True; break
            # compare the word (valid) to the secret word:-> NEED TO FIX
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
    
    def start(ego) -> None:
        return ego.startView(ego)
    def play(ego) -> None:
        return ego.gameplayView(ego)
    def guess(ego) -> None:
        return ego.guessModal(ego)
    async def won(ego) -> None:
        embed = Embed(title="Wordle")
        embed.description = f"**You won with {ego.tries} trie(s) left!** :heart:\nThe secret word was: `{ego.secret_word}`\nYour guesses: ```\n" + "\n".join(ego.tried) + "```"
        underline = "\n"
        embed.add_field(name = "*Analysis*", value = f"""- *Secret word difficulty*: *<comming soon>*\n- *Guess efficiency*: ```{underline.join(map(lambda x: str(x) + "%", ego.tried_efficiency))}```""")
        embed.set_footer(text = f'Requested by {ego.interaction.user.name}#{ego.interaction.user.discriminator}', icon_url=ego.interaction.user.avatar)
        await ego.interaction.edit_original_response(embed = embed, view = None)
        # GAME ENdED
    async def lost(ego) -> None:
        embed = Embed(title="Wordle")
        embed.description = f"**You lost!** :joy: \nThe secret word was: `{ego.secret_word}`\nYour guesses: ```\n" + "\n".join(ego.tried) + "```"
        underline = '\n'
        embed.add_field(name = "*Analysis*", value = f"""- *Secret word difficulty*: *<comming soon>*\n- *Guess efficiency*: ```{underline.join(map(lambda x: str(x) + "%", ego.tried_efficiency))}```""")
        embed.set_footer(text = f'Requested by {ego.interaction.user.name}#{ego.interaction.user.discriminator}', icon_url=ego.interaction.user.avatar)
        await ego.interaction.edit_original_response(embed = embed, view = None)

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
                if compared["invalid_type"] == 1:
                    error_msg = "Your guess should be a 5-letter word."
                elif compared["invalid_type"] == 2:
                    error_msg = "Your guess should only contain letters."
                elif compared["invalid_type"] == 3:
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
            await interaction.followup.send(embed = Embed(title='Maintaining', description='The bot is not ready to use yet, please wait a little bit.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
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
    @command(name='wordle', description='BETA - Play Wordle in Discord.')
    @describe(silent = 'Whether you want the output to be sent to you alone or not')
    async def wordle(self, interaction: Interaction, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        instance = game_wordle(interaction)
        view = instance.start()
        await interaction.followup.send(embed=Embed(title='Wordle', description='- Guess the Wordle in 6 tries.\n- Each guess must be a valid 5-letter word.\n- The letter indicators will change to show how close your guess was to the word. Examples:\n```[W]EARY\nW is in the word and in the correct spot.\nP<I>LLS\nI is in the word but in the wrong spot.```')\
                                        .set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), view=view, ephemeral=silent)

tree.add_command(game())

class net(Group):
    @staticmethod
    async def is_authorized(interaction: Interaction):
        if maintenance_status:
            await interaction.followup.send(embed = Embed(title='Maintaining', description='The bot is not ready to use yet, please wait a little bit.').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
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
    @staticmethod
    async def get_ip_info(ip) -> dict:
        async with ClientSession() as session:
            async with session.get(f'https://api.iprisk.info/v1/{ip}') as response:
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
            debugem = Embed(title="Processing your request...").description = "[...] Validating data\n[] Connect to the API\n[] Fetch redirect list\n[] Return redirect list"
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
                        api_elapsed = response.headers.get("X-Elapsed-Time")
                    except Exception as e:
                        success = False
                        error = e
                        break
            debugem.description = "[OK] Validate data\n[OK] Connect to the API\n[OK] Fetch image\n[...] Returning image"
            await debugmsg.edit(embed = debugem)
            break
        return {"success": success, "image_data": image_data, "error": error, "api_elapsed": api_elapsed}
    
    @command(name='screenshot', description='BETA - Take a screenshot of a website')
    @describe(url='URL of the website you want to screenshot. (Include https:// or http://)', delay='Delays for the driver to wait after the website stopped loading (in seconds, max 20s) (default: 0)', resolution = 'Resolution of the driver window (Default: 720p)', silent = 'Whether you want the output to be sent to you alone or not')
    @choices(resolution = [Choice(value=i, name=k) for i, k in [(240, '240p - Minimum'), (360, '360p - Website'), (480, '480p - Standard'), (720, '720p - HD'), (1080, '1080p - Full HD'), (1440, '1440p - 2K'), (2160, '2160p - 4K')]]) # , ('undetected_selenium', 'Selenium + Undetected Chromium (for bypassing)') # engine = [Choice(value=i, name=k) for i, k in [('selenium', 'Selenium + Chromium'), ('playwright', 'Playwright + Chromium')]]
    async def screenshot(self, interaction: Interaction, url: str, delay: Range[int, 1, 20] = 0, resolution: int = 720, silent: bool = False):
        global global_ratelimit
        await interaction.response.defer(ephemeral = True)
        # conditions to stop executing the command
        if not await self.is_authorized(interaction): return 
        if not url.startswith('http'):
            await interaction.followup.send(embed=Embed(title='Error', description='Please provide a valid URL, including http or https.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = silent)
            return
        if any(url.startswith(i) for i in [x + y for x in ['http://', 'https://'] for y in ['0.0.0.0', '127.0.0.1', 'localhost']]):
            await interaction.followup.send(embed=Embed(title='Error', description='Please do not try to access localhost.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = silent)
            return
        if global_ratelimit >= configurations.max_global_ratelimit:
            await interaction.followup.send(embed=Embed(title='Rate-limited', description='Bot is currently global rate-limited, please try again later').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral= True)
            return
        msg = await interaction.followup.send(embed=Embed(title = 'Processing your request...'), ephemeral=True)
        await asyncio.sleep(1)
        global_ratelimit += 1 # get_screenshot_undetected_chromedriver
        els = time()
        data = await self.get_screenshot(url=url, resolution=resolution, delay=delay, debugmsg=msg)
        global_ratelimit += -1
        global_elapsed = round(1000*(time() - els))
        await msg.edit(embed=Embed(title="Finished", description="Your request has been processed.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        if data["success"]:
            image_bytes = data["image_data"]
            embed = Embed(title='Success',description=f'Here is the website screenshot of {url} \n||*(took {global_elapsed}ms globally, {data["api_elapsed"]}ms for the API to work, elapsed times including requested delays)*||', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
            embed.set_image(url='attachment://screenshot.png')
            await interaction.followup.send(ephemeral = silent, embed=embed, file=File(BytesIO(image_bytes), filename='screenshot.png'))
        else:
            await interaction.followup.send(ephemeral = silent, embed=Embed(title='Error', description=f'Failed to get the screenshot from the API, ask developers for more details... [API error?]').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))   
    @command(name = 'ip', description='Use APIs to fetch information about a IPv4 address.')
    @describe(ipv4 = "The IPv4 address you want to fetch.", silent = 'Whether you want the output to be sent to you alone or not')
    # @choices(ipv4 = [Choice(value = i) for i in [f"{x}.{y}.{z}.{t}" for x in range(0, 255) for y in range(0, 255) for z in range(0, 255) for t in range(0, 255)]])
    async def ip(self, interaction: Interaction, ipv4: str, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        if not (lambda ip: len(x:= ip.split('.')) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in x))(ipv4):
            await interaction.followup.send(embed=Embed(title='Error', description='Input IPv4 address is invalid.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = silent)
            return
        ipdata = await self.get_ip_info(ipv4)
        embed = Embed(title=f"IP information", description= f"Here's the information for `{ipv4}`:")
        if "error" in ipdata:
            err = ipdata.get("error")
            fieldlist = [
                ("Error", err.get("message", None)),
                ("Status", err.get("status", None)),
            ]
        else:
            fieldlist = [
                ("IP", ipdata.get("ip", None)),
                ("Data Center", ipdata.get("data_center", None)),
                ("Continent", f'{ipdata.get("geo", {}).get("continent", "_")} | {ipdata.get("geo", {}).get("continent_code", "_")}'),
                ("Country", f'{ipdata.get("geo", {}).get("country", "_")} | {ipdata.get("geo", {}).get("country_code", "_")} {ipdata.get("geo", {}).get("country_flag_emoji", "?")}'),
                ("City", ipdata.get("geo", {}).get("city", None)),
                ("Region", f'{ipdata.get("geo", {}).get("region", "_")} | {ipdata.get("geo", {}).get("region_code", "_")}'),
                ("\u200B", "\n"),  # blank field separator
                ("Network Route", ipdata.get("network", {}).get("route", None)),
                ("AS Number", ipdata.get("network", {}).get("as_number", None)),
                ("AS Organization", f'{ipdata.get("network", {}).get("as_org", "_")} | {ipdata.get("network", {}).get("as_org_alt", "?")}')
            ]
        for field_name, field_value in fieldlist:
            if field_value is None: continue
            embed.add_field(name=field_name, value=f'`{field_value}`' if field_value else "", inline=False)
        embed.set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
        await interaction.followup.send(embed = embed, ephemeral=silent)
    @command(name = 'unshort_url', description='Capture redirects from a URL and return the final URL.')
    @describe(url = "The URL you want to unshorten.", silent = 'Whether you want the output to be sent to you alone or not')
    async def unshorten_url(self, interaction: Interaction, url: str, silent: bool = False):
        await interaction.response.defer(ephemeral=silent)
        if not await self.is_authorized(interaction): return
        if not url.startswith('http'):
            await interaction.followup.send(embed=Embed(title='Error', description='Please provide a valid URL, including http or https.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = silent)
            return
        if any(url.startswith(i) for i in [x + y for x in ['http://', 'https://'] for y in ['0.0.0.0', '127.0.0.1', 'localhost']]):
            await interaction.followup.send(embed=Embed(title='Error', description='Please do not try to access localhost.', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar), ephemeral = silent)
            return
        msg = await interaction.followup.send(embed=Embed(title = 'Processing your request...'), ephemeral=True)
        await asyncio.sleep(1)
        global global_ratelimit
        global_ratelimit += 1
        els = time()
        data = await self.get_unshortened(url=url, debugmsg=msg)
        global_ratelimit += -1
        global_elapsed = round(1000*(time() - els))
        await msg.edit(embed=Embed(title="Finished", description="Your request has been processed.").set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))
        if data["success"]:
            redirects = data.get("redirect_list", [])
            embed = Embed(title='Success',description=f'Here is the list of of redirects got from {url} \n||*(took {global_elapsed}ms globally, {data["api_elapsed"]}ms for the API to work, elapsed times including requested delays)*||', ).set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar)
            embed.add_field(name = 'Redirects', value = '\n'.join([f'` -> {i}`' for i in redirects]) if redirects else 'No redirects found.')
            await interaction.followup.send(ephemeral = silent, embed=embed)
        else:
            await interaction.followup.send(ephemeral = silent, embed=Embed(title='Error', description=f'Failed to get redirects from the URL, ask developers for more details... [API error?]').set_footer(text = f'Requested by {interaction.user.name}#{interaction.user.discriminator}', icon_url=interaction.user.avatar))   

tree.add_command(net())
"""
-------------------------------------------------
FEATURE COMMANDS (official)
-------------------------------------------------
/echo
/uptime
"""


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
    ilog("Bot is ready. Getting informations...", 'init', 'info')
    await client.change_presence(activity=Game('starting...'), status=Status.idle)
    await asyncio.sleep(2)
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
    if configurations.using_sentry:
        ilog('Initializing Sentry...', 'init', 'info')
        sentry_sdk.init(dsn=configurations.sentry_dsn, traces_sample_rate=1.0)
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
