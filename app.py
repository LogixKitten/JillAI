from flask import Flask, render_template, request, redirect, url_for, session, flash
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # Password validation
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[A-Z])(?=.*[a-z])(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            flash("Password must be at least 8 characters long, contain a number, an uppercase letter, a lowercase letter, and a special character.", 'error')
            return redirect(url_for('register'))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if username or email already exists
        cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
        user = cursor.fetchone()
        if user:
            flash("Username or email already exists.", 'error')
            return redirect(url_for('register'))

        # Hash the password and insert new user into the database
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute('INSERT INTO users (first_name, last_name, email, username, password) VALUES (%s, %s, %s, %s, %s)',
                       (first_name, last_name, email, username, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['POST'])
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
                return redirect(url_for('home'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('home'))

    return redirect(url_for('home'))

@app.route('/chat_room')
def chat_room():
    if 'username' not in session:
        return redirect(url_for('login'))
    return "Chat Room Coming Soon!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

