import asyncio
import discord
import os
import requests
from twitchio.ext import commands
from dotenv import load_dotenv

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
TRACK_CHANNEL_ID = ID HERE  # Replace with your Discord channel ID

# List of bot usernames to ignore
bot_usernames = [
    'moobot',
    'wizebot',
    'nightbot',
    'streamlabs',
    'streamelements',
    'pokemoncommunitygame',
    'soundalerts',
    'blerp'
]

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

    def __init__(self):
        super().__init__(token=TWITCH_OAUTH_TOKEN, prefix='!', initial_channels=[])
        self.active_users = set()  # Store active users who have sent messages

    async def event_ready(self):
        print(f'Logged in to Twitch as {self.nick}')

    async def event_message(self, message):
        # Only track if the message is from a user (not the bot itself)
        if message.echo:
            return

        # Add the user to the active users set
        self.active_users.add(message.author.name)
        print(f'Detected chat user: {message.author.name}')
        
        # Process commands if any are added in the future
        await self.handle_commands(message)

    async def get_active_users(self):
        return list(self.active_users)

    async def get_viewers(self, channel_name):
        url = f'https://tmi.twitch.tv/group/user/{channel_name}/chatters'
        try:
            response = requests.get(url)
            response.raise_for_status()  # Will raise an error for bad status codes
            data = response.json()
            viewers = data.get('chatters', {}).get('viewers', [])
            return viewers
        except Exception as err:
            print(f"An error occurred: {err}")
        return []

twitch_bot = TwitchBot()

# Function to post active viewers list in Discord
async def post_viewers_list(channel, twitch_username):
    while twitch_username in active_links:
        active_users = await twitch_bot.get_active_users()
        if active_users:
            # Filter out bot usernames
            filtered_users = [user for user in active_users if user.lower() not in bot_usernames]
            
            if filtered_users:
                viewers_list = ', '.join(filtered_users)
                await channel.send(f'Active users interacting in {twitch_username}: {viewers_list}')
                
                # Track user appearances
                for user in filtered_users:
                    if user in user_appearance_count:
                        user_appearance_count[user] += 1
                    else:
                        user_appearance_count[user] = 1
            else:
                await channel.send(f'No non-bot chat users detected for {twitch_username}.')

        else:
            await channel.send(f'No active chat users detected for {twitch_username}.')

        # Get the latest viewer count
        stream_data = get_twitch_stream_data(twitch_username)
        if stream_data:
            viewer_count = stream_data['viewer_count']
            await channel.send(f'{twitch_username} currently has {viewer_count} viewers.')
        else:
            await channel.send(f'{twitch_username} is not currently live.')

        # Reset active users set for the next interval
        twitch_bot.active_users.clear()

        # Wait for 20 minutes (1200 seconds)
        await asyncio.sleep(1200)

    print(f"Tracking for {twitch_username} has been stopped.")

# Function to start tracking a Twitch channel
async def start_tracking(message, twitch_username):
    # Check if we're already tracking this username to prevent duplicate tasks
    if twitch_username not in active_links:
        task = client.loop.create_task(post_viewers_list(message.channel, twitch_username))
        active_links[twitch_username] = task
        await message.channel.send(f'Started tracking {twitch_username}.')
        await twitch_bot.join_channels([twitch_username])

        # Provide an initial viewer count when tracking starts
        stream_data = get_twitch_stream_data(twitch_username)
        if stream_data:
            viewer_count = stream_data['viewer_count']
            await message.channel.send(f'{twitch_username} currently has {viewer_count} viewers.')

# Event: Bot is ready
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# Event: Message received
@client.event
@client.event
async def on_message(message):
    print(f"Message received in channel {message.channel.id}: {message.content}")
    
    if message.author == client.user:
        print("Ignoring the bot's own message.")
        return

    if message.channel.id == TRACK_CHANNEL_ID:
        print(f"Message is in the correct channel: {TRACK_CHANNEL_ID}")
        
        if 'twitch.tv' in message.content:
            print("Twitch link detected")
            
            # Extract the Twitch username from the link
            twitch_username = message.content.split('twitch.tv/')[-1].split()[0]
            print(f"Extracted Twitch username: {twitch_username}")

            if twitch_username not in active_links:
                print(f"Starting tracking for {twitch_username}")
                await start_tracking(message, twitch_username)
    else:
        print("Message received in a different channel.")

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
                    print(f"Stopped tracking {twitch_username} and left the channel.")
                
                # Find and display users who appeared in more than one list
                multi_appearance_users = [user for user, count in user_appearance_count.items() if count > 1]
                single_appearance_users = [user for user, count in user_appearance_count.items() if count == 1]

                if multi_appearance_users:
                    multi_user_list = ', '.join(multi_appearance_users)
                    await message.channel.send(f'Users who appeared in multiple lists: {multi_user_list}')
                else:
                    await message.channel.send('No users appeared in more than one list.')

                if single_appearance_users:
                    single_user_list = ', '.join(single_appearance_users)
                    await message.channel.send(f'Users who appeared in only one list: {single_user_list}')
                else:
                    await message.channel.send('No users appeared in only one list.')

                # Clear the user appearance count for future tracking
                user_appearance_count.clear()

# Function to get Twitch stream data
def get_twitch_stream_data(username):
    url = 'https://api.twitch.tv/helix/streams'
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {get_twitch_oauth_token()}'
    }
    params = {
        'user_login': username
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data['data']:
            return data['data'][0]
        else:
            return None
    except Exception as err:
        print(f"An error occurred: {err}")
    return None

# Function to get Twitch OAuth token
def get_twitch_oauth_token():
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as err:
        print(f"An error occurred: {err}")
    return None

# Run both the Discord and Twitch bots, plus the log clearing task
loop = asyncio.get_event_loop()
loop.create_task(client.start(DISCORD_TOKEN))
loop.create_task(twitch_bot.start())
loop.run_forever()
