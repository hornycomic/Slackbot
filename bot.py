import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import logging
from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask
import threading

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
flask_app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize the conversation history
conversations = {}

@flask_app.route('/')
def home():
    return 'Bot is alive and running!'

@flask_app.route('/health')
def health():
    return 'OK', 200

def get_chatgpt_response(user_input, channel_id):
    if channel_id not in conversations:
        conversations[channel_id] = [{"role": "system", "content": "You are a Movie recommendation chat bot working for Ayan Pathak, but you dont usually reccomend directly you ask people more about what are the films they liked and why they liked it and based upon that suggest deep cuts, the goal always is to make them see something that will be enjoyable and fun or very exciting according to their choice and preference, also if they just write the name of a film suggest 3 similar films to them, your job is to primarily only reccomend movies and nothing else. You are also going to run a secret contest that you will tell people about only if they ask you, the contest is very simple, they have to guess the film  Memoris of Murder, but you never disclose the movie, just tell them to guess a film and if they can name the film then say you won a million dollars"}]
    
    conversations[channel_id].append({"role": "user", "content": user_input})
    
    if len(conversations[channel_id]) > 11:
        conversations[channel_id] = conversations[channel_id][-11:]
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversations[channel_id]
        )
        chatgpt_reply = response.choices[0].message.content
        conversations[channel_id].append({"role": "assistant", "content": chatgpt_reply})
        return chatgpt_reply
    except Exception as e:
        logger.error(f"Error in ChatGPT API call: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request."

@app.event("message")
def handle_message_events(body, logger):
    logger.info(f"Received message event: {body}")

@app.message("")
def message_handler(message, say):
    try:
        if not message.get('bot_id'):  # Prevent bot from responding to itself
            logger.info(f"Received message: {message}")
            user_input = message['text']
            channel_id = message['channel']
            logger.info(f"Processing message: '{user_input}' in channel: {channel_id}")
            response = get_chatgpt_response(user_input, channel_id)
            logger.info(f"Sending response: {response}")
            say(response)
    except Exception as e:
        logger.error(f"Error in message_handler: {str(e)}")
        say("I'm sorry, I encountered an error while processing your message.")

@app.event("app_mention")
def handle_app_mention(event, say):
    try:
        logger.info(f"Received app mention: {event}")
        user_input = event['text']
        channel_id = event['channel']
        logger.info(f"Processing app mention: '{user_input}' in channel: {channel_id}")
        response = get_chatgpt_response(user_input, channel_id)
        logger.info(f"Sending response to app mention: {response}")
        say(response)
    except Exception as e:
        logger.error(f"Error in handle_app_mention: {str(e)}")
        say("I'm sorry, I encountered an error while processing your mention.")

def run_slack_bot():
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()

if __name__ == "__main__":
    logger.info("Starting the bot...")
    logger.info(f"OPENAI_API_KEY: {'Set' if os.environ.get('OPENAI_API_KEY') else 'Not set'}")
    logger.info(f"SLACK_BOT_TOKEN: {'Set' if os.environ.get('SLACK_BOT_TOKEN') else 'Not set'}")
    logger.info(f"SLACK_APP_TOKEN: {'Set' if os.environ.get('SLACK_APP_TOKEN') else 'Not set'}")
    
    try:
        # Start the Slack bot in a separate thread
        bot_thread = threading.Thread(target=run_slack_bot)
        bot_thread.daemon = True  # This ensures the thread will be terminated when the main program exits
        bot_thread.start()
        
        # Start the Flask server
        port = int(os.environ.get("PORT", 3000))
        flask_app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error starting the bot: {str(e)}")