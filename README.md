# utils-bot

utils-bot is a discord.py bot packaged with unique features.

## Deploying

### You can deploy the bot by yourself:
0. Clone the repo either download the .zip file or `git clone` it.

1. Install dependencies: `python3 -m pip install -r requirements.txt`

2. Setup varibles via `configs.py` file, or edit your machine's environment varibles.

3. Start the application: `sh main.sh`


## Usage

### The bot includes some useful commands: 

- For bot maintainers:
  + `/sync` :  sync the CommandTree with Discord. (use with caution, this could causes ratelimits | should only be used when there's a update)
  + `/info` :  get the current bot's infomation.
  + `/sys` 
    + `eval` : execute eval() scripts.
    + `guilds` : get the list of guilds that have this bot in.
    + `whitelist` :
      + `list` : get the list of whitelisted closed-beta users
      + `modify` : modify the whitelisted list...
  + `/locsys` [for `owner_guild_id` GUILD ONLY]
    + `maintenance` : set the current maintenance status for the bot. (disable the bot globally)
- For [repl.it](https://replit.com) users (with `IS_REPLIT` set to `YES`):
  + `/locsys` [for `owner_guild_id` GUILD ONLY]
    + `update` : update the version of this bot (update via git).
    + `version` : get the current version of the bot.
    + `restart` : execute os.system('kill 1')
- Beta commands (in development):
  + `/net` 
    + `screenshot` : screenshot a website via a headless browser.
    + `ip` : get the IP info of a IPv4 address.
    + `unshortener` : capture redirects (3** status codes) from a URL.
  + `/game` 
    + `wordle` : play [NYT wordle](https://www.nytimes.com/games/wordle) inside Discord.
  + `/tool` 
    + `totp` : generate a TOTP code from a secret key.

### CommandTree
```
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

/game
    |-- wordle
/net
    |-- screenshot
    |-- ip
    |-- unshortener

/tool
    |-- totp

/info
```

## Contributing

(not implemented)

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

## License

This project is protected by [MIT license](https://choosealicense.com/licenses/mit/), click hyperlink for more information.