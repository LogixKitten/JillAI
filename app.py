from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector
import re
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)

app.secret_key = os.getenv('FLASK_SECRET_KEY')

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, first_name, last_name, username, email):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.email = email

# Database configuration
db_config = {
    'host': 'localhost',
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if username or email already exists
        cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
        user = cursor.fetchone()
        if user:
            flash("Username or email already exists.", 'error')
            return render_template('signup.html')

        # Hash the password and insert new user into the database
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute('INSERT INTO users (first_name, last_name, email, username, password) VALUES (%s, %s, %s, %s, %s)',
                       (first_name, last_name, email, username, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user_data = cursor.fetchone()

        cursor.close()
        conn.close()

        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            # Create an instance of the User class
            user = User(id=user_data['id'], first_name=user_data['first_name'], last_name=user_data['last_name'], username=user_data['username'], email=user_data['email'])
            login_user(user)  # Now this should work
            flash('Logged in successfully.', 'success')
            return redirect(url_for('chat_room'))
        else:
            flash('Invalid username or password.', 'error')
            return render_template('login.html')

    return render_template('login.html')

@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    
    cursor.close()
    connection.close()
    
    if user_data:
        return User(id=user_data['id'], first_name=user_data['first_name'], last_name=user_data['last_name'], username=user_data['username'], email=user_data['email'])
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

@app.route('/chat_room')
@login_required
def chat_room():
    return render_template('chat.html', user=current_user, first_name=current_user.first_name)

# Route to handle chat messages
@app.route('/send-message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_message = data.get('message')

    # Logic for AI persona's response
    ai_response = f"This is a response to: {user_message}"

    return jsonify({'response': ai_response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

