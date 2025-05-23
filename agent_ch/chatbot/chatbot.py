from .models import SessionState
from .managers import CourseManager, QuizManager, ExplanationManager, ScoreManager

class Chatbot:
    def __init__(self, course_manager, explanation_manager, quiz_manager, score_manager):
        self.course_manager = course_manager
        self.explanation_manager = explanation_manager
        self.quiz_manager = quiz_manager
        self.score_manager = score_manager
        self.sessions = {}
    
    def get_or_create_session(self, session_id):
        """Get existing session or create a new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState()
        return self.sessions[session_id]
    
    def handle_message(self, session_id, message):
        """Main method to handle incoming messages"""
        state = self.get_or_create_session(session_id)

        if not message:
            return {"response": "Please type a message."}

        if state.conversation_state == "waiting_for_course":
            return self._handle_waiting_for_course(state, message)
        elif state.conversation_state == "awaiting_next_topic_permission":
            return self._handle_next_topic_permission(state, message)
        elif state.conversation_state == "awaiting_clarification":
            return self._handle_clarification(state, message)
        elif state.conversation_state == "awaiting_quiz_choice":
            return self._handle_quiz_choice(state, message)
        elif state.conversation_state == "quiz_question":
            return self._handle_quiz_answer(state, message, session_id)
        elif state.conversation_state == "awaiting_next_quiz_question":
            return self._handle_next_quiz_question(state)
        else:
            return self._handle_default_case(state, message)
    

    def _handle_waiting_for_course(self, state, message):
        matched = self.course_manager.get_matched_course(message)
        if matched:
            state.selected_course = matched
            state.topics = self.course_manager.get_topics(matched)
            state.current_topic_index = 0
            state.conversation_state = "explaining_topic"
            return {"response": self._explain_next_topic(state)}
        else:
            courses = "\n".join(f"- {course}" for course in self.course_manager.get_courses())
            return {"response": f"I couldn't find that course. Here are the available ones:\n\n{courses}"}
    
    def _handle_next_topic_permission(self, state, message):
        if message.lower() in ["yes", "y"]:
            state.current_topic_index += 1
            state.conversation_state = "explaining_topic"
            return {"response": self._explain_next_topic(state)}
        else:
            state.conversation_state = "awaiting_clarification"
            state.current_topic_for_clarification = state.topics[state.current_topic_index]
            return {"response": "Could you please specify which part you didn't understand?"}
    
    def _handle_clarification(self, state, message):
        response = self._simplify_current_topic(state, message)
        state.conversation_state = "awaiting_quiz_choice"
        return {"response": response}
    
    def _handle_quiz_choice(self, state, message):
        if message.lower() in ["yes", "y"]:
            state.conversation_state = "quiz_question"
            return {"response": self._start_quiz(state)}
        else:
            state.conversation_state = "awaiting_clarification"
            state.current_topic_for_clarification = state.topics[state.current_topic_index]
            return {"response": "Could you please specify which part you didn't understand?"}
    
    
    def _handle_quiz_answer(self, state, user_answer, session_id):
        index = state.current_quiz_index
        quiz_questions = state.quiz_questions

        if index >= len(quiz_questions):
            print(index, len(quiz_questions))
            return {"response": "✅ You've already completed the quiz. Type 'yes' to proceed to the next topic."}

        current_q = quiz_questions[index]
        correct = current_q["answer"]
        course = state.selected_course

        explanation = self.quiz_manager.get_answer_explanation(course, current_q['question'], correct)

        is_correct = user_answer.strip().upper() == correct.upper()
        if is_correct:
            state.score += 1

        result = "✅ Correct!" if is_correct else f"❌ Incorrect. The correct answer is {correct}."
        state.current_quiz_index += 1

        self.score_manager.update_score(session_id, course, state.score)

        if state.current_quiz_index < len(quiz_questions):
            state.conversation_state = "awaiting_next_quiz_question"
            return {
                "response": f"{result}\n{explanation}\n\nYour current score: {state.score}\nType 'next' for the next question."
            }
        else:
            # Quiz completed → Reset index
            state.current_quiz_index = 0
            state.conversation_state = "awaiting_next_topic_permission"
            return {
                "response": f"{result}\n{explanation}\n\n🎉 You've completed this quiz. Your final score: {state.score}\nWould you like to continue to the next topic? (yes/no)"
            }


    def _handle_next_quiz_question(self, state):
        return {"response": self._send_next_quiz_question(state)}
    
    def _handle_default_case(self, state, message):
        matched = self.course_manager.get_matched_course(message)
        if matched:
            state.selected_course = matched
            state.topics = self.course_manager.get_topics(matched)
            state.current_topic_index = 0
            state.conversation_state = "explaining_topic"
            return {"response": self._explain_next_topic(state)}
        return {"response": "I'm here to assist you! Please type a valid course name."}
    
   
    def _explain_next_topic(self, state):
        topics = state.topics
        index = state.current_topic_index

        if index >= len(topics):
            return "🎉 You've completed all the topics and quizzes. Well done!"

        topic = topics[index]
        course = state.selected_course

        # Get explanation
        if topic in state.explanations:
            explanation = state.explanations[topic]
        else:
            explanation = self.explanation_manager.fetch_topic_explanation(course, topic)
            state.explanations[topic] = explanation

        # Always generate new quiz questions
        quiz_questions = self.quiz_manager.generate_quiz_questions(course, topic)
        state.quiz_questions = quiz_questions  # Direct assignment of new questions
        state.current_quiz_index = 0
        state.conversation_state = "awaiting_quiz_choice"

        return f"**{topic}**:\n{explanation}\n\nWould you like to try a quiz on this topic? (yes/no)"
        
    def _start_quiz(self, state):
        if not state.quiz_questions:
            state.current_topic_index += 1
            state.conversation_state = "explaining_topic"
            return "No quiz questions available. Moving to the next topic..."
        return f"Let's start the quiz!\n\n{state.quiz_questions[0]['question']}"
    
    def _send_next_quiz_question(self, state):
        index = state.current_quiz_index
        quiz_questions = state.quiz_questions

        if index >= len(quiz_questions):
            state.conversation_state = "awaiting_next_topic_permission"
            return "🎉 You've completed the quiz. Would you like to proceed to the next topic? (yes/no)"

        state.conversation_state = "quiz_question"
        return quiz_questions[index]["question"]
    
  
    def _simplify_current_topic(self, state, clarification):
        topic = state.current_topic_for_clarification or state.topics[state.current_topic_index]
        course = state.selected_course
        
        # Get simplified explanation
        simple_explanation = self.explanation_manager.simplify_explanation(course, topic, clarification)
        
        # Generate new quiz questions after simplification
        new_quiz_questions = self.quiz_manager.generate_quiz_questions(course, topic)
        state.quiz_questions = new_quiz_questions  # Direct assignment of new questions
        state.current_quiz_index = 0
        state.conversation_state = "awaiting_quiz_choice"
        
        return f"Here's a simpler explanation:\n\n{simple_explanation}\n\nWould you like to try a quiz on this topic? (yes/no)"
