import json
import os
from datetime import datetime
import streamlit as st

SESSION_FILE = "sessions.json"

class SessionManager:
    def __init__(self):
        self.sessions = self.load_sessions()

    def load_sessions(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_sessions(self):
        with open(SESSION_FILE, "w") as f:
            json.dump(self.sessions, f, indent=4)

    def create_session(self, name, balance, pair, start_date, timeframe, description):
        session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.sessions[session_id] = {
            "id": session_id,
            "name": name,
            "balance": balance,
            "pair": pair,
            "start_date": start_date,
            "timeframe": timeframe,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        self.save_sessions()
        return self.sessions[session_id]

def initialize_session_state():
    if 'sm' not in st.session_state:
        st.session_state.sm = SessionManager()
    if 'active_session' not in st.session_state:
        st.session_state.active_session = None
    if 'replay_index' not in st.session_state:
        st.session_state.replay_index = 0
    if 'is_playing' not in st.session_state:
        st.session_state.is_playing = False
    if 'replay_speed' not in st.session_state:
        st.session_state.replay_speed = 1
    if 'trades' not in st.session_state:
        st.session_state.trades = []