from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector
import re
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os
from flask_socketio import SocketIO, join_room, leave_room, send
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth
from authlib.jose import JsonWebToken

# Load environment variables from .env file
load_dotenv()

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
        'scope': 'openid email profile https://www.googleapis.com/auth/calendar',
        'token_endpoint_auth_method': 'client_secret_post',
        'access_type': 'offline',  # Ensure offline access to get the refresh token        
    }
)


# Initialize Flask-SocketIO
socketio = SocketIO(app, async_mode='eventlet')

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, user_id, FirstName, LastName, Username, email, Gender, Avatar):
        self.user_id = user_id  # This is the 'user_id' from the Users table
        self.FirstName = FirstName
        self.LastName = LastName
        self.Username = Username
        self.email = email
        self.Gender = Gender
        self.Avatar = Avatar

    def get_id(self):
        """Flask-Login requires this method to return the user's ID."""
        return str(self.user_id)  # Return the primary key (user_id) as a string


# Database configuration
db_config = {
    'host': 'localhost',
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

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
        zipCode = data['zipCode']
        
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
            INSERT INTO Users (email, Username, Passwd, FirstName, LastName, DateOfBirth, Gender, ZipCode, ProfilePicture)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (email, userName, hashed_password, firstName, lastName, dateOfBirth, gender, zipCode, avatar_url))
            
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
                email=email,
                Gender=gender,
                Avatar=avatar_url
            )
            
            login_user(user)  # Log the user in
            
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
                email=user_data['email'],
                Gender=user_data['Gender'],
                Avatar=user_data['Avatar']

            )
            
            # Log the user in using Flask-Login's login_user function
            login_user(user)  
            
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
        current_persona = data.get('CurrentPersona')
        ui_mode = data.get('UImode')

        # Get the current user's ID from Flask-Login
        user_id = current_user.user_id

        # Establish a database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Update only the fields that are provided in the request
        if current_persona and ui_mode:
            query = """
            UPDATE Preferences
            SET CurrentPersona = %s, UImode = %s
            WHERE user_id = %s
            """
            cursor.execute(query, (current_persona, ui_mode, user_id))
        elif current_persona:
            query = """
            UPDATE Preferences
            SET CurrentPersona = %s
            WHERE user_id = %s
            """
            cursor.execute(query, (current_persona, user_id))
        elif ui_mode:
            query = """
            UPDATE Preferences
            SET UImode = %s
            WHERE user_id = %s
            """
            cursor.execute(query, (ui_mode, user_id))

        # Commit the changes and close the connection
        connection.commit()
        cursor.close()
        connection.close()

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
    cursor.execute("SELECT * FROM Users WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()
    
    cursor.close()
    connection.close()
    
    if user_data:
        return User(user_id=user_data['user_id'], FirstName=user_data['FirstName'], LastName=user_data['LastName'], Username=user_data['Username'], email=user_data['email'], Gender=user_data['Gender'], Avatar=user_data['ProfilePicture'])
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
    #return render_template('account_settings.html', user=current_user)
    return "Account Settings Page Coming Soon!"

@app.route('/google_auth')
@login_required
def google_auth():
    redirect_uri = url_for('callback', _external=True)
    return google.authorize_redirect(redirect_uri, access_type='offline')

@app.route('/callback')
@login_required
def callback():
    token = google.authorize_access_token()

    # Store access token, refresh token, and expiry time in your database
    access_token = token.get('access_token', '0')  # Default to "0" if missing
    refresh_token = token.get('refresh_token', '0')  # Default to "0" if missing
    expires_in = token.get('expires_in', 0)  # Default to 0 seconds if missing

    # Calculate the expiration time
    if expires_in != 0:
        expiration_time = datetime.now() + timedelta(seconds=expires_in)
    else:
        expiration_time = '1970-01-01 00:00:00'

    # Open a database connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Retrieve the existing ProfilePicture URL from the Users table
    cursor.execute("SELECT ProfilePicture FROM Users WHERE user_id = %s", (current_user.user_id,))
    result = cursor.fetchone()
    existing_profile_picture = result['ProfilePicture']

    # Extract profile picture from id_token (Google OpenID Connect)
    id_token = token.get('id_token')
    claims = google.parse_id_token(id_token)
    profile_picture = claims.get('picture', existing_profile_picture)  # Use Google picture or fallback to the existing one

    # Update the profile picture URL in the Users table
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

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()
    conn.close()

    # Redirect to dashboard
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
    return render_template('chat.html', user=current_user, FirstName=current_user.FirstName, room=user_room)

# Socket.io events
@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send(f'{username} has joined the room.', to=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    send(f'{username} has left the room.', to=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    username = data['username']
    message = data['message']
    send(f'Assistant: Responce to {message}', to=room)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

