import os
import uuid
from pyrogram import Client, filters
from pymongo import MongoClient
from uuid import uuid4
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import logging
import requests
from time import time, sleep
from keep_alive import keep_alive


load_dotenv()

keep_alive()

file_ids = {}


# Telegram bot credentials
api_id = int(os.environ.get('API_ID'))
api_hash = os.environ.get('API_HASH')
bot_token = os.environ.get('BOT_TOKEN')

urlshortx_api_token = os.environ.get('URL_SHORTENER_API_KEY')

# Time (in seconds) after which the token will expire (set it according to your requirement)
TOKEN_TIMEOUT = 86400  # 24 hour

# MongoDB credentials
mongo_url = os.environ.get('MONGODB_URI')
mongo_db_name = "file_data"
mongo_collection_name = "files"

# Initialize the MongoDB client and collection
mongo_client = MongoClient(mongo_url)
db = mongo_client[mongo_db_name]
collection = db[mongo_collection_name]
user_collection = db['users']  # Collection to store user tokens

# Channel ID from environment variable
channel_id = int(os.environ.get("CHANNEL_ID", "0"))
group_id = int(os.environ.get("GROUP_ID", "0"))
admin_id = int(os.environ.get("ADMIN_ID"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output logs to the console
    ]
)

# Create a logger for the bot
logger = logging.getLogger(__name__)

# Create a Pyrogram client
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# New function to delete messages after 60 seconds


def delete_message(chat_id, message):
    sleep(60)  # Wait for 60 seconds
    message.delete()  # Use the delete method to delete the message


# Handler for the /start command
@app.on_message(filters.command("start"))
def handle_start_command(client, message):
    try:
        user_id = message.from_user.id

        # Get the token from the URL if it's present
        if len(message.command) > 1:
            provided_token = message.command[1]

            if verify_token(user_id, provided_token):
                # The user is verified successfully
                app.send_message(
                    user_id, "You are verified successfully! Now you can use the search command in Group Now.")
            else:
                # The provided token doesn't match the stored token
                app.send_message(
                    user_id, "Verification failed. Please click on the correct link to verify your account.")
        else:
            # Generate or update the user's token and send the verification link
            token = generate_or_update_token(user_id)
            bot_username = app.get_me().username
            url_to_shorten = f'https://t.me/{bot_username}?start={token}'
            shortened_url = shorten_url(url_to_shorten)

            # Create an inline keyboard with the button for the shortened URL
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Verify your account", url=shortened_url)]])

            # Send the message with the verification button
            sent_message = app.send_message(
                message.chat.id, "Welcome! To 🗄File-Share-Boy👦, Please verify✅ your token:", reply_markup=keyboard)

            # Delete the sent message after 60 seconds
            delete_message(user_id, sent_message)

    except Exception as e:
        logger.error(f"Error while processing the start command: {e}")

# Handler for the search command


@app.on_message(filters.chat(group_id) & filters.command("search"))
def handle_search_command(client, message):
    user_id = message.from_user.id
    user_data = user_collection.find_one(
        {'user_id': user_id, 'status': 'verified'})

    if user_data:
        current_time = time()
        token_expiration_time = user_data.get('time', 0) + TOKEN_TIMEOUT

        if current_time > token_expiration_time:
            # Token is expired, send a message asking the user to renew their token
            app.send_message(
                message.chat.id, "Your token has expired. Please tap here 👉 /start to renew your token.")
        else:
            # Check if a search query was provided
            if len(message.command) < 2:
                app.send_message(
                    message.chat.id, "Please provide a search query along with the /search command.")
                return

            # User is verified and token is not expired, proceed with search
            query = message.command[1]  # Extract the search query
            search_results = collection.find(
                {'file_name': {'$regex': query, '$options': 'i'}})

            # Clear the file_ids dictionary before populating it with new search results
            file_ids.clear()

            # Create a list to hold the buttons for each result
            buttons = []

            # Prepare the buttons for each search result
            for result in search_results:
                # Generate a unique identifier for the file
                unique_id = str(uuid4())
                # Store the unique ID and corresponding file ID
                file_ids[unique_id] = result['file_id']

                buttons.append([InlineKeyboardButton(
                    result['file_name'], callback_data=unique_id)])

            if not buttons:
                # No search results found, send a message to inform the user and the admin
                app.send_message(
                    message.chat.id, "No results found. The admin will be notified soon.")
                app.send_message(
                    admin_id, f"User @{message.from_user.username} with ID {user_id} searched for: {query}")
            else:
                # Create an inline keyboard with the buttons for user selection
                keyboard = InlineKeyboardMarkup(buttons)

                # Send the message with the search results as clickable options
                sent_message = app.send_message(
                    user_id, "Select a file:", reply_markup=keyboard)
                logger.info(
                    f"{len(buttons)} search results sent as clickable options.")

                # Delete the sent message after 60 seconds
                delete_message(message.chat.id, sent_message)
    else:
        # User is not verified, send a message asking them to verify their account
        app.send_message(
            message.chat.id, "You need to verify your account first. Please tap here 👉 /start to verify your token.")

# Handler for button clicks


@app.on_callback_query()
def handle_callback(client, callback_query):
    unique_id = callback_query.data
    file_id = file_ids.get(unique_id)

    if file_id:
        # Handle the button click here (e.g., send the file corresponding to the file_id)
        app.send_document(callback_query.from_user.id, file_id,
                          caption="Here's the file you requested.")
    else:
        # In case something goes wrong or the file_id is not found
        app.answer_callback_query(callback_query.id, text="File not found.")

# Define a message handler to fetch files from the channel and store in MongoDB


@app.on_message(filters.chat(channel_id) & filters.document)
def fetch_files(client, message):
    try:
        if message.document:
            channel_id = message.chat.id
            # Store relevant information about the file in MongoDB
            file_data = {
                "file_id": message.document.file_id,
                "file_name": message.document.file_name,
                "channel_id": channel_id,
                "caption": message.caption,
            }
            collection.insert_one(file_data)
            print(f"  Database Updated🔄   ")
    except Exception as e:
        print(f"Error: {e}")

# Helper function to shorten the URL using URLShortx API


def shorten_url(url):
    try:
        api_url = f"https://urlshortx.com/api"
        params = {
            "api": urlshortx_api_token,
            "url": url,
            "format": "text"
        }
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            return response.text.strip()
        else:
            logger.error(
                f"URL shortening failed. Status code: {response.status_code}, Response: {response.text}")
            return url
    except Exception as e:
        logger.error(f"URL shortening failed: {e}")
        return url

# Generate a random token and save it to the database for a new user or update existing user's token


def generate_or_update_token(user_id):
    user_data = user_collection.find_one({'user_id': user_id})
    current_time = time()

    if user_data:
        # The user already exists, check if the token is expired
        token_expiration_time = user_data.get('time', 0) + TOKEN_TIMEOUT
        if current_time > token_expiration_time:
            # The token is expired, generate a new random token
            token = str(uuid.uuid4())  # Generate a new random token using uuid
            user_collection.update_one(
                {'user_id': user_id},
                {'$set': {'token': token, 'status': 'not verified', 'time': current_time}}
            )
        else:
            # The token is not expired, return the existing token
            token = user_data['token']
    else:
        # The user is new, generate a random token and add them to the database
        token = str(uuid.uuid4())  # Generate a random token using uuid
        user_collection.insert_one({
            'user_id': user_id,
            'token': token,
            'status': 'not verified',
            'time': current_time  # Save the current timestamp for token refresh
        })
    return token

# Verify the user's token and update status


def verify_token(user_id, provided_token):
    user_data = user_collection.find_one(
        {'user_id': user_id, 'token': provided_token})
    if user_data:
        # Update the user's status to 'verified'
        user_collection.update_one({'user_id': user_id}, {
                                   '$set': {'status': 'verified'}})
    return user_data is not None

# Handler for the /token_time command


@app.on_message(filters.command("token_time"))
def handle_token_time_command(client, message):
    try:
        user_id = message.from_user.id

        # Check if the user's token is present in the database
        user_data = user_collection.find_one({'user_id': user_id})
        if user_data and 'time' in user_data:
            current_time = time()
            token_expiration_time = user_data['time'] + TOKEN_TIMEOUT
            time_remaining = token_expiration_time - current_time

            if time_remaining <= 0:
                app.send_message(
                    user_id, "Your token has expired. Please tap here 👉 /start to renew your token.")
            else:
                minutes_remaining = int(time_remaining / 360)
                sent_message = app.send_message(
                    user_id, f"Your token will expire in {minutes_remaining} hours.")

                # Delete the sent message after 60 seconds
                delete_message(user_id, sent_message)
        else:
            app.send_message(
                user_id, "You are not verified. Please tap here 👉 /start to verify your token.")

    except Exception as e:
        logger.error(
            f"Error while processing the token_time_remaining command: {e}")


# Run the bot
if __name__ == "__main__":
    app.run()
