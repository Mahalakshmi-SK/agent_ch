from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import os
from groq import Groq
from chatbot import Chatbot, CourseManager, ExplanationManager, QuizManager, ScoreManager
from login import UserManager

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": ["http://localhost:5000"],
        "supports_credentials": True
    }
})
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# Initialize components
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("API key is missing! Please set the GROQ_API_KEY environment variable.")

client = Groq(api_key=GROQ_API_KEY)
user_manager = UserManager()
chatbot = Chatbot(
    CourseManager(),
    ExplanationManager(client),
    QuizManager(client),
    ScoreManager()
)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"error": "Please login first"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", username=session['username'])

# Existing login route supporting JSON API login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Support both JSON and form POST
        if request.is_json:
            data = request.json
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        success, message = user_manager.authenticate_user(username, password)
        if success:
            session['username'] = username
            # If form POST, redirect to chatbot page
            if not request.is_json:
                return redirect(url_for('chatbot'))  # Make sure you have chatbot route
            return jsonify({"success": True, "message": message})
        else:
            if not request.is_json:
                return render_template('login.html', error=message)
            return jsonify({"success": False, "message": message}), 401

    return render_template("login.html")

# NOTE: Make sure you have a route named 'chatbot', example below:
@app.route('/chatbot')
def chatbot_page():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("chatbot.html", username=session['username'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        success, message = user_manager.register_user(username, password)
        if success:
            session['username'] = username
            return jsonify({"success": True, "message": message})
        return jsonify({"success": False, "message": message}), 400
    
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'username' in session:
        return jsonify({
            'authenticated': True,
            'username': session['username']
        })
    return jsonify({'authenticated': False})

@app.route('/api/courses', methods=['GET'])
def get_courses():
    return jsonify(chatbot.course_manager.get_courses())

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    session_id = data.get('session_id', session.get('username', 'default'))  # Use username as session ID
    message = data.get('message')
    
    response = chatbot.handle_message(session_id, message)

    # Proper access to SessionState attributes
    session_state = chatbot.sessions.get(session_id)
    if session_state and session_state.selected_course:
        course = session_state.selected_course
        score = session_state.score
        user_manager.update_user_session(session['username'], session_id, course, score)
    
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
