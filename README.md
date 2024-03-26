<h1 align="center">
  <br>
  <a href="https://github.com/kurzgesagt-in-a-nutshell/"><img src=".github/images/birdbot.png" height="150" alt="Bird Bot"></a>
  <br>
    Bird Bot
  <br>
</h1>

<h4 align="center">The almighty and powerful Bird Bot helps run the Kurzgesagt discord server like a well oiled machine</h4>

# ➡️ Getting Started

## ⚙️ Prerequisites

- [Python 3.11 or higher](https://www.python.org/)
- [MongoDB](https://www.mongodb.com/)

## 📦 Installation 

Follow these steps to get the bot up and running in your system
- Run the following commands 

```
# clone the repository
git clone https://github.com/kurzgesagt-in-a-nutshell/kurzgesagtbot

# install virtualenv if you haven't already (Or use another Virtual Environment manager)
pip install virtualenv

# Setup a venv
python3.11 -m venv birdbot
source birdbot/bin/activate

# install the dependencies
pip install -r requirements.txt
```

- Navigate to /app/utils/config.py and change the values of the variables according to your requirements

- Create a file named `.env` and paste the following lines in it. Change the values of the variables according to your requirements
```
MAIN_BOT_TOKEN='INSERT_MAIN_BOT_TOKEN'
BETA_BOT_TOKEN='INSERT_BETA_BOT_TOKEN'
ALPHA_BOT_TOKEN='INSERT_ALPHA_BOT_TOKEN'
DB_KEY='INSERT_MONGODB_DATABASE_CONNECTION_URL'
```

- Run the bot with, use the `-a` or `-b` option to run testing versions of the bot
```
python3 startbot.py [-b] [-a]
```

If you need additional help you may join our [Discord Server](https://discord.gg/kurzgesagt)

# 🤲 Contributing

Please read our contributor guidelines [here](https://github.com/kurzgesagt-in-a-nutshell/.github/blob/main/CONTRIBUTING.md) before contributing

Before submitting a pull request please ensure you conform to our [PyRight](https://github.com/microsoft/pyright) standards and be sure to use [ISort](https://pycqa.github.io/isort/#using-isort) import sorter and the [Black](https://github.com/psf/black) code formatter.
Run these commands (preferably in the given order) and make sure they do not throw any errors:
```
pyright .
isort .
black .
```
