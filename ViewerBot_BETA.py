import asyncio
import discord
import os
import aiohttp
import requests
import logging
import json
from twitchio.ext import commands
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = 'PATH TO YOUR ENV FILE'
load_dotenv(dotenv_path=env_path)

# Discord bot token and Twitch API credentials from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
TWITCH_OAUTH_TOKEN = os.getenv('TWITCH_OAUTH_TOKEN')
TWITCH_NICKNAME = os.getenv('TWITCH_NICKNAME')  # Your bot's or your Twitch username

# Specify the Discord channel ID to track
TRACK_CHANNEL_ID = ID_HERE  # Replace with your Discord channel ID

# URL to the bot_usernames.json file in your GitHub repository
bot_usernames_url = 'https://raw.githubusercontent.com/HZRD-Media/Twitch-Viewer-Tracker-Discord-Bot/ac4f1a960ad974afbe0f2b52f81f78395999024b/bot_usernames.json'

# Async function to download and load the JSON file
async def load_bot_usernames():
    async with aiohttp.ClientSession() as session:
        async with session.get(bot_usernames_url) as response:
            if response.status == 200:
                data = await response.json()
                return data['bot_usernames']
            else:
                logger.error(f"Failed to download bot_usernames.json, status code: {response.status}")
                return []

# Load the bot usernames
bot_usernames = asyncio.run(load_bot_usernames())

# Initialize the Discord client
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True  # To track deleted messages
client = discord.Client(intents=intents)

# Store active Twitch links and associated tasks
active_links = {}

# Store user appearances across multiple lists
user_appearance_count = {}

# Initialize TwitchIO Bot
class TwitchBot(commands.Bot):

    def __init__(self, logger):
        super().__init__(token=TWITCH_OAUTH_TOKEN, prefix='!', initial_channels=[])
        self.active_users = set()  # Store active users who have sent messages
        self.logger = logger  # Store the logger instance

    async def event_ready(self):
        self.logger.info(f'Logged in to Twitch as {self.nick}')

    async def event_message(self, message):
        # Only track if the message is from a user (not the bot itself)
        if message.echo:
            return

        # Add the user to the active users set
        self.active_users.add(message.author.name)
        self.logger.info(f'Detected chat user: {message.author.name}')
        
        # Process commands if any are added in the future
        await self.handle_commands(message)

    async def get_active_users(self):
        return list(self.active_users)

    async def get_viewers(self, channel_name):
        url = f'https://tmi.twitch.tv/group/user/{channel_name}/chatters'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()  # Will raise an error for bad status codes
                    data = await response.json()
                    viewers = data.get('chatters', {}).get('viewers', [])
                    return viewers
        except aiohttp.ClientError as err:
            self.logger.error(f"An error occurred while fetching viewers: {err}")
        return []

# Initialize the TwitchBot with the logger instance
twitch_bot = TwitchBot(logger=logger)

# Function to post active viewers list in Discord
async def post_viewers_list(channel, twitch_username):
    while twitch_username in active_links:
        active_users = await twitch_bot.get_active_users()
        if active_users:
            # Filter out bot usernames using the list from the JSON file
            filtered_users = [user for user in active_users if user.lower() not in bot_usernames]
            
            if filtered_users:
                viewers_list = ', '.join(filtered_users)
                await channel.send(f'Active users interacting in {twitch_username}: {viewers_list}')
                
                # Track user appearances
                for user in filtered_users:
                    user_appearance_count[user] = user_appearance_count.get(user, 0) + 1
            else:
                await channel.send(f'No non-bot chat users detected for {twitch_username}.')

        else:
            await channel.send(f'No active chat users detected for {twitch_username}.')

        # Get the latest viewer count
        stream_data = await get_twitch_stream_data(twitch_username)
        if stream_data:
            viewer_count = stream_data['viewer_count']
            await channel.send(f'{twitch_username} currently has {viewer_count} viewers.')
        else:
            await channel.send(f'{twitch_username} is not currently live.')

        # Reset active users set for the next interval
        twitch_bot.active_users.clear()

        # Wait for 20 minutes (1200 seconds)
        await asyncio.sleep(1200)

    logger.info(f"Tracking for {twitch_username} has been stopped.")

# Function to start tracking a Twitch channel
async def start_tracking(message, twitch_username):
    # Check if we're already tracking this username to prevent duplicate tasks
    if twitch_username not in active_links:
        task = asyncio.create_task(post_viewers_list(message.channel, twitch_username))
        active_links[twitch_username] = task
        await message.channel.send(f'Started tracking {twitch_username}.')
        await twitch_bot.join_channels([twitch_username])

# Event: Bot is ready
@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')

# Event: Message received
@client.event
async def on_message(message):
    logger.info(f"Message received in channel {message.channel.id}: {message.content}")
    
    if message.author == client.user:
        logger.info("Ignoring the bot's own message.")
        return

    if message.channel.id == TRACK_CHANNEL_ID:
        logger.info(f"Message is in the correct channel: {TRACK_CHANNEL_ID}")
        
        if 'twitch.tv' in message.content:
            logger.info("Twitch link detected")
            
            # Extract the Twitch username from the link
            twitch_username = message.content.split('twitch.tv/')[-1].split()[0]
            logger.info(f"Extracted Twitch username: {twitch_username}")

            if twitch_username not in active_links:
                logger.info(f"Starting tracking for {twitch_username}")
                await start_tracking(message, twitch_username)
    else:
        logger.info("Message received in a different channel.")

# Event: Message deleted
@client.event
async def on_message_delete(message):
    # Only consider deletions in the specified channel
    if message.channel.id == TRACK_CHANNEL_ID:
        if 'twitch.tv' in message.content:
            # Extract the Twitch username from the link
            twitch_username = message.content.split('twitch.tv/')[-1].split()[0]

            # Stop tracking if the link is removed
            if twitch_username in active_links:
                # Cancel the ongoing task
                task = active_links.pop(twitch_username, None)
                if task:
                    task.cancel()
                    await message.channel.send(f'Stopped tracking {twitch_username} as the link was removed.')

                    # Leave the Twitch channel
                    await twitch_bot.part_channels([twitch_username])
                    logger.info(f"Stopped tracking {twitch_username} and left the channel.")

                # Find and display users who appeared in more than one list
                multi_appearance_users = [user for user, count in user_appearance_count.items() if count > 1]
                single_appearance_users = [user for user, count in user_appearance_count.items() if count == 1]

                # Print the single appearance list first
                if single_appearance_users:
                    single_user_list = ', '.join(reversed(single_appearance_users))
                    await message.channel.send(f'Users who appeared in only one list: {single_user_list}')
                else:
                    await message.channel.send('No users appeared in only one list.')

                # Then print the multiple appearance list
                if multi_appearance_users:
                    multi_user_list = ', '.join(reversed(multi_appearance_users))
                    await message.channel.send(f'Users who appeared in multiple lists: {multi_user_list}')
                else:
                    await message.channel.send('No users appeared in more than one list.')

                # Clear the user appearance count for future tracking
                user_appearance_count.clear()

# Function to get Twitch stream data
async def get_twitch_stream_data(username):
    url = 'https://api.twitch.tv/helix/streams'
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {await get_twitch_oauth_token()}'
    }
    params = {
        'user_login': username
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                if data['data']:
                    return data['data'][0]
                else:
                    return None
    except aiohttp.ClientError as err:
        logger.error(f"An error occurred while fetching stream data: {err}")
    return None

# Function to get Twitch OAuth token
async def get_twitch_oauth_token():
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data['access_token']
    except aiohttp.ClientError as err:
        logger.error(f"An error occurred while obtaining OAuth token: {err}")
    return None

# Run both the Discord and Twitch bots
loop = asyncio.get_event_loop()
loop.create_task(client.start(DISCORD_TOKEN))
loop.create_task(twitch_bot.start())
loop.run_forever()
