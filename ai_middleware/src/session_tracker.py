class SessionTracker:
    def __init__(self):
        self.session_states = {}  # session_id -> {operator_id, last_check}
    
    def track_operator_change(self, session_id: int, current_operator_id) -> bool:
        """Returns True if operator was removed (agent left)"""
        previous_state = self.session_states.get(session_id, {})
        previous_operator = previous_state.get('operator_id')
        
        # Update current state
        self.session_states[session_id] = {
            'operator_id': current_operator_id,
            'last_check': True
        }
        
        # Detect if operator was removed
        if previous_operator and not current_operator_id:
            return True  # Agent left
        
        return False