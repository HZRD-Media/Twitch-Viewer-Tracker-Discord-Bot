# Twitch Viewer Tracker Discord Bot

   This bot tracks active chat users on a specified Twitch stream when a Twitch link is posted in a Discord channel. It periodically updates the Discord channel with the list of    active chat users and the current viewer count.

## Features
   - Automatically starts tracking a Twitch stream when a Twitch link is posted in the specified Discord channel.
   - Periodically posts the active chat users and viewer count in the Discord channel.
   - Stops tracking when the Twitch link is removed from the Discord channel.

## Setup and Installation

   To set up and run this bot, follow these steps:

### 1. Discord Bot Setup

   a. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
   b. Create a new application.
   c. Under "Bot", click "Add Bot" to create a bot user.
   d. Enable the following intents in the bot settings:
      - **Message Content Intent**
      - **Server Members Intent**
      - **Message Activity Intent**
   e. Copy the bot token, which you'll need to add to the `.env` file later.

### 2. Twitch Developer Application Setup

   a. Go to the [Twitch Developer Portal](https://dev.twitch.tv/console/apps/create).
   b. Create a new application.
   c. Set the OAuth redirect URL to `http://localhost`.
   d. Copy the **Client ID** and **Client Secret**, which you'll need to add to the `.env` file later.

### 3. Install Python and Set Up the Environment

   a. Install [Python 3.8+](https://www.python.org/downloads/).

### 4. Dependencies

   The bot requires the following Python libraries:

   - **discord.py**: A Python library for interacting with the Discord API. It allows the bot to connect to Discord, listen to messages, and perform actions like sending messages       or reacting to events.

   - **requests**: A simple and elegant HTTP library for Python. It’s used here to make API calls to Twitch to fetch information like stream data and viewer counts.

   - **twitchio**: A Python IRC client for Twitch, enabling interaction with Twitch chat. This allows the bot to monitor who is active in the Twitch chat during the stream.

   - **python-dotenv**: A library that loads environment variables from a `.env` file into Python. This helps keep sensitive information like API keys and tokens out of the main         codebase.

### 5. Set Up a Virtual Environment and Install Dependencies

   a. Set up a virtual environment by running the following command in your terminal:
   python -m venv venv

   b. Activate the virtual environment:
   Windows:  .\venv\Scripts\activate
   MacOS/Linux:  source venv/bin/activate

   With the virtual environment activated, install the necessary dependencies by running:
   pip install discord.py requests twitchio python-dotenv

### 6. Clone the Repository and Set Up Environment Variables

   a. Clone the repository to your local machine: (Or just download the files)
   git clone https://github.com/yourusername/twitch-viewer-tracker-bot.git
   cd twitch-viewer-tracker-bot

   b. Create a .env file in the project root directory and populate it with your Discord and Twitch credentials as follows:
      DISCORD_TOKEN=your_discord_bot_token
      TWITCH_CLIENT_ID=your_twitch_client_id
      TWITCH_CLIENT_SECRET=your_twitch_client_secret
      TWITCH_OAUTH_TOKEN=your_twitch_oauth_token
      TWITCH_NICKNAME=your_twitch_nickname

   Replace 'your_discord_bot_token', 'your_twitch_client_id', 'your_twitch_client_secret', 'your_twitch_oauth_token', and 'your_twitch_nickname' with your actual credentials.

   c. Update the TRACK_CHANNEL_ID variable in the ViewerBot.py script with the ID of the Discord channel where you want the bot to track Twitch links:
   TRACK_CHANNEL_ID = 1272604274068820019  # Replace with your Discord channel ID

### 7. Running the Bot
   a. Ensure your virtual environment is activated.

   b. Run the bot using the following command:
   python ViewerBot.py

   c. The bot will now listen for Twitch links in the specified Discord channel and begin tracking when a link is posted. It will automatically stop tracking when the link is    removed.
