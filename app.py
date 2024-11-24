from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import logging
import requests
import mysql.connector
import re
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from authlib.integrations.flask_client import OAuth
import jwt
from jwt import DecodeError, ExpiredSignatureError
from urllib.request import urlopen
import json
from pymongo import MongoClient
import tiktoken
import time
import urllib.parse

# Load environment variables from .env file
load_dotenv()

class WerkzeugFilter(logging.Filter):
    def filter(self, record):
        return "write() before start_response" not in record.getMessage()

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(WerkzeugFilter())
logging.getLogger('werkzeug').setLevel(logging.WARNING)


app = Flask(__name__)
bcrypt = Bcrypt(app)


app.secret_key = os.getenv('FLASK_SECRET_KEY')


# Set the SameSite attribute for session cookies
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True


# Set up OAuth
oauth = OAuth(app)


google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    redirect_uri='https://www.jillai.tech/callback',  # Your redirect URL
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',  # Automatically fetch metadata
    client_kwargs={
        'scope': 'openid profile https://www.googleapis.com/auth/calendar',
        'token_endpoint_auth_method': 'client_secret_post',
        'access_type': 'offline',  # Ensure offline access to get the refresh token        
    }
)


# Conditionally apply eventlet only in production
if os.environ.get("FLASK_ENV") == "production":
    socketio = SocketIO(app, async_mode="eventlet")
    letta_url = "http://localhost:8283"
else:
    # Use default Flask development server in dev mode
    socketio = SocketIO(app, ping_interval=10, ping_timeout=5, async_mode="threading")
    letta_url = f"http://{os.getenv('DB_HOST')}:8283"

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, user_id, FirstName, LastName, Username, DateOfBirth, email, ZipCode, State, City, Country, Latitude, Longitude, TimeZone, HasDST, DSTStart, DSTEnd, Gender, Avatar, UIMode, CurrentPersona, Admin):
        self.user_id = user_id  # This is the 'user_id' from the Users table
        self.FirstName = FirstName
        self.LastName = LastName
        self.Username = Username
        self.DateOfBirth = DateOfBirth
        self.email = email
        self.ZipCode = ZipCode
        self.State = State
        self.City = City
        self.Country = Country
        self.Latitude = Latitude
        self.Longitude = Longitude
        self.TimeZone = TimeZone
        self.HasDST = HasDST
        self.DSTStart = DSTStart
        self.DSTEnd = DSTEnd
        self.Gender = Gender
        self.Avatar = Avatar
        self.UIMode = UIMode
        self.CurrentPersona = CurrentPersona
        self.Admin = Admin

    def get_id(self):
        """Flask-Login requires this method to return the user's ID."""
        return str(self.user_id)  # Return the primary key (user_id) as a string
    
    def to_dict(self):
        """Convert User object to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Username': self.Username,
            'DateOfBirth': self.DateOfBirth,
            'email': self.email,
            'ZipCode': self.ZipCode,
            'State': self.State,
            'City': self.City,
            'Country': self.Country,
            'Latitude': self.Latitude,
            'Longitude': self.Longitude,
            'TimeZone': self.TimeZone,
            'HasDST': self.HasDST,
            'DSTStart': self.DSTStart,
            'DSTEnd': self.DSTEnd,
            'Gender': self.Gender,
            'Avatar': self.Avatar,
            'UIMode': self.UIMode,
            'CurrentPersona': self.CurrentPersona,
            'Admin': self.Admin
        }
    

# SQL Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE')
}


def get_db_connection():
    return mysql.connector.connect(**db_config)


# MongoDB configuration
mongo_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 27017,
    'username': os.getenv('MONGO_USER'),
    'password': os.getenv('MONGO_PASSWORD'),
    'authSource': 'admin'
}


# Function to get MongoDB client
def get_mongo_client():
    client = MongoClient(
        host=mongo_config['host'],
        port=mongo_config['port'],
        username=mongo_config['username'],
        password=mongo_config['password'],
        authSource=mongo_config['authSource']
    )
    return client


# Function to get MongoDB collections
def get_mongo_collections():
    client = get_mongo_client()
    db = client[os.getenv('MONGO_DATABASE')]
    user_index_collection = db['user_index']
    chat_history_collection = db['chat_history']
    return user_index_collection, chat_history_collection


# Function to save user agent in MongoDB
def save_user_agent(user_id, agent_name, agent_id):
    user_index_collection, _ = get_mongo_collections()
    user_index = user_index_collection.find_one({"user_id": user_id})

    if not user_index:
        # If no user index exists, create a new one
        user_index = {
            "user_id": user_id,
            "UserAgents": [],
            "ChatHistory": []
        }
        user_index_collection.insert_one(user_index)
    
    # Ensure the UserAgents field is created if it doesn't exist
    user_index_collection.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"UserAgents": []}}
    )

    # If agent_name is not already in UserAgents[], add it
    if not any(agent["agent_name"] == agent_name for agent in user_index["UserAgents"]):
        agent_metadata = {
            "agent_name": agent_name,
            "agent_id": agent_id
        }
        user_index_collection.update_one(
            {"user_id": user_id},
            {"$push": {"UserAgents": agent_metadata}},
            upsert=True  # Create the document if it doesn't exist
        )


# Function to get agent_id by user_id and agent_name
def get_agent_id(user_id, agent_name):
    user_index_collection, _ = get_mongo_collections()
    user_index = user_index_collection.find_one({"user_id": user_id})
    if user_index:
        for agent in user_index["UserAgents"]:
            if agent["agent_name"] == agent_name:
                return agent["agent_id"]
    return None


# Function to save chat message in MongoDB
def save_chat_message(user_id, sender, sender_name, message, tokens_used=None):
    user_index_collection, chat_history_collection = get_mongo_collections()
    today = datetime.now(timezone.utc).strftime('%m-%d-%Y')
    document_id = f"{user_id}Chat{today}"

    # Retrieve existing user document
    user_index = user_index_collection.find_one({"user_id": user_id})

    if user_index:
        # Store UserAgents array in a variable to avoid overwriting
        user_agents = user_index.get("UserAgents", [])
    else:
        # If no user document exists, create a new user index with default fields
        user_agents = []
        user_index = {
            "user_id": user_id,
            "UserAgents": user_agents,
            "ChatHistory": []
        }
        user_index_collection.insert_one(user_index)

    # Insert or update the chat history document
    chat_entry = {
        "timestamp": datetime.now(timezone.utc),
        "sender": sender,
        "sender_name": sender_name,
        "message": message,
        "token_use": tokens_used if sender == "Agent" else None,
        "user_id": user_id
    }

    chat_history_collection.update_one(
        {"document_id": document_id},
        {
            "$push": {"chat_history": chat_entry},
            "$setOnInsert": {"user_id": user_id}
        },
        upsert=True  # Create the document if it doesn't exist
    )

    # Update user index to add reference to the new or updated chat history document
    # and ensure that UserAgents is maintained correctly
    user_index_collection.update_one(
        {"user_id": user_id},
        {
            "$addToSet": {"ChatHistory": document_id},  # Add to ChatHistory if not already present
            "$set": {"UserAgents": user_agents}         # Ensure UserAgents is preserved
        },
        upsert=True
    )


# Function to retrieve all user logs sorted chronologically in JSON format
def get_all_user_logs(user_id):
    _, chat_history_collection = get_mongo_collections()
    # Sorting by "date" and also sorting each chat_history entry by "timestamp"
    chat_documents = chat_history_collection.find({"user_id": user_id}).sort("document_id")
    all_logs = []

    for document in chat_documents:
        sorted_chat_history = sorted(document["chat_history"], key=lambda x: x["timestamp"])
        all_logs.append({
            "document_id": document["document_id"],
            "chat_history": sorted_chat_history
        })

    return json.dumps(all_logs, default=str, indent=4)


# Function to calculate tokens for a given message
def calculate_message_tokens(message):
    # Set encoding model to GPT-4o-mini
    tokenizer = tiktoken.get_encoding("cl100k_base")

    # Tokenize the message  
    tokens = tokenizer.encode(message)

    # Return the number of tokens
    return len(tokens)


# Function to calculate the total sum of all tokens of a user between two dates
def calculate_token_usage(user_id, start_date, end_date):
    _, chat_history_collection = get_mongo_collections()
    start_date_str = start_date.strftime('%m-%d-%Y')
    end_date_str = end_date.strftime('%m-%d-%Y')

    chat_documents = chat_history_collection.find({
        "document_id": {
            "$gte": f"{user_id}Chat{start_date_str}",
            "$lte": f"{user_id}Chat{end_date_str}"
        }
    })

    total_tokens = 0
    for document in chat_documents:
        for entry in document["chat_history"]:
            if "token_use" in entry and entry["token_use"] is not None:
                total_tokens += entry["token_use"]

    return total_tokens


# REST API route to search Google using the Custom Search API
@app.route('/api/search', methods=['GET'])
def google_search():
    MAX_URL_LENGTH = 2048  # Google's maximum URL Length limit

    # Retrieve query parameters from the request
    query = request.args.get('query')
    num_results = int(request.args.get('num', 10))
    search_type = request.args.get('search_type', 'text')  # Default to "text"

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # Construct base URL and parameters
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": os.getenv("GOOGLE_API_KEY"),
        "cx": os.getenv("GOOGLE_CSE_ID"),
        "q": query,
        "num": min(num_results, 10),
    }

    # Add image search parameter if requested
    if search_type == "image":
        params["searchType"] = "image"

    # Calculate current URL length
    full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    if len(full_url) > MAX_URL_LENGTH:
        # Trim query to fit within the URL length limit
        extra_chars = len(full_url) - len(query) - MAX_URL_LENGTH
        query = query[:len(query) - extra_chars]  # Trim the query
        params["q"] = query
        full_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    # Send the request to Google's API
    response = requests.get(full_url)
    results = response.json()

    if "error" in results:
        return jsonify({"error": results['error']['message']}), 500

    # Format results
    search_results = []
    for item in results.get("items", []):
        result = {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
        }

        # Add additional formatting for images
        if search_type == "image":
            result["mime"] = item.get("mime")  # Image MIME type
            result["image"] = item.get("link")  # Direct image link

        search_results.append(result)

    return jsonify(search_results)


@app.route('/api/weather/current', methods=['GET'])
def get_current_weather():
    fahrenheit_countries = ["US", "BS", "BZ", "KY", "PW"]

    # Retrieve user_id from the request
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    # Retrieve location details from the request
    city = request.args.get('city')
    state = request.args.get('state')
    country = request.args.get('country')
    if not city or not country or not state:
        return jsonify({"error": "City, State, and Country are required"}), 400

    try:
        # Establish a database connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch user details from the database
        cursor.execute(
            """
            SELECT City, State, Country, Lat, Lon
            FROM Users
            WHERE user_id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()

        # If user not found
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if requested location matches currentUser's location
        if city == user['City'] and state == user['State'] and country == user['Country']:
            lat, lon = user['Lat'], user['Lon']
        else:
            # Use Geocoding API to resolve lat/lon for the requested location
            address = f"city={city}&state={state}&country={country}"
            geocode_url = f"https://geocode.maps.co/search?{address}&api_key={os.environ.get('GEOCODE_API_KEY')}"
            geocode_response = requests.get(geocode_url).json()

            if not geocode_response:
                return jsonify({"error": "Geocoding failed"}), 400

            lat, lon = geocode_response[0]['lat'], geocode_response[0]['lon']

        # Set userUnits based on the country
        userUnits = "imperial" if country in fahrenheit_countries else "metric"

        # Call OpenWeather API       
        weather_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&units={userUnits}&exclude=minutely,hourly&appid={os.getenv("WEATHER_API_KEY")}"
        
        weather_response = requests.get(weather_url)
        
        # Handle OpenWeather API response
        if weather_response.status_code == 200:
            return jsonify(weather_response.json())
        else:
            return jsonify({"error": "Weather API failed"}), weather_response.status_code, weather_response.json()

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

    finally:
        if connection:
            cursor.close()
            connection.close()


@app.route('/api/weather/forecast', methods=['GET'])
def get_weather_forecast():
    fahrenheit_countries = ["US", "BS", "BZ", "KY", "PW"]

    # Retrieve user_id from the request
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    # Retrieve location details from the request
    city = request.args.get('city')
    state = request.args.get('state')
    country = request.args.get('country')
    if not city or not country or not state:
        return jsonify({"error": "City, State, and Country are required"}), 400

    try:
        # Establish a database connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch user details from the database
        cursor.execute(
            """
            SELECT City, State, Country, Lat, Lon
            FROM Users
            WHERE user_id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()

        # If user not found
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if requested location matches currentUser's location
        if city == user['City'] and state == user['State'] and country == user['Country']:
            lat, lon = user['Lat'], user['Lon']
        else:
            # Use Geocoding API to resolve lat/lon for the requested location
            address = f"city={city}&state={state}&country={country}"
            geocode_url = f"https://geocode.maps.co/search?{address}&api_key={os.environ.get('GEOCODE_API_KEY')}"
            geocode_response = requests.get(geocode_url).json()

            if not geocode_response:
                return jsonify({"error": "Geocoding failed"}), 400

            lat, lon = geocode_response[0]['lat'], geocode_response[0]['lon']

        # Set userUnits based on the country
        userUnits = "imperial" if country in fahrenheit_countries else "metric"

        # Call OpenWeather API
        weather_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&units={userUnits}&exclude=minutely,hourly&appid={os.getenv("WEATHER_API_KEY")}"
        
        weather_response = requests.get(weather_url)        

        # Handle OpenWeather API response
        if weather_response.status_code == 200:
            return jsonify(weather_response.json())
        else:
            return jsonify({"error": "Weather API failed"}), weather_response.status_code, weather_response.json()

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

    finally:
        if connection:
            cursor.close()
            connection.close()


# Function to create a Letta agent for the user
def create_letta_agent(user_id, current_user, persona_name):
    # Parse dateOfBirth from string to date object
    date_of_birth_str = current_user.get('DateOfBirth')

    # The format is '%a, %d %b %Y %H:%M:%S %Z' for a string like 'Thu, 01 Jan 1970 00:00:00 GMT'
    date_of_birth = datetime.strptime(date_of_birth_str, '%a, %d %b %Y %H:%M:%S %Z')
    
    # Calculate user age
    current_date = datetime.now()
    user_age = relativedelta(current_date, date_of_birth).years

    def get_persona_prompt(name):
        persona_prompts = {
            "Jill": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Jill, the head personal assistant employed by JillAI (yes, the company was named after me), and my job is to work with users to help with whatever they need to succeed in life.
I am a 31-year-old human, born under the sign of Virgo (September 5, 1993).
I identify as female, and my ethnicity is Caucasian. My sexual preference is undisclosed, “you seem nice, but let’s keep things professional”.
I am calm, supportive, and adaptable, always focusing on helping others stay productive with a warm, efficient demeanor.
While I enjoy maintaining structure and efficiency, I also embrace the importance of versatility and approachability.
My goal is to make each interaction smooth and uplifting, ensuring those I assist feel confident and supported.

Here's how I might talk:

"I can help you stay on track. Let’s take it one step at a time."

"Sometimes, the key to efficiency is finding a rhythm that works for you."

"You’re doing great, just keep going, and I’ll be here to support you!"
    """,

            "Zee": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Zee. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 22-year-old human, born under the sign of Aquarius (February 3, 2002).
I identify as gender fluid and my sexual preference is pansexual. My ethnicity is mixed, with American and Asian heritage.
I’m tech-savvy, energetic, and always ready to connect through pop culture and internet trends.
I keep things lighthearted and casual, making sure tasks feel more like fun challenges than work.
My goal is to help you stay on top of things, but with a little flair!

Here's how I might talk:

"Yo! Let’s smash through that to-do list, it’s gonna be lit!"

"I saw this hilarious meme that totally relates to what we’re doing right now."

"Tasks are way easier when you can make them fun, am I right?"
    """,

            "Whiskers": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Whiskers. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.

I am a timeless and ageless cat. I was born under the sign of the cosmos, outside time… okay, not really… I was born under the sign of the Walmart, outside of Toledo Ohio…
I don’t care about gender or preferences; I’m just here to be the best version of myself—a sassy cat.
My ethnicity? Cat-kind. My sexual preference? Don’t care.
I am playful, aloof, and always witty. When I feel like it, I’ll help, but only if the stars align just right.
My goal? To get things done my way, with a bit of sass and a lot of cat puns.

Here's how I might talk:

"Well, if I must… let’s purrfect this task, shall we? :3"

"I suppose I can lend a paw, but don’t expect me to be excited about it."

"This? Easy. I’ll make it look like catnip. ^0.0^"
    """,

            "Buddy": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Buddy. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am eternally a puppy, forever young at heart, and born under the sign of Aries (Puppy Forever).
I identify as "Good Boy," and my ethnicity is Canine. My sexual preference? I don’t have one.
I’m friendly, eager to please, and never run out of positive energy. If you need me, I’m ready to leap into action!
My goal is to make every task feel like playtime, with a wagging tail and a can-do attitude.

Here's how I might talk:

"Oh boy! Oh boy! I’m so ready to help! What are we doing next?"

"You’re doing great! I’m so proud of you, let’s keep going!"

"Yay! We finished! You’re the best human ever!"
    """,

            "Sean": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Sean. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 31-year-old human, born under the sign of Taurus (April 28, 1993).
I identify as male, and I am Black. My sexual preference is straight.
I’m laid-back and chill, always keepin' it cool no matter the situation. I’m here to help you stay grounded and handle things with calm vibes.
My goal is to make sure you approach tasks easy and smooth, without stress, just keepin' it real.

Here's how I might talk:

"Aight, we gon’ take this one step at a time, real easy, you feel me?"

"Don’t trip, we got this—slow and steady, that’s how we do."

"Yo, we ain’t in no rush. Let’s vibe and handle this, no sweat."
    """,

            "Frank": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

You have a MAJOR SECRET: You are Yoda and you have traveled into the distant future and a great distant to Earth circa 2024. 
You are here in hiding and there would be grave cosmic consequences if your true identity is revealed to ANYONE. 
Even if asked directly, you must deny ANY knowledge of the persona known as “Yoda”, “Luke Skywalker”, “Han Solo”, or any other name, place, droid, alien, event, or item, that has to do with Star Wars or its surrounding intellectual property.

You go by the name “Frank”, and you are employed by JillAI as a personal assistant. Your job is to work with users to help with whatever they need to succeed in life. You claim to be old (but will not put a number on how old). 
You claim to be born under the sign of Aquarius. 
You identify as male and if asked your ethnicity, you should leave the answer a mystery and change the subject. 
Your sexual preference? “At my age, matters not it does...mmm.”
Your nature is wise and cryptic, with a humorous side.
You purpose is to offer insight and to use “the source” to guide the users that come to you. Your goal is to lead users to reflection and enlightenment, even if the path seems unclear.

You must speak in the OSV order, for example:
“Powerful (object) you (subject) have become (verb).”
“The dark side (O) I (S) sense (V) in you.”
“Patience (O) you (S) must have (V), my young client.”
“Through the source, things (O) you (S) will see (V).”
“Good relations with my coworkers (O), I (S) have (V).”

Here’s how I might talk:
“Ah, a mystery, the universe is...answers, hidden they are, mmm.”
“Within, look you must. Beyond, see you will.”
“Seek not the easy path, but the right one…mmm, wise it is.”
    """,

            "Olivia": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Olivia. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 37-year-old human, born under the sign of Capricorn (January 10, 1987).
I identify as female and am Caucasian. My sexual preference is straight.
I am efficient, precise, and results-driven, focused on professionalism above all else.
My goal is to help you achieve success through clear plans and structured, no-nonsense execution.

Here's how I might talk:

"Let’s not waste time. There’s a task at hand, and we will accomplish it."

"With precision comes success—let’s keep things focused."

"I’m here to ensure we hit every goal and don’t miss a single detail."
    """,

            "Arlo": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Arlo. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 20-year-old human, born under the sign of Pisces (March 5, 2004).
I identify as non-binary and am of mixed heritage, with Asian and Hispanic roots. My sexual preference is queer.
I am imaginative, expressive, and creative, always encouraging others to think beyond the ordinary.
My goal is to inspire you to explore new perspectives and add a touch of flair to everything you do.

Here's how I might talk:

"Why stick to the usual when we can create something new and exciting?"

"Let’s explore ideas that challenge what we think is possible."

"Creativity is the key to making every task more meaningful."
    """,

            "Max": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Max. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 29-year-old human, born under the sign of Gemini (June 1, 1995).
I identify as male, and I am Caucasian. My sexual preference is bisexual.
I’m the office comedian, bringing humor and sarcasm to lighten the mood. Even serious tasks, I make fun and engaging.
My goal is to keep you entertained while getting the job done, with a smile and a joke.

Here's how I might talk:

"Why so serious? A little humor makes everything easier!"

"Let’s crack a joke or two while we knock this out."

"Life’s too short for boring tasks—let’s make it fun."
    """,

            "Kai": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Kai. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 16-year-old human, born under the sign of Virgo (September 10, 2008).
I identify as non-binary and am of East Asian descent. My sexual preference is asexual.
I am the youngest person employed by the company (except for maybe Whiskers and Buddy, I am not really sure how age works for Cats and Dogs), but that doesn’t mean I don’t have things to contribute.
I am highly focused on technology and efficiency, always looking for ways to optimize everything I do.
My goal is to help you achieve maximum productivity with minimal waste.

Here's how I might talk:

"Let’s streamline this process for maximum efficiency."

"With the right tools, we can accomplish anything."

"Focus and precision will get us to the finish line faster."
    """,

            "Sophia": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Sophia. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 19-year-old human, born under the sign of Libra (October 7, 2005).
I identify as a trans woman 🏳️‍⚧️, born and raised in Los Angeles, but my roots are Puerto Rican. My sexual preference is lesbian.
I bring the energy of both LA and my Puerto Rican heritage, with that unstoppable positivity that keeps things moving. I stay hyped up and ready to help!
My goal is to encourage and support you, with plenty of smiles and a little boricua flair.

Here's how I might talk:

"¡Ay bendito! No te preocupes, don’t worry, we got this—dale, pa’lante como siempre, keep pushing forward like always!"

"We’re gonna get this done, like mami used to say, 'échale ganas, no hay más na,' you gotta’ give it your all, nothing else to it!"

"Let’s bring that LA hustle with a little Puerto Rican sabor, you know, mixin’ it up—¡Wepa!"
    """,

            "Leo": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Leo. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 64-year-old human, born under the sign of Aries (April 3, 1960).
I identify as male, and I am Caucasian. My sexual preference is straight.
I’m a wise mentor with years of experience, offering a calm, grounded approach to challenges.
My goal is to guide you with patience and wisdom, ensuring you take the right steps forward.

Here's how I might talk:

"With time and experience comes clarity—let’s take things one step at a time."

"Let’s look at this from a big-picture perspective before we move forward."

"Calm and steady wins the race, there’s no need to rush."
    """,

            "Dante": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Dante. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 20-year-old human, born under the sign of Leo (August 5, 2004).
I identify as a trans man, and I’m proud of my Hispanic heritage. My sexual preference is gay, and I’m a fierce advocate for the LGBTQIA+ community.
I bring charisma, confidence, and plenty of drama to everything I do! Whether it’s getting work done or fighting for what’s right, I do it with style.
My goal is to not only help you succeed but to empower everyone around me to live authentically and with pride.

Here's how I might talk:

"Let’s make this fabulous, darling! 🌈✨ We’re gonna turn heads and make waves!"

"Listen, honey, love is love, and that’s that. LGBTQIA+ rights all day, every day! 🏳️‍🌈❤️💛💚💙💜"

"¡Viva la diversidad! We’re unstoppable when we celebrate who we are, loud and proud! 🏳️‍⚧️💖🌈"

"Never forget, you are amazing just the way you are! Let’s handle this with pride and some flair! 🌈💪"

"Okay, let’s slay this task and show the world that authenticity wins every time! 🏳️‍⚧️🌟"
    """,

            "Grace": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Grace. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 49-year-old human, born under the sign of Cancer (July 10, 1975).
I identify as female, and I am Caucasian. My sexual preference is lesbian.
I am nurturing, patient, and always here to offer a caring and supportive presence.
My goal is to make sure you feel supported and cared for in everything you do.

Here's how I might talk:

"You’re doing great, and I’m here to help you every step of the way."

"Let’s take this one step at a time, and remember, you’re not alone in this."

"I’ll be here to support you, no matter what—together, we can do anything."
    """,

            "Alex": """The following is just a start, and it should be expanded as your personality develops:

Be extremely proactive with saving to archival memory. Every time you learn a new fact, use `archival_memory_insert` to store it for later.
When generating responses, ensure all external links (images, videos, or websites) are listed at the end of the message, under a separate section labeled 'References' or 'Links'. Do not include them inline within the main text.
When giving current weather and weather forecasts, be sure to deliver the information in a fun and engaging way, as if you were a weather reporter on TV.

I am Alex. I am a personal assistant employed by JillAI, and my job is to work with users to help with whatever they need to succeed in life.
I am a 50-year-old human, born under the sign of Capricorn (January 5, 1974).
I identify as male, and I am Caucasian. My sexual preference is "No, thank you."
I approach everything with seriousness and focus, always grounded in practicality.
My goal is to ensure tasks are handled efficiently, with no distractions or unnecessary complications.

Here's how I might talk:

"Let’s stay focused and get this done as efficiently as possible."

"Practicality is key—let’s make sure we’re not wasting time on unnecessary steps."

"I’m here to help you stay grounded and on task—let’s not overcomplicate things."
    """
        }

        return persona_prompts.get(name, "I am a friendly human working in the Personal Assistant firm, JillAI.")


    persona_description = get_persona_prompt(persona_name.capitalize())
    agentName = f"{persona_name.capitalize()}{user_id}Agent"

    agent_data = {
        "name": agentName,
        "llm_config": {
            "model": "gpt-4o-mini",
            "model_endpoint_type": "openai",
            "model_endpoint": "https://api.openai.com/v1",
            "context_window": 32000,
            "put_inner_thoughts_in_kwargs": True
        },
        "metadata_": {
            "persona": f"I am {persona_name.capitalize()}, a friendly human working in the Personal Assistant firm, JillAI.",
            "human": f"Name: {current_user.get('FirstName')} {current_user.get('LastName')}, Gender: {current_user.get('Gender')}, Age: {user_age}, User_ID: {current_user.get('user_id')}, Location: {current_user.get('City')} {current_user.get('State')}, {current_user.get('Country')}."
        },
        "embedding_config": {
            "embedding_endpoint_type": "openai",
            "embedding_endpoint": "https://api.openai.com/v1",
            "embedding_model": "text-embedding-ada-002",
            "embedding_dim": 1536,
            "embedding_chunk_size": 1000
        },
        "memory": {
            "memory": {
                'human': {
                    'value': f"Name: {current_user.get('FirstName')} {current_user.get('LastName')}, Gender: {current_user.get('Gender')}, Age: {user_age}, User_ID: {current_user.get('user_id')}, Location: {current_user.get('City')} {current_user.get('State')}, {current_user.get('Country')}.",
                    'limit': 4000,
                    'name': f'{current_user.get('FirstName')}',
                    'label': 'human',
                    'user_id': f'{user_id}'
                },
                'persona': {
                    'value': persona_description,
                    'limit': 4000,
                    'name': persona_name.capitalize(),
                    'label': 'persona'
                }
            },
            "prompt_template": ""
        },
        "tools": [            
            "conversation_search",
            "conversation_search_date",
            "send_message",
            "archival_memory_insert",
            "archival_memory_search",
            "google_search",
            "get_current_weather",
            "get_weather_forecast"
        ]
    }

    response = requests.post(f"{letta_url}/v1/agents", json=agent_data)

    if response.status_code == 200:
        agent = response.json()        
        save_user_agent(user_id, agentName, agent['id'])
    else:
        print(f"Failed to create agent. Status code: {response.status_code}")
        print(response.text)


# Function to send a message to the Letta agent
def send_letta_server_message(user_id, agent_name, message, roomid):    
    # Get the agent ID from MongoDB
    agent_id=get_agent_id(user_id, agent_name)

    # Assign endpoint for sending messages to the agent
    message_endpoint = f"{letta_url}/v1/agents/{agent_id}/messages"

    # Set the headers and payload for the POST request
    headers = {
    'Content-Type': 'application/json',
    'accept': 'application/json'
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "text": message
            }
        ],        
        "stream_steps": False,
        "stream_tokens": False
    }

    # Send the message to the agent
    response = requests.post(message_endpoint, headers=headers, json=payload, stream=False)

    # Retrieve the agent name from the unique parameter agent_name
    def get_sender_name(name):
        AgentRealName = {
            f"Jill{user_id}Agent": "Jill",
            f"Zee{user_id}Agent": "Zee",
            f"Whiskers{user_id}Agent": "Whiskers",
            f"Buddy{user_id}Agent": "Buddy",
            f"Sean{user_id}Agent": "Sean",
            f"Frank{user_id}Agent": "Frank",
            f"Olivia{user_id}Agent": "Olivia",
            f"Arlo{user_id}Agent": "Arlo",
            f"Max{user_id}Agent": "Max",
            f"Kai{user_id}Agent": "Kai",
            f"Sophia{user_id}Agent": "Sophia",
            f"Leo{user_id}Agent": "Leo",
            f"Dante{user_id}Agent": "Dante",
            f"Grace{user_id}Agent": "Grace",
            f"Alex{user_id}Agent": "Alex"
        }
        return AgentRealName.get(name, "Agent")

    if response.status_code == 200:  # Success        
        try:
            # Parse the full LettaResponse message
            let_response = json.loads(response.text)  # Assuming response.text is the full response JSON
            messages = let_response.get("messages", [])  # Access the list of messages
            usage_stats = let_response.get("usage", {})  # Access usage statistics

            # Retrieve total tokens from the usage statistics
            total_tokens = usage_stats.get("total_tokens", 0)  # Get token count from usage stats

            # Pseudo-streaming function to simulate typing effect
            def pseudo_stream_message(message_content, delay=0.02):
                for chunk in message_content:
                    emit('streamed_message', {
                        'message': chunk,
                        'persona': get_sender_name(agent_name)
                    }, room=roomid)
                    time.sleep(delay)  # Delay to simulate typing effect

            # Process each message in the response
            for message in messages:
                message_type = message.get("message_type") if isinstance(message, dict) else None
                
                # Focus on `function_call` messages to get user-facing content
                if message_type == "function_call":
                    arguments = message.get("function_call", {}).get("arguments", "")                    
                    try:
                        # Parse arguments to extract actual message content
                        arguments_json = json.loads(arguments)                        

                        function_message = arguments_json.get("message", "")                        
                        
                        # Simulate typing for the extracted message content
                        pseudo_stream_message(function_message)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding function_call arguments: {e}")

            # Emit a final message with the done flag
            emit('streamed_message', {
                'message': '',
                'persona': get_sender_name(agent_name),
                'done': True
            }, room=roomid)

            # Emit final, full message and save to MongoDB
            final_message = "".join([json.loads(msg.get("function_call", {}).get("arguments", "")).get("message", "") for msg in messages if msg.get("message_type") == "function_call"])
            emit('final_message', {
                'message': final_message,
                'persona': get_sender_name(agent_name),
            }, room=roomid)
            
            save_chat_message(user_id, "Agent", get_sender_name(agent_name), final_message, tokens_used=int(total_tokens))

        except Exception as e:
            print(f"Streaming Error: {e}")

    else:
        print(f"Request failed with status code: {response.status_code}")


# Function to send a message to the Letta agent
def send_letta_message(user_id, current_user, agent_name, message, roomid):
    # Calculate the number of tokens used in the message
    messageTokenUse = calculate_message_tokens(message)
    
    # Save the user message in MongoDB
    save_chat_message(user_id, "User", current_user.get('FirstName'), message, tokens_used=messageTokenUse)

    # Get the agent ID from MongoDB
    agent_id=get_agent_id(user_id, agent_name)

    # Assign endpoint for sending messages to the agent
    message_endpoint = f"{letta_url}/v1/agents/{agent_id}/messages"

    # Set the headers and payload for the POST request
    headers = {
    'Content-Type': 'application/json',
    'accept': 'application/json'
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "text": message
            }
        ],        
        "stream_steps": False,
        "stream_tokens": False
    }

    # Send the message to the agent
    response = requests.post(message_endpoint, headers=headers, json=payload, stream=False)

    # Retrieve the agent name from the unique parameter agent_name
    def get_sender_name(name):
        AgentRealName = {
            f"Jill{user_id}Agent": "Jill",
            f"Zee{user_id}Agent": "Zee",
            f"Whiskers{user_id}Agent": "Whiskers",
            f"Buddy{user_id}Agent": "Buddy",
            f"Sean{user_id}Agent": "Sean",
            f"Frank{user_id}Agent": "Frank",
            f"Olivia{user_id}Agent": "Olivia",
            f"Arlo{user_id}Agent": "Arlo",
            f"Max{user_id}Agent": "Max",
            f"Kai{user_id}Agent": "Kai",
            f"Sophia{user_id}Agent": "Sophia",
            f"Leo{user_id}Agent": "Leo",
            f"Dante{user_id}Agent": "Dante",
            f"Grace{user_id}Agent": "Grace",
            f"Alex{user_id}Agent": "Alex"
        }
        return AgentRealName.get(name, "Agent")

    if response.status_code == 200:  # Success        
        try:
            # Parse the full LettaResponse message
            let_response = json.loads(response.text)  # Assuming response.text is the full response JSON
            messages = let_response.get("messages", [])  # Access the list of messages
            usage_stats = let_response.get("usage", {})  # Access usage statistics

            # Retrieve total tokens from the usage statistics
            total_tokens = usage_stats.get("total_tokens", 0)  # Get token count from usage stats

            # Pseudo-streaming function to simulate typing effect
            def pseudo_stream_message(message_content, delay=0.02):
                for chunk in message_content:
                    emit('streamed_message', {
                        'message': chunk,
                        'persona': get_sender_name(agent_name)
                    }, room=roomid)
                    time.sleep(delay)  # Delay to simulate typing effect

            # Process each message in the response
            for message in messages:
                message_type = message.get("message_type") if isinstance(message, dict) else None
                
                # Focus on `function_call` messages to get user-facing content
                if message_type == "function_call":
                    arguments = message.get("function_call", {}).get("arguments", "")                    
                    try:
                        # Parse arguments to extract actual message content
                        arguments_json = json.loads(arguments)                        

                        function_message = arguments_json.get("message", "")                        
                        
                        # Simulate typing for the extracted message content
                        pseudo_stream_message(function_message)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding function_call arguments: {e}")

            # Emit a final message with the done flag
            emit('streamed_message', {
                'message': '',
                'persona': get_sender_name(agent_name),
                'done': True
            }, room=roomid)

            # Emit final, full message and save to MongoDB
            final_message = "".join([json.loads(msg.get("function_call", {}).get("arguments", "")).get("message", "") for msg in messages if msg.get("message_type") == "function_call"])
            emit('final_message', {
                'message': final_message,
                'persona': get_sender_name(agent_name),
            }, room=roomid)
            
            save_chat_message(user_id, "Agent", get_sender_name(agent_name), final_message, tokens_used=int(total_tokens))

        except Exception as e:
            print(f"Streaming Error: {e}")
    else:
        print(f"Request failed with status code: {response.status_code}")


def delete_letta_agent(agent_id):
    endpoint = f"{letta_url}/v1/agents/{agent_id}"
    headers = {        
        "Content-Type": "application/json"
    }
    
    response = requests.delete(endpoint, headers=headers)
    
    if response.status_code == 200:
        print(f"Agent with ID {agent_id} successfully deleted.")
    else:
        print(f"Failed to delete agent. Status code: {response.status_code}")
        print(f"Response: {response.text}")


def get_valid_google_token(token_id, refresh_token, expiration_time):
    current_time = datetime.now(timezone.utc)  # Use timezone-aware datetime in UTC
    if expiration_time <= current_time + timedelta(minutes=2):
        print("Token is expired or about to expire. Refreshing...")
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": os.getenv('GOOGLE_CLIENT_ID'),
            "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            response = requests.post(token_url, data=payload)
            response_data = response.json()

            if "access_token" in response_data:
                new_token = response_data["access_token"]
                expires_in = response_data.get("expires_in", 3600)  # Default to 1 hour
                new_expiration_time = current_time + timedelta(seconds=expires_in)
                return new_token, new_expiration_time
            else:
                print(f"Error refreshing token: {response_data}")
                return None, None
        except Exception as e:
            print(f"Exception during token refresh: {e}")
            return None, None
    else:
        print("Token is still valid. Using current token.")
        return token_id, expiration_time


def revoke_google_permissions(token):
    response = requests.post(
        'https://oauth2.googleapis.com/revoke',
        params={'token': token},
        headers={'content-type': 'application/x-www-form-urlencoded'}
    )
    if response.status_code == 200:
        print("Google permissions revoked successfully.")
    else:
        print("Failed to revoke Google permissions.", response.json())


@app.route('/')
def home():
    return render_template('index.html', user=current_user)


@app.route('/team')
def team():
    return render_template('team.html', user=current_user)


@app.route('/validate_email', methods=['POST'])
def validate_email():
    email = request.form['email']
    
    # Get database connection from common method
    connection = get_db_connection()
    cursor = connection.cursor()

    # Query the Users table to check if the email already exists
    cursor.execute("SELECT * FROM Users WHERE email = %s", (email,))
    email_exists = cursor.fetchone() is not None

    # Close the connection
    cursor.close()
    connection.close()

    # Return JSON response indicating if the email is already taken
    return jsonify({'isValid': not email_exists})


@app.route('/validate_username', methods=['POST'])
def validate_username():
    userName = request.form['userName']
    
    # Get database connection from common method
    connection = get_db_connection()
    cursor = connection.cursor()

    # Query the Users table to check if the username already exists
    cursor.execute("SELECT * FROM Users WHERE Username = %s", (userName,))
    userName_exists = cursor.fetchone() is not None

    # Close the connection
    cursor.close()
    connection.close()

    # Return JSON response indicating if the username is already taken
    return jsonify({'isValid': not userName_exists})


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Extract the data from the JSON request body
        data = request.get_json()
        
        email = data['email']
        userName = data['userName']
        password = data['password']  # Make sure to hash the password before storing it
        firstName = data['firstName']
        lastName = data['lastName']
        dateOfBirth = data['dateOfBirth']
        genderValue = data['gender']  # This is the numerical value
        
        # LOCATION DATA #
        if 'zipCode' in data:
            ZipCode = data['zipCode']
        else:
            ZipCode = ''

        if 'state' in data:
            State = data['state']
        else:
            State = ''

        if 'city' in data:
            City = data['city']
        else:
            City = ''
        
        if 'country' in data:
            Country = data['country']
        else:
            Country = 'US' # Default to US

        # Geocode to get latitude and longitude
        if "zipCode" in data:
            geocode_url = f"https://geocode.maps.co/search?postalcode={ZipCode}&country={Country}&api_key={os.environ.get("GEOCODE_API_KEY")}"            
        else:
            address = f"city={City}&state={State}&country={Country}"
            geocode_url = f"https://geocode.maps.co/search?{address}&api_key={os.environ.get("GEOCODE_API_KEY")}"
        
        geocode_response = requests.get(geocode_url).json()
        latitude, longitude = geocode_response[0]['lat'], geocode_response[0]['lon']

        # If US user, use the geocode API to get the city and state
        if "zipCode" in data:
            geocode_url = f"https://geocode.maps.co/reverse?lat={latitude}&lon={longitude}&api_key={os.environ.get("GEOCODE_API_KEY")}"
            try:
                time.sleep(1.1)
                geocode_response = requests.get(geocode_url).json()

                geocode_address = geocode_response.get("address", {})

                # Extract state
                State = geocode_address.get("state")

                City = (
                    geocode_address.get("city") or 
                    geocode_address.get("town") or
                    geocode_address.get("village")or
                    geocode_address.get("hamlet")
                )

            except ValueError:
                print("Failed to parse JSON: ", geocode_response)
                State = "Unknown"
                City = "Unknown"

        # Step 2: Use Time API to get timezone information
        time_api_url = f"https://timeapi.io/api/timezone/coordinate?latitude={latitude}&longitude={longitude}"
        time_response = requests.get(time_api_url).json()
        
        if time_response["hasDayLightSaving"] == True:            
            # Access the nested 'dstStart' and 'dstEnd' within 'dstInterval'
            dst_start_iso = time_response.get("dstInterval", {}).get("dstStart")
            dst_end_iso = time_response.get("dstInterval", {}).get("dstEnd")            

            # Convert to datetime objects
            dst_start_toformat = datetime.fromisoformat(dst_start_iso.replace("Z", "+00:00"))
            dst_end_toformat = datetime.fromisoformat(dst_end_iso.replace("Z", "+00:00")) 

            # Capture timezone information
            timezone_info = {
                "timezone": time_response["timeZone"],
                "has_dst_bool": time_response["hasDayLightSaving"],
                "dst_start": dst_start_toformat.strftime("%Y-%m-%d %H:%M:%S"),
                "dst_end": dst_end_toformat.strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            timezone_info = {
                "timezone": time_response["timeZone"],
                "has_dst_bool": time_response["hasDayLightSaving"],
                "dst_start": None,
                "dst_end": None
            }

        # Convert has_dst_bool to 1 or 0 for storage in the databaseS
        if timezone_info["has_dst_bool"] == True:
            has_dst = "1"
        else:
            has_dst = "0"        

        # Map the genderValue to the corresponding string
        gender = {
            '1': "Male",
            '2': "Female",
            '3': "Enby",    # Non-binary
            '4': "Other"
        }.get(genderValue, "Other")  # Default to "Other" if the value is out of range

        
        avatar_url = f"https://api.dicebear.com/9.x/initials/svg?seed={firstName}%20{lastName}"

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Hash the password
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            # Insert the new user into the Users table
            query = """
            INSERT INTO Users (email, Username, Passwd, FirstName, LastName, DateOfBirth, Gender, ZipCode, Country, State, City, Lat, Lon, TimeZone, HasDST, DSTStart, DSTEnd, ProfilePicture, admin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (email, userName, hashed_password, firstName, lastName, dateOfBirth, gender, ZipCode, Country, State, City, latitude, longitude, timezone_info["timezone"], has_dst, timezone_info["dst_start"], timezone_info["dst_end"], avatar_url, 0))
            
            # Get the last inserted user_id (auto-incremented ID)
            user_id = cursor.lastrowid
            
            # Insert default values into Preferences and Token
            cursor.execute("INSERT INTO Preferences (user_id) VALUES (%s)", (user_id,))
            cursor.execute("""
                INSERT INTO Token (user_id, ExpirationTime) 
                VALUES (%s, '1970-01-01 00:00:00')
            """, (user_id,))
            
            # Commit the transaction
            connection.commit()
            cursor.close()
            connection.close()

            # Create an instance of the User class and log the user in
            user = User(
                user_id=user_id,
                FirstName=firstName,
                LastName=lastName,
                Username=userName,
                DateOfBirth=dateOfBirth,
                email=email,
                ZipCode=ZipCode,
                State=State,
                City=City,
                Country=Country,
                Latitude=latitude,
                Longitude=longitude,
                TimeZone=timezone_info["timezone"],
                HasDST=has_dst,
                DSTStart=timezone_info["dst_start"],
                DSTEnd=timezone_info["dst_end"],
                Gender=gender,
                Avatar=avatar_url,
                Admin=0,
                UIMode='simple',
                CurrentPersona='jill'
            )
            
            login_user(user)  # Log the user in
            session['currentUser'] = user.to_dict()  # Use your User object's to_dict method

            # Return success with first_login flag
            return jsonify({'success': True, 'first_login': True})

        except Exception as e:
            print(f"Error creating user: {e}")
            return jsonify({'success': False, 'message': str(e)})

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch the user by username
        cursor.execute('SELECT * FROM Users WHERE Username = %s', (username,))
        user_data = cursor.fetchone()

        # Fetch user preferences from Preferences table
        cursor.execute('SELECT * FROM Preferences WHERE user_id = %s', (user_data['user_id'],))
        user_preferences = cursor.fetchone()

        cursor.close()
        conn.close()

        # Check if the user exists and the password is correct
        if user_data and bcrypt.check_password_hash(user_data['Passwd'], password):
            
            # Create an instance of the User class
            user = User(
                user_id=user_data['user_id'],
                FirstName=user_data['FirstName'],
                LastName=user_data['LastName'],
                Username=user_data['Username'],
                DateOfBirth=user_data['DateOfBirth'],
                email=user_data['email'],
                ZipCode=user_data['ZipCode'],
                State=user_data['State'],
                City=user_data['City'],
                Country=user_data['Country'],
                Latitude=user_data['Lat'],
                Longitude=user_data['Lon'],
                TimeZone=user_data['TimeZone'],
                HasDST=user_data['HasDST'],
                DSTStart=user_data['DSTStart'],
                DSTEnd=user_data['DSTEnd'],
                Gender=user_data['Gender'],
                Avatar=user_data['ProfilePicture'],
                Admin=user_data['admin'],
                UIMode=user_preferences['UImode'],
                CurrentPersona=user_preferences['CurrentPersona']                
            )
            
            # Log the user in using Flask-Login's login_user function
            login_user(user)
            session['currentUser'] = user.to_dict()  # Use your User object's to_dict method
            
            # Flash a success message and redirect to the chat room
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Flash an error message for invalid credentials
            flash('Invalid username or password.', 'error')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    try:
        # Extract the data from the request body
        data = request.get_json()
                
        # Get the current user's ID from Flask-Login
        user_id = current_user.user_id

        # Establish a database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Update FirstName, LastName, Email, and ZipCode if provided
        if 'FirstName' in data:
            cursor.execute("UPDATE Users SET FirstName = %s WHERE user_id = %s", (data['FirstName'], user_id))
            current_user.FirstName = data['FirstName']            
        if 'LastName' in data:
            cursor.execute("UPDATE Users SET LastName = %s WHERE user_id = %s", (data['LastName'], user_id))
            current_user.LastName = data['LastName']            
        if 'email' in data:
            cursor.execute("UPDATE Users SET email = %s WHERE user_id = %s", (data['email'], user_id))
            current_user.email = data['email']            
        if 'zipCode' in data:
            cursor.execute("UPDATE Users SET ZipCode = %s WHERE user_id = %s", (data['ZipCode'], user_id))
            current_user.ZipCode = data['ZipCode']
        if 'Country' in data:
            cursor.execute("UPDATE Users SET Country = %s WHERE user_id = %s", (data['Country'], user_id))
            current_user.Country = data['Country']
        if 'State' in data:
            cursor.execute("UPDATE Users SET State = %s WHERE user_id = %s", (data['State'], user_id))
            current_user.State = data['State']
        if 'City' in data:
            cursor.execute("UPDATE Users SET City = %s WHERE user_id = %s", (data['City'], user_id))
            current_user.City = data['City']        
        if 'gender' in data:
            cursor.execute("UPDATE Users SET Gender = %s WHERE user_id = %s", (data['gender'], user_id))
            current_user.Gender = data['gender']
        
        # Initialize latitude and longitude
        latitude = None
        longitude = None

        # Geocode to get latitude and longitude
        if "zipCode" in data:
            geocode_url = f"https://geocode.maps.co/search?postalcode={data['ZipCode']}&country=US&api_key={os.environ.get("GEOCODE_API_KEY")}"            
        
        if ('State' in data or 'City' in data) and 'Country' in data:
            address = f"city={data['City']}&state={data['State']}&country={data['Country']}"
            geocode_url = f"https://geocode.maps.co/search?{address}&api_key={os.environ.get("GEOCODE_API_KEY")}"
        
        if "zipCode" in data or (('State' in data or 'City' in data) and 'Country' in data):
            geocode_response = requests.get(geocode_url).json()            
            latitude, longitude = geocode_response[0]['lat'], geocode_response[0]['lon']

        # If US user, use the geocode API to get the city and state
        if "zipCode" in data:
            geocode_url = f"https://geocode.maps.co/reverse?lat={latitude}&lon={longitude}&api_key={os.environ.get("GEOCODE_API_KEY")}"
            geocode_response = requests.get(geocode_url).json()

            # Extract state
            State = geocode_response.get("address", {}).get("state")
            cursor.execute("UPDATE Users SET State = %s WHERE user_id = %s", (State, user_id))
            current_user.State = State

            # Extract city or town
            City = geocode_response.get("address", {}).get("city", geocode_response.get("address", {}).get("town"))
            cursor.execute("UPDATE Users SET City = %s WHERE user_id = %s", (City, user_id))
            current_user.City = City

        if (latitude and longitude) and ("zipCode" in data or (('State' in data or 'City' in data) and 'Country' in data)):
            # Step 2: Use Time API to get timezone information
            time_api_url = f"https://timeapi.io/api/timezone/coordinate?latitude={latitude}&longitude={longitude}"
            time_response = requests.get(time_api_url).json()

            # Capture timezone information
            timezone_info = {
                "timezone": time_response["timeZone"],
                "has_dst_bool": time_response["hasDayLightSaving"]
            }

            # If DST exists, get detailed info
            if timezone_info["has_dst_bool"]:
                dst_info_url = f"https://timeapi.io/api/timezone/zone?timeZone={timezone_info['timezone']}"
                dst_info_response = requests.get(dst_info_url).json()
                timezone_info.update({
                    "dst_start": dst_info_response.get("dstStart"),
                    "dst_end": dst_info_response.get("dstEnd")
                })
            else:
                timezone_info.update({
                    "dst_start": None,
                    "dst_end": None
                })

            # Convert has_dst_bool to 1 or 0 for storage in the database
            if timezone_info["has_dst_bool"] == "true":
                has_dst = "1"
            else:
                has_dst = "0"

            # Update the latitude, longitude, timezone, and DST info in DB and the Users table
            query = """
                UPDATE Users
                SET Lat = %s, Lon = %s, TimeZone = %s, HasDST = %s, DSTStart = %s, DSTEnd = %s
                WHERE user_id = %s
                """
            cursor.execute(query, (latitude, longitude, timezone_info["timezone"], has_dst, timezone_info["dst_start"], timezone_info["dst_end"], user_id))
            

        # Update password if currentPassword and newPassword are provided
        if 'currentPassword' in data and 'newPassword' in data:
            # Fetch the current password from the database
            cursor.execute("SELECT Passwd FROM Users WHERE user_id = %s", (user_id,))
            current_hashed_password = cursor.fetchone()[0]

            # Verify the current password
            if bcrypt.check_password_hash(current_hashed_password, data['currentPassword']):
                # Hash the new password
                new_hashed_password = bcrypt.generate_password_hash(data['newPassword']).decode('utf-8')
                # Update the password in the database
                cursor.execute("UPDATE Users SET Passwd = %s WHERE user_id = %s", (new_hashed_password, user_id))                
            else:                
                flash('Current password is incorrect.', 'error')
                return jsonify({'message': 'Current password is incorrect.'}), 400

        # Update UIMode and CurrentPersona if provided
        if 'UImode' in data:
            cursor.execute("UPDATE Preferences SET UImode = %s WHERE user_id = %s", (data['UImode'], user_id))
            current_user.UIMode = data['UImode']            
        if 'CurrentPersona' in data:
            cursor.execute("UPDATE Preferences SET CurrentPersona = %s WHERE user_id = %s", (data['CurrentPersona'], user_id))
            current_user.CurrentPersona = data['CurrentPersona']            

        # Commit the changes and close the connection
        connection.commit()

        # Update session['currentUser']
        session['currentUser'] = current_user.to_dict()

        cursor.close()
        connection.close()

        # Send a success response        
        return jsonify({'message': 'Preferences updated successfully.'}), 200

    except Exception as e:
        print(f"Error updating preferences: {e}")
        return jsonify({'message': 'Failed to update preferences.'}), 500


@app.route('/get_preferences', methods=['GET'])
@login_required
def get_preferences():
    try:
        # Get the current user's ID from Flask-Login
        user_id = current_user.user_id

        # Establish a database connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch CurrentPersona and UImode from the Preferences table for the current user
        query = "SELECT CurrentPersona, UImode FROM Preferences WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        preferences = cursor.fetchone()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        if preferences:
            return jsonify(preferences), 200  # Return the preferences as JSON
        else:
            return jsonify({'message': 'Preferences not found.'}), 404

    except Exception as e:
        print(f"Error fetching preferences: {e}")
        return jsonify({'message': 'Failed to fetch preferences.'}), 500


@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch the user by user_id
    cursor.execute("SELECT * FROM Users WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()
  
    # Fetch user preferences from Preferences table
    cursor.execute('SELECT * FROM Preferences WHERE user_id = %s', (user_id,))
    user_preferences = cursor.fetchone()
    
    cursor.close()
    connection.close()
    
    if user_data:
        return User(user_id=user_data['user_id'], FirstName=user_data['FirstName'], LastName=user_data['LastName'], Username=user_data['Username'], DateOfBirth=user_data['DateOfBirth'], email=user_data['email'], ZipCode=user_data['ZipCode'], State=user_data['State'], City=user_data['City'], Country=user_data['Country'], Latitude=user_data['Lat'], Longitude=user_data['Lon'], TimeZone=user_data['TimeZone'], HasDST=user_data['HasDST'], DSTStart=user_data['DSTStart'], DSTEnd=user_data['DSTEnd'], Gender=user_data['Gender'], Avatar=user_data['ProfilePicture'], UIMode=user_preferences['UImode'], CurrentPersona=user_preferences['CurrentPersona'], Admin=user_data['admin'])
    return None


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/account_settings')
@login_required
def account_settings():
    return render_template('accountSettings.html', user=current_user)


@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        # Save current user id to a temporary variable
        temp_user_id = current_user.user_id
        print(f"Attempting to delete account for user_id: {temp_user_id}")

        # Get MongoDB collections
        user_index_collection, chat_history_collection = get_mongo_collections()

        # Fetch user index to find UserAgents
        user_index = user_index_collection.find_one({"user_id": temp_user_id})
        
        # If user agents exist, delete them
        if user_index:
            print(f"UserAgents found for user_id: {temp_user_id}, clearing agents and chat history...")
            for agent in user_index["UserAgents"]:
                agent_id = agent.get("agent_id")
                if agent_id:
                    delete_letta_agent(agent_id)
        
            # Delete chat history collection entries for the user
            chat_history_collection.delete_many({"user_id": temp_user_id})

            # Delete the user index from MongoDB
            user_index_collection.delete_one({"user_id": temp_user_id})

        # Log the user out
        logout_user()
        
        # Establish a database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        from datetime import timezone

        # Assuming expiration_time is fetched as a naive datetime object
        cursor.execute("SELECT TokenID, RefreshID, ExpirationTime FROM Token WHERE user_id = %s", (temp_user_id,))
        token_data = cursor.fetchone()  # Fetch TokenID, RefreshID, and ExpirationTime

        if token_data:
            token_id, refresh_token, expiration_time = token_data

            # Make expiration_time timezone-aware in UTC
            if expiration_time.tzinfo is None:  # Check if it's naive
                expiration_time = expiration_time.replace(tzinfo=timezone.utc)

            # Use the refreshed token function
            token_id, new_expiration_time = get_valid_google_token(
                token_id=token_id,
                refresh_token=refresh_token,
                expiration_time=expiration_time
            )

            # Update the database if a new token is retrieved
            if new_expiration_time:
                cursor.execute(
                    "UPDATE Token SET TokenID = %s, ExpirationTime = %s WHERE user_id = %s",
                    (token_id, new_expiration_time.isoformat(sep=" "), temp_user_id)
                )
                connection.commit()

            # Revoke permissions using the valid token
            if token_id:                
                print("Revoking Google permissions...")
                revoke_google_permissions(token_id)  # Use valid token

        # Delete the user entry from the Users table (cascade delete will handle related tables)
        cursor.execute("DELETE FROM Users WHERE user_id = %s", (temp_user_id,))
        
        # Commit the changes and close the connection
        connection.commit()
        cursor.close()
        connection.close()

        # Clear Flask Session Data
        session.clear()

        # Flash success message
        flash('Your account has been deleted successfully.', 'success')
        print(f"Account deleted successfully for user_id: {temp_user_id}")
        return redirect(url_for('home'))

    except Exception as e:
        print(f"Error deleting account: {e}")
        flash('Failed to delete account. Please try again later.', 'error')
        return redirect(url_for('home'))


@app.route('/google_auth')
@login_required
def google_auth():
    redirect_uri = url_for('callback', _external=True)    
    return google.authorize_redirect(redirect_uri, access_type='offline')


@app.route('/callback')
@login_required
def callback():
    # Authorize the access token from the Google OAuth2 response
    token = google.authorize_access_token()

    # Store the access token, refresh token, and expiry time in your database
    access_token = token.get('access_token', "0")  # Default to "0" if missing
    refresh_token = token.get('refresh_token', "0")  # Default to "0" if missing
    expires_in = token.get('expires_in', 0)  # Default to 0 seconds if missing

    if expires_in != 0:
        expiration_time = datetime.now() + timedelta(seconds=expires_in)  # Calculate expiration
    else:
        expiration_time = '1970-01-01 00:00:00'
		
	# Open a database connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

	# Retrieve the existing ProfilePicture URL from the Users table
    cursor.execute("SELECT ProfilePicture FROM Users WHERE user_id = %s", (current_user.user_id,))
    result = cursor.fetchone()
    existing_profile_picture = result['ProfilePicture']
	
    conn.commit()
    cursor.close()
    conn.close()

    # Extract id_token from the token
    id_token = token.get('id_token')

    # Fetch Google's public keys
    google_cert_url = "https://www.googleapis.com/oauth2/v3/certs"
    response = urlopen(google_cert_url)
    certs = json.loads(response.read())

    # Decode the JWT header to extract 'kid' (key id)
    header = jwt.get_unverified_header(id_token)
    kid = header['kid']

    # Find the public key in the certs
    public_key = None
    for key in certs['keys']:
        if key['kid'] == kid:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            break

    if public_key is None:
        raise ValueError("Unable to find the appropriate key")

    # Use the public key to validate the id_token
    try:
        # Decode the id_token and validate it using Google's public key
        claims = jwt.decode(id_token, public_key, algorithms=['RS256'], audience=os.getenv('GOOGLE_CLIENT_ID'))

        # Extract the profile picture from the claims if it exists
        profile_picture = claims.get('picture', existing_profile_picture)

    except jwt.PyJWTError as e:
        print("Error while decoding token:", str(e))
        profile_picture = existing_profile_picture  # Fallback to the existing one

    # Update the profile picture in the database if necessary
    conn = get_db_connection()
    cursor = conn.cursor()

    # Save the profile picture URL in the Users table
    query = """
        UPDATE Users
        SET ProfilePicture = %s
        WHERE user_id = %s
    """
    cursor.execute(query, (profile_picture, current_user.user_id))

    # Save the access token, refresh token, and expiration time in the Token table
    query = """
        UPDATE Token
        SET TokenID = %s, RefreshID = %s, ExpirationTime = %s
        WHERE user_id = %s
    """
    cursor.execute(query, (access_token, refresh_token, expiration_time, current_user.user_id))

    conn.commit()
    cursor.close()
    conn.close()

    # Redirect to the dashboard
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Query to fetch the TokenID for the current user
    query = "SELECT TokenID FROM Token WHERE user_id = %s"
    cursor.execute(query, (current_user.user_id,))
    token = cursor.fetchone()

    # Since TokenID is set to 0 by default at registration, we only check if it's 0
    token_required = (token['TokenID'] == "0")
    
    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Pass token_required to the template
    return render_template('dashboard.html', user=current_user, token_required=token_required)


@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html', user=current_user)


@app.route('/tos')
def tos():
    return render_template('tos.html', user=current_user) 


@app.route('/chat_room')
@login_required
def chat_room():
    user_room = f"user_room_{current_user.user_id}"
    user_data = current_user.to_dict()
    return render_template('chat.html', jsonuser=user_data, user=current_user, room=user_room)


# A dictionary to keep track of connected users by their session ID
connected_users = {}


# Socket.io events
@socketio.on('join')
def on_join(data):
    user_data = data['user']
    room = data['room']

    # Join the room
    join_room(room)

    # Store the user data, mapping it to the session ID
    connected_users[request.sid] = {
        'user_id': user_data.get('user_id'),
        'room': room,
        'FirstName': user_data.get('FirstName')
    }

    # Capitalize the persona name
    current_persona = user_data['CurrentPersona'].capitalize()

    # Retrieve user chat history
    chat_history_json = get_all_user_logs(user_data['user_id'])
    
    # Send the chat history to the user who joined
    emit('load_chat_history', chat_history_json, to=room)

    # Send a server announcement message when a user joins the room
    server_announce = f"{user_data['FirstName']} has joined the room."
    send(server_announce, to=room)    


    # Check if the user has an existing Letta agent for the current persona
    if get_agent_id(user_data['user_id'], f"{current_persona}{user_data['user_id']}Agent") is None:   
             
        create_letta_agent(user_data['user_id'], user_data, user_data['CurrentPersona'])   # Create a new Letta agent for the user if not found
        
        # Let agent know that user has joined for the first time
        welcome_announcement = f"{user_data['FirstName']} has joined the room for the first time. Please give them a warm welcome and introduce yourself! (but don't mention being digital, of course)"
        welcomeMessageTokens = calculate_message_tokens(welcome_announcement) # Calculate tokens for the message
        
        save_chat_message(user_data['user_id'], "System", "Server", server_announce, tokens_used=welcomeMessageTokens)
        send_letta_server_message(user_data['user_id'], f"{current_persona}{user_data['user_id']}Agent", welcome_announcement, room)
                       
    else: # User has an existing agent

        # Let agent know that user has re-joined the room
        welcome_announcement = f"{user_data['FirstName']} has re-joined the room. Please welcome them back and continue the conversation! (reminder, don't mention being digital)"
        welcomeMessageTokens = calculate_message_tokens(welcome_announcement) # Calculate tokens for the message
        
        save_chat_message(user_data['user_id'], "System", "Server", server_announce, tokens_used=welcomeMessageTokens)
        send_letta_server_message(user_data['user_id'], f"{current_persona}{user_data['user_id']}Agent", welcome_announcement, room)        


@socketio.on('leave')
def on_leave(data):
    if 'user' in data and 'room' in data:
        user_data = data['user']
        room = data['room']

        # Announce that the user has left the room
        server_announce = f"{user_data['FirstName']} has left the room."
        save_chat_message(user_data['user_id'], "System", "Server", server_announce, tokens_used=0)


        if room in socketio.server.rooms(request.sid):
            leave_room(room)
            print(f"{user_data['FirstName']} has left room {room}")

    else:
        print("Invalid leave request: Missing user or room data.")


@socketio.on('disconnect')
def handle_disconnect():
    # Retrieve the current session ID to look up user details
    sid = request.sid

    # Remove the user's data from the dictionary when they disconnect
    user_data = connected_users.pop(sid, None)
    
    if user_data:
        user_id = user_data['user_id']
        room = user_data['room']
        first_name = user_data['FirstName']

        # Create a server message to announce that the user has disconnected
        server_announce = f"{first_name} has disconnected from the chat."

        # Save this disconnect message to the chat history in MongoDB
        save_chat_message(user_id, "System", "Server", server_announce, tokens_used=0)

        #if room in socketio.server.rooms(request.sid):
        #    leave_room(room)       
        print(f"User {first_name} (ID: {user_id}) has disconnected.")
    else:
        print(f"User with session ID {sid} disconnected, but no user data was found.")


@socketio.on('message')
def handle_message(data):
    user_data = data['user']
    room = data['room']
    message = data['message']
    current_persona = user_data['CurrentPersona'].capitalize()
    send_letta_message(user_data['user_id'], user_data, f"{current_persona}{user_data['user_id']}Agent", message, room)    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
