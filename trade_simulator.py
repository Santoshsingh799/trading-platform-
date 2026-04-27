import streamlit as st
from datetime import datetime

class TradeSimulator:
    @staticmethod
    def open_position(direction, price, date, sl=0, tp=0, risk_reward=0):
        trade = {
            "id": f"TRD-{int(datetime.now().timestamp())}",
            "direction": direction,
            "entry_price": price,
            "entry_date": date,
            "exit_price": None,
            "exit_date": None,
            "sl": sl,
            "tp": tp,
            "rr_ratio": risk_reward,
            "pnl": 0.0,
            "status": "OPEN"
        }
        st.session_state.trades.append(trade)
        
    @staticmethod
    def close_position(trade_id, exit_price, exit_date):
        for trade in st.session_state.trades:
            if trade['id'] == trade_id and trade['status'] == 'OPEN':
                trade['exit_price'] = exit_price
                trade['exit_date'] = exit_date
                
                # PNL Calculation (Assuming 1 lot / $1 per pip for simplicity in virtual sim)
                if trade['direction'] == 'LONG':
                    trade['pnl'] = (exit_price - trade['entry_price'])
                else:
                    trade['pnl'] = (trade['entry_price'] - exit_price)
                    
                trade['status'] = 'CLOSED'
                break

    @staticmethod
    def get_open_pnl(current_price):
        pnl = 0.0
        for trade in st.session_state.trades:
            if trade['status'] == 'OPEN':
                if trade['direction'] == 'LONG':
                    pnl += (current_price - trade['entry_price'])
                else:
                    pnl += (trade['entry_price'] - current_price)
        return pnl