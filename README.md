*current version: v0.10*
# utils-bot

utils-bot is a discord.py bot packaged with unique features.

## Changelogs on v0.10:
- MongoDB implementation

## Deploying

### You can deploy the bot by yourself:

0. Clone the repo: either download the .zip file or `git clone` it.

- It is recommended to build this app with [Nixpacks](https://nixpacks.com/docs/install), which is the way I designed this app to be built with. If you use Nixpacks, you can skip step 1 and 3, 4. To build and run, use this:

```py
nixpacks build . --name utilsbot
docker run -it --env-file ./.env utilsbot
```

1. Install dependencies: `python3 -m pip install -r requirements.txt`

2. Prepare required APIs, including screenshot, database, ... (you can find in gh/utils-bot repos), including:
- Deshortener API [ [Link](https://github.com/utils-bot/deshortener-api) ]

- Screenshot API (currently in development) [ [Private version](https://github.com/utils-bot/js-screenshot-api) | [Public version](https://github.com/utils-bot/screenshot-api) ]

3. Setup variables via `configs.py` file, or edit your machine's environment variables, based on .env.example file.

4. Start the application: `python3 main.py`


## Contributing

(not implemented)

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

## License

This project is protected by [MIT license](https://choosealicense.com/licenses/mit/)..