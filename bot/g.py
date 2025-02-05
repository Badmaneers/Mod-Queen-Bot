import telebot
import os
import random
import json
import zlib
import base64
from dotenv import load_dotenv
import re
import time
from collections import defaultdict
import signal
import sys
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ✅ Move this up to define `bot` early
bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Ensure API keys are loaded correctly
if not BOT_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Error: BOT_TOKEN or OPENROUTER_API_KEY is not set.")

# ========== Memory Storage ========== #
MEMORY_FILE = "chat_memory.json"

def compress_data(data):
    """Compress JSON data using zlib & base64"""
    return base64.b64encode(zlib.compress(json.dumps(data).encode())).decode()

def decompress_data(data):
    """Decompress JSON data"""
    return json.loads(zlib.decompress(base64.b64decode(data)).decode())

def load_memory():
    """Load chat memory from a compressed file"""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as file:
                raw_data = file.read().strip()
                if raw_data:
                    return decompress_data(raw_data)
        except Exception as e:
            print(f"Error loading memory: {e}")
    return {}

def save_memory():
    """Save chat memory to a compressed file"""
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            file.write(compress_data(chat_memory))
    except Exception as e:
        print(f"Error saving memory: {e}")

chat_memory = load_memory()

# ========== Utility Functions ========== #
def load_from_file(filename, default_list=None):
    """Load data from a file or use default values"""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return [line.strip() for line in file.readlines()]
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return default_list or []

def load_prompt():
    """Load bot's personality prompt"""
    try:
        with open("bot/prompt.txt", "r", encoding="utf-8") as file:
            return file.read().strip()
    except Exception as e:
        print(f"Error loading prompt.txt: {e}")
        return "You are a sassy and engaging assistant."

# Load data files
roasts = load_from_file("bot/roasts.txt", ["You're like a software update: Nobody wants you, but we’re stuck with you."])
motivations = load_from_file("bot/motivations.txt", ["Keep shining like the star you are!"])
badwords = load_from_file("bot/badwords.txt", ["examplebadword1", "examplebadword2"])

# Spam tracking with reset
user_messages = defaultdict(int)
message_timestamps = defaultdict(float)

# Custom welcome message
@bot.message_handler(commands=['start'])
def welcome_message(message):
    bot.reply_to(message, f"Hey {message.from_user.first_name}! Your fave admin is here. Type /help to see what I can do!")

# Handle '/help' command
@bot.message_handler(commands=['help'])
def help_message(message):
    bot.reply_to(message, "Heyy, here's what I can do:\n"
                          "/roast - Want some spicy burns? 🔥\n"
                          "/motivate - Get a pep talk! 💪\n"
                          "/tea - Spill some gossip 😉\n"
                          "/rules - See the group rules 📜\n"
                          "/contribute - Help make me better! 🛠️\n"
                          "/mute to mute a user 🤐\n"
                          "/unmute to unmute a user 👄")

# Roast command
@bot.message_handler(commands=['roast'])
def roast_user(message):
    if roasts:
        bot.reply_to(message, f"{message.from_user.first_name}, {random.choice(roasts)}")
    else:
        bot.reply_to(message, "Oops, I'm out of roasts for now! Try again later.")

# Motivation command
@bot.message_handler(commands=['motivate'])
def motivate_user(message):
    if motivations:
        bot.reply_to(message, f"{message.from_user.first_name}, {random.choice(motivations)}")
    else:
        bot.reply_to(message, "Oops, I'm out of motivation for now! Try again later.")

# Spill the tea
@bot.message_handler(commands=['tea'])
def spill_tea(message):
    bot.reply_to(message, "Sis, you know I can’t gossip in public... but DM me 😉")

# Group rules
@bot.message_handler(commands=['rules'])
def group_rules(message):
    bot.reply_to(message, "Rule #1: No spam. Rule #2: Be respectful. Rule #3: Have fun, but don’t test me. 😉")

# Help contribute
@bot.message_handler(commands=['contribute'])
def contribute(message):
    bot.reply_to(message, 
                 "Want to contribute to my sass and moderation skills? 🛠️\n\n"
                 "Check out my GitHub repository: [https://github.com/Badmaneers/Mod-Queen-Bot]\n"
                 "Feel free to submit issues, suggest new features, or fork the repo and make pull requests!\n\n"
                 "Every contribution helps make me even better! 🚀")
                 

# ========== Admin Features ========== #
def is_admin(chat_id, user_id):
    """Check if the user is an admin in the group."""
    chat_admins = bot.get_chat_administrators(chat_id)
    return any(admin.user.id == user_id for admin in chat_admins)

@bot.message_handler(commands=['mute'])
def mute_user(message):
    """Admin can mute users."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "🚫 Only admins can use this command!")
        return

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        bot.restrict_chat_member(chat_id, target_id, can_send_messages=False)
        bot.reply_to(message, "🔇 User has been muted!")
    else:
        bot.reply_to(message, "Reply to a user to mute them.")

@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    """Admin can unmute users."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "🚫 Only admins can use this command!")
        return

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        bot.restrict_chat_member(chat_id, target_id, can_send_messages=True)
        bot.reply_to(message, "🔊 User has been unmuted!")
    else:
        bot.reply_to(message, "Reply to a user to unmute them.")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    """Admin can ban users from the group."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "🚫 Only admins can use this command!")
        return

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        bot.kick_chat_member(chat_id, target_id)
        bot.reply_to(message, "🚨 User has been banned!")
    else:
        bot.reply_to(message, "Reply to a user to ban them.")

@bot.message_handler(commands=['warn'])
def warn_user(message):
    """Warn users before banning."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "🚫 Only admins can use this command!")
        return

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        user_warnings[target_id] += 1

        if user_warnings[target_id] >= 3:
            bot.kick_chat_member(chat_id, target_id)
            bot.reply_to(message, "🚨 User has been banned after 3 warnings!")
        else:
            bot.reply_to(message, f"⚠️ Warning {user_warnings[target_id]}/3 - Stop violating the rules!")
    else:
        bot.reply_to(message, "Reply to a user to warn them.")
                 

system_prompt = load_prompt()

# ========== Anti-Spam System ========== #
user_messages = defaultdict(int)
message_timestamps = defaultdict(float)
user_warnings = defaultdict(int)

def warn_user(user_id, chat_id):
    """Warn user and kick if repeated violations"""
    user_warnings[user_id] += 1
    if user_warnings[user_id] >= 3:
        bot.kick_chat_member(chat_id, user_id)
        bot.send_message(chat_id, "User has been kicked for repeated violations.")
    else:
        bot.send_message(chat_id, f"⚠️ Warning {user_warnings[user_id]}/3 - Stop spamming!")

# ========== Moderation & AI Response ========== #
@bot.message_handler(func=lambda message: message.text and message.text.strip() != "")
def auto_moderate(message):
    user_id = str(message.from_user.id)  # Convert to string for JSON keys
    chat_id = message.chat.id

    # Anti-spam detection
    current_time = time.time()
    if current_time - message_timestamps[user_id] < 5:  # Messages too fast = spam
        warn_user(user_id, chat_id)
        bot.delete_message(chat_id, message.message_id)
        return

    message_timestamps[user_id] = current_time
    user_messages[user_id] += 1

    # Bad word filtering
    if any(badword in message.text.lower() for badword in badwords):
        bot.delete_message(chat_id, message.message_id)
        bot.send_message(chat_id, f"Uh-oh, watch your language {message.from_user.first_name}!")
        return

    # Store chat history
    if user_id not in chat_memory:
        chat_memory[user_id] = []

    chat_memory[user_id].append({"role": "user", "content": message.text})
    chat_memory[user_id] = chat_memory[user_id][-10:]  # Keep last 10 messages

    # If bot is mentioned, generate response
    if f"@{bot.get_me().username.lower()}" in message.text.lower() or \
       (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id):
        try:
            conversation = [{"role": "system", "content": system_prompt}] + chat_memory[user_id]

            # ✅ FIX: Correctly extract AI response
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-405b-instruct:free",
                messages=conversation
            )

            ai_reply = response.choices[0].message.content.strip() if response.choices else "Oops, I have no response. 😭"


            chat_memory[user_id].append({"role": "assistant", "content": ai_reply})
            save_memory()  # Save after AI response

            bot.reply_to(message, ai_reply)

        except Exception as e:
            bot.send_message(chat_id, "Oops, something went wrong.")
            print(f"AI error: {e}")

# ========== Start Bot ========== #
def handle_exit(signal_number, frame):
    print("Saving memory before exit...")
    save_memory()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

print("Sassy Telegram bot is running...")
bot.infinity_polling()
