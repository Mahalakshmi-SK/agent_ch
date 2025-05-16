from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from groq import Groq
from chatbot import Chatbot, CourseManager, ExplanationManager, QuizManager, ScoreManager

app = Flask(__name__)
CORS(app)

# Initialize components
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("API key is missing! Please set the GROQ_API_KEY environment variable.")

client = Groq(api_key=GROQ_API_KEY)
chatbot = Chatbot(
    CourseManager(),
    ExplanationManager(client),
    QuizManager(client),
    ScoreManager()
)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/api/courses', methods=['GET'])
def get_courses():
    return jsonify(chatbot.course_manager.get_courses())

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id', 'default')
    message = data.get('message')
    response = chatbot.handle_message(session_id, message)
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True, port=5000)


