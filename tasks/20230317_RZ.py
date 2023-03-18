# Example of using a rotary encoder to measure running speed and trigger events when
# running starts and stops. The subject must run for 10 seconds to trigger reward delivery,
# then stop running for 5 seconds to initiate the next trial.

from pyControl.utility import *
from devices import *


v.reward_zone_distance = 200 #distance between zones
v.reward_zone_open = 5*second #reward availability after RZ entry
v.reward_duration = 100*ms  # Time reward solenoid is open for.
v.poll_resolution = 1000*ms # Time to push events to the search state

#init attributes for use within states:
v.next_reward = 200
v.lap_counter = 0
v.last_lap_end___ = 0 #position at the end of last lap
v.lick_count___ = 0
v.total_licks = 0

board = Breakout_1_2() # Breakout board.

# Instantiate hardware - would normally be in a seperate hardware definition file.

# Running wheel must be plugged into port 1 of breakout board.
belt_pos = Rotary_encoder(name='pos', sampling_rate=15, output='position', threshold=100,
                          rising_event='started_running',
                          falling_event='stopped_running')

lick_port = Lickometer(board.port_2, debounce=20)

# analog_input = Analog_input(pin=board.DAC_1, name='DAC1', sampling_rate=1000)


solenoid = lick_port.SOL_1 # Reward delivery solenoid.

# States and events.

states = [ 'trial_start',
          'searching', 'reward_zone_entry', 'reward_zone', 'reward',#RZ behavior
          ]
          
events = [
          'lick_1',
    'poll_timer', 'reward_timer',
 'started_running', 'stopped_running'
]

initial_state = 'trial_start'


#functions used by states

def lap_reset():
    #should also try resetting the pos attribute to zero
    v.lap_counter += 1
    v.last_lap_end___ = belt_pos.position

def get_abs_pos():
    return belt_pos.position - v.last_lap_end

def set_reward():
    v.next_reward = belt_pos.position + v.reward_zone_distance
    set_timer('poll_timer', v.poll_resolution, output_event=True)

def run_start():
    belt_pos.record() # Start streaming wheel velocity to computer.

# State behaviour functions.
def trial_start(event):
    timed_goto_state('searching', 1*second)

def searching(event):
    if event == 'entry':
        set_reward()
        v.lick_count___ = 0
    elif event == 'poll_timer':
        if belt_pos.position > v.next_reward:
            goto_state('reward_zone_entry')
        set_timer('poll_timer', v.poll_resolution, output_event=True)

def reward_zone_entry(event):
    if event == 'entry':
        v.lick_count___ == 0
        set_timer('reward_timer', v.reward_zone_open)
        disarm_timer('poll_timer')
    elif event == 'lick_1':
        goto_state('reward')
    elif event == 'reward_timer':
        goto_state('searching')

def reward_zone(event):
    if event == 'lick_1':
        goto_state('reward')
    elif event == 'reward_timer':
        goto_state('searching')

def reward(event):
    # Deliver reward then go to inter trial interval.
    if event == 'entry':
        v.lick_count___ += 1
        timed_goto_state('reward_zone', v.reward_duration)
        solenoid.on()
        v.total_licks += 1
    elif event == 'exit':
        solenoid.off()
    elif event == 'reward_timer':
        goto_state('searching')