from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
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
        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            stored_password = user['password']
            if bcrypt.check_password_hash(stored_password, password.encode('utf-8')):
                session['username'] = username
                return redirect(url_for('chat_room'))
            else:
                flash('Invalid username or password.')
                return render_template('login.html')
        else:
            flash('Invalid username or password.')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/chat_room')
def chat_room():
    return render_template('chat.html')

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

