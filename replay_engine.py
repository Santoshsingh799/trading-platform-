import streamlit as st
import time

class ReplayEngine:
    @staticmethod
    def play(max_index):
        st.session_state.is_playing = True
        
    @staticmethod
    def pause():
        st.session_state.is_playing = False
        
    @staticmethod
    def step_forward(max_index):
        st.session_state.is_playing = False
        if st.session_state.replay_index < max_index - 1:
            st.session_state.replay_index += 1
            
    @staticmethod
    def rewind():
        st.session_state.is_playing = False
        if st.session_state.replay_index > 0:
            st.session_state.replay_index -= 1

    @staticmethod
    def run_loop(max_index):
        if getattr(st.session_state, 'is_playing', False):
            if st.session_state.replay_index < max_index - 1:
                # Speeds: 1x = 1s, 2x = 0.5s, 4x = 0.25s, 8x = 0.125s
                speed_mapping = {"1x": 1.0, "2x": 0.5, "4x": 0.25, "8x": 0.125}
                delay = speed_mapping.get(st.session_state.get('replay_speed', '1x'), 1.0)
                
                time.sleep(delay)
                st.session_state.replay_index += 1
                st.rerun()
            else:
                st.session_state.is_playing = False
                st.rerun()