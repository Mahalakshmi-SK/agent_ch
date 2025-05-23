import json
import os
from groq import Groq

class CourseManager:
    def __init__(self, data_file="data.json"):
        self.course_data = self._load_course_data(data_file)
    
    def _load_course_data(self, data_file):
        """Load course data from JSON file"""
        with open(data_file, "r", encoding="utf-8") as file:
            return json.load(file)
    
    def get_courses(self):
        """Return list of available courses"""
        return list(self.course_data.keys())
    
    def get_matched_course(self, user_input):
        """Find a course that matches user input"""
        return next((course for course in self.course_data 
                    if course.lower() == user_input.lower()), None)
    
    def get_topics(self, course_name):
        """Return topics for a given course"""
        return list(self.course_data.get(course_name, {}).keys())

class QuizManager:
    def __init__(self, groq_client):
        self.client = groq_client
    
    def generate_quiz_questions(self, course, topic):
        """Generate quiz questions for a given topic"""
        try:
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are an expert in {course}. Generate two quiz questions related to {topic} along with the correct answer."
                    },
                    {
                        "role": "user", 
                        "content": f"Provide two multiple-choice quiz questions for the topic '{topic}' in {course}. Format them as:\nQ1: Question?\nA) Option1\nB) Option2\nC) Option3\nD) Option4\nCorrect Answer: X\n\nQ2: Question?\nA) Option1\nB) Option2\nC) Option3\nD) Option4\nCorrect Answer: Y"
                    }
                ],
                temperature=0.7
            )
            quiz_text = response.choices[0].message.content.strip()
            return self._parse_quiz_questions(quiz_text)
        except Exception as e:
            return [{"question": f"Error generating quiz: {str(e)}", "answer": ""}]
    
    def _parse_quiz_questions(self, quiz_text):
        """Parse the generated quiz text into structured questions"""
        quiz_list = []
        current_question = ""
        current_answer = ""

        lines = quiz_text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("Q"):
                if current_question and current_answer:
                    quiz_list.append({"question": current_question.strip(), "answer": current_answer.strip()})
                current_question = line
                current_answer = ""
            elif line.startswith(("A)", "B)", "C)", "D)")):
                current_question += "\n" + line
            elif "Correct Answer:" in line:
                current_answer = line.split("Correct Answer:")[-1].strip()

        if current_question and current_answer:
            quiz_list.append({"question": current_question.strip(), "answer": current_answer.strip()})

        return quiz_list
    
    def get_answer_explanation(self, course, question, correct_answer):
        """Get explanation for why an answer is correct"""
        try:
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are an expert in {course}. Provide a short, clear explanation for why the given answer is correct."
                    },
                    {
                        "role": "user", 
                        "content": f"Explain in 2 to 3 lines why this answer is correct:\n{question}\nAnswer: {correct_answer}"
                    }
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error getting explanation: {str(e)}"

class ExplanationManager:
    def __init__(self, groq_client):
        self.client = groq_client
        
    def fetch_topic_explanation(self, course, topic):
        """Fetch detailed explanation for a topic"""
        try:
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are an expert in {course}. Provide clear and detailed explanations about topics related to {course}."
                    },
                    {
                        "role": "user", 
                        "content": f"""Explain the topic '{topic}' in detail as it relates to {course}. 
Use **bold formatting** for topic headings and subheadings, and use line breaks to separate different sections clearly."""
                    }
                ],
                temperature=0.7
            )
            explanation = response.choices[0].message.content.strip()
            return explanation
        except Exception as e:
            return f"Error fetching explanation: {str(e)}"

    def simplify_explanation(self, course, topic, clarification):
        """Provide a simplified explanation of a topic based on user's confusion"""
        try:
            simplified_response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are an expert in {course}. Re-explain the specific part of '{topic}' that the student didn't understand: '{clarification}'. Keep it simple and clear."
                    },
                    {
                        "role": "user", 
                        "content": f"Please explain this part in simpler terms: {clarification}"
                    }
                ],
                temperature=0.7
            )
            return simplified_response.choices[0].message.content.strip()
        except Exception as e:
            return f"Sorry, I couldn't fetch a simplified explanation due to an error: {str(e)}"
    
class ScoreManager:
    def __init__(self, score_file="score.json"):
        self.score_file = score_file
    
    def update_score(self, session_id, course, score):
        """Update the score for a session and course"""
        try:
            if not os.path.exists(self.score_file):
                with open(self.score_file, 'w') as f:
                    json.dump({}, f)
            
            with open(self.score_file, 'r') as f:
                scores = json.load(f)
            
            if session_id not in scores:
                scores[session_id] = {}
            scores[session_id][course] = score
            
            with open(self.score_file, 'w') as f:
                json.dump(scores, f, indent=2)
        except Exception as e:
            print(f"Error updating score file: {e}")