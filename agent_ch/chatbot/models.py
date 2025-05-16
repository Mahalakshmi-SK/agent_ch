class SessionState:
    def __init__(self):
        self.conversation_state = "waiting_for_course"
        self.selected_course = None
        self.topics = []
        self.current_topic_index = 0
        self.explanations = {}
        self.quiz_data = {}
        self.quiz_questions = []
        self.current_quiz_index = 0
        self.score = 0
        self.current_topic_for_clarification = None