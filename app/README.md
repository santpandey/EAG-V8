# Telegram Bot

## Setup Instructions

1. Create a Telegram Bot:
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Follow instructions to get your bot token

2. Install Dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Bot Token:
   - Open `config.py`
   - Replace `'YOUR_BOT_TOKEN_HERE'` with your actual bot token

4. Run the Bot:
```bash
python telegram_bot.py
```

## Bot Features
- `/start`: Greets the user
- `/help`: Shows available commands
- Echoes back any message sent to it

## Notes
- Ensure you have Python 3.7+ installed
- Keep your bot token secret!
