import json
import os
import hashlib
from datetime import datetime  # Added for timestamp

class UserManager:
    def __init__(self, users_file="users.json"):
        self.users_file = users_file
        self.users = self._load_users()
    
    def _load_users(self):
        """Load users from JSON file"""
        if not os.path.exists(self.users_file):
            return {}
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_users(self):
        """Save users to JSON file"""
        with open(self.users_file, "w") as f:
            json.dump(self.users, f, indent=2)
    
    def register_user(self, username, password):
        """Register a new user"""
        if username in self.users:
            return False, "Username already exists"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        # Hash the password before storing
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        self.users[username] = {
            "password": hashed_password,
            "sessions": {}
        }
        self._save_users()
        return True, "Registration successful"
    
    def authenticate_user(self, username, password):
        # Reload users to get latest data
        self.users = self._load_users()
        
        user = self.users.get(username)
        if not user:
            return False, "User not found"
        
        stored_password_hash = user.get("password")
        if not stored_password_hash:
            return False, "Corrupted user data: no password found"
        
        # Hash the input password using SHA-256 (matches your storage)
        input_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        if input_hash == stored_password_hash:
            return True, "Login successful"
        else:
            return False, "Invalid password"

    def get_user_sessions(self, username):
        """Get user's session data"""
        return self.users.get(username, {}).get("sessions", {})
    
    def update_user_session(self, username, session_id, course, score):
        """Update user's session data with timestamp"""
        if username not in self.users:
            return
        
        if "sessions" not in self.users[username]:
            self.users[username]["sessions"] = {}

        if session_id not in self.users[username]["sessions"]:
            self.users[username]["sessions"][session_id] = {}
        
        # Update score for the course
        self.users[username]["sessions"][session_id][course] = score
        
        # Update the last updated timestamp
        self.users[username]["sessions"][session_id]["last_updated"] = str(datetime.now())
        
        self._save_users()
