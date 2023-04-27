'''
Functions for GUI control of water valve
Buttons are added to the GUI in run_task_tab.py
'''

def man_reward(self):
    if self.board.framework_running:
        self.board.send_reward_msg_to_pyboard()

def man_open():
    pass

def man_toggle():
    pass