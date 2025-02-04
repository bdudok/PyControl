# Example of using a rotary encoder to measure running speed and trigger events when
# running starts and stops. The subject must run for 10 seconds to trigger reward delivery,
# then stop running for 5 seconds to initiate the next trial.

from pyControl.utility import *
from devices import *


v.reward_zone_distance = 200 #distance between zones
v.reward_zone_open = 5*second #reward availability after RZ entry
v.reward_duration = 100*ms  # Time reward solenoid is open for.
v.poll_resolution = 20*ms # Time to push events to the search state

#init attributes for use within states:
v.next_reward = 0
v.lap_counter = 0
v.last_lap_end = 0 #position at the end of last lap

board = Breakout_1_2() # Breakout board.

# Instantiate hardware - would normally be in a seperate hardware definition file.

# Running wheel must be plugged into port 1 of breakout board.
belt_pos = Rotary_encoder(name='pos', sampling_rate=15, output='position', threshold=1, )

lick_port = Lickometer(board.port_2)


solenoid = lick_port.SOL_1 # Reward delivery solenoid.

# States and events.

states = [
          'searching', 'reward_zone', 'reward', #RZ behavior
          ]
          
events = ['reward_off',
          'poll_delay',
          'lick_1',]

initial_state = 'searching'


#functions used by states

def lap_reset():
    #should also try resetting the pos attribute to zero
    v.lap_counter += 1
    v.last_lap_end = belt_pos.position

def get_abs_pos():
    return belt_pos.position - v.last_lap_end

def set_reward():
    v.next_reward = belt_pos.position + v.reward_zone_distance

def run_start():
    belt_pos.record() # Start streaming wheel velocity to computer.

# State behaviour functions.

def searching(event):
    if event == 'entry':
        set_reward()
    elif event == 'poll_delay':
        if belt_pos.position > v.next_reward:
            goto_state('reward_zone')
    #this works, but generates events that are logged. should be done by the rotary generating events.
    set_timer('poll_delay', v.poll_resolution, output_event=True)


def reward_zone(event):
    if event == 'entry':
        timed_goto_state('searching', v.reward_zone_open)
    elif event == 'lick_1':
        goto_state('reward')

def reward(event):
    # Deliver reward then go to inter trial interval.
    if event == 'entry':
        timed_goto_state('reward_zone', v.reward_duration)
        solenoid.on()
    elif event == 'exit':
        solenoid.off()