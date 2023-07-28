from pymongo import MongoClient
from uuid import uuid4
import requests
from time import time, sleep
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters, Client, User

# Telegram bot credentials
api_id = int(os.environ.get('API_ID'))
api_hash = os.environ.get('API_HASH')
bot_token = os.environ.get('BOT_TOKEN')

urlshortx_api_token = os.environ.get('URL_SHORTENER_API_KEY')

# Time (in seconds) after which the token will expire (set it according to your requirement)
TOKEN_TIMEOUT = 86400  # 24 hours

# MongoDB credentials
mongo_url = os.environ.get('MONGODB_URI')
mongo_db_name = "file_data"
mongo_collection_name = "files"

# Initialize the MongoDB client and collection
mongo_client = MongoClient(mongo_url)
db = mongo_client[mongo_db_name]
collection = db[mongo_collection_name]
user_collection = db['users']  # Collection to store user tokens

# Admin ID from environment variable
admin_id = int(os.environ.get("ADMIN_ID"))

# Define the function to check if a user is the admin
def is_admin(user: User, admin_id):
    return user.id == admin_id

# Function to delete specific file data from the database
def delete_file_data(file_id):
    try:
        # Find and delete the file data from the collection based on the file_id
        collection.delete_one({'file_id': file_id})
        print(f"File data with file_id: {file_id} deleted from the database.")
    except Exception as e:
        print(f"Error while deleting file data: {e}")

# Function to delete a user from the database
def delete_user_data(user_id):
    try:
        # Find and delete the user data from the user_collection based on the user_id
        user_collection.delete_one({'user_id': user_id})
        print(f"User data with user_id: {user_id} deleted from the database.")
    except Exception as e:
        print(f"Error while deleting user data: {e}")
