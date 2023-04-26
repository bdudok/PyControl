#Treadmill with random reward

from pyControl.utility import *
from devices import *
import gc


v.reward_zone_distance = 5000 #distance between zones
v.reward_zone_open = 5*second #reward availability after RZ entry
v.reward_zone_length = 1000
v.reward_duration = 100*ms  # Time reward solenoid is open for.
v.poll_resolution = 1000*ms # Time to push events to the search state - mouse can't find new reward zone between polls
v.force_lap_reset = 200000 #lap reset triggered if not reset tag

#init attributes for use within states:
v.next_reward = 200 #this always adds a next reward in a random distance
v.lap_counter = 0
v.lick_count___ = 0
v.last_lap_end = 0 #position at the end of last lap
v.total_licks = 0

board = Breakout_1_2() # Breakout board.

# Instantiate hardware - would normally be in a seperate hardware definition file.

# Running wheel must be plugged into port 1 of breakout board.
belt_pos = Rotary_encoder(name='pos', sampling_rate=15, output='position', threshold=100,
                          rising_event='started_running',
                          falling_event='stopped_running')

lick_port = Lickometer(board.port_2, debounce=20)

# lap_reset_tag_cp = Digital_input(board.port_3.DIO_A, rising_event='RFID_CP', falling_event=None, debounce=5, pull='down')
# cp has no signal, use TIR pin instead
lap_reset_tag = Digital_input(board.port_3.DIO_B, rising_event='RFID_TIR', falling_event=None, debounce=5, pull='down')

solenoid = lick_port.SOL_1 # Reward delivery solenoid.

# States and events.

states = [ 'trial_start',
          'searching', 'reward_zone_entry', 'reward_zone', 'reward',#RZ behavior
          ]
          
events = [
          'lick_1', #lick port
    'RFID_TIR', #RFID tag in range
    'poll_timer', 'reward_timer', #internal timers
 'started_running', 'stopped_running', #utility
]

initial_state = 'trial_start'


#functions used by states

def lap_reset(force=False):
    '''
    This is called when either:
    force == True: the abs pos reaches a threshold set in v.force_lap reset,
    or when the lap reset tag is activated
    Should work from any state, should not change state
    '''
    disarm_timer('poll_timer')
    v.lap_counter += 1
    print_variables(['lap_counter', ])
    if force:
        #time has passed since the pos was reached, start from that
        v.last_lap_end += v.force_lap_reset
    else:
        #if called by lap reset tag
        v.last_lap_end = get_abs_pos()
    #refresh reward zones
    set_reward()

def get_abs_pos():
    '''
    return absolute belt position
    assumes that the rotary position counter never overflows
    this is also the mechanism to check for force reset - any time this is called.
    Should work from any state, should not change state
    '''
    curr_pos = belt_pos.position - v.last_lap_end
    if curr_pos > v.force_lap_reset:
        lap_reset(force=True)
        get_abs_pos()
    return curr_pos

def set_reward():
    '''
    Set the position of the next reward zone. we are working one by one, always setting just the next
    Also sets a poll timer
    '''
    v.next_reward = get_abs_pos() + v.reward_zone_distance + random() * v.reward_zone_distance
    set_timer('poll_timer', v.poll_resolution, output_event=True)

def run_start():
    belt_pos.record() # Start streaming wheel velocity to computer.

# State behaviour functions.
def trial_start(event):
    timed_goto_state('searching', 1*second)

def all_states(event):
    if event == 'RFID_TIR': #called by the lap reset sensor
        lap_reset()

def searching(event):
    '''
    this is the default state. periodically check if the next RZ has been reached.
    '''
    if event == 'entry':
        set_reward()
        gc.collect() #this is a good time to grabage collect as nothing urgent can happen
    elif event == 'poll_timer':
        if get_abs_pos() > v.next_reward:
            goto_state('reward_zone_entry')
        else:
            set_timer('poll_timer', v.poll_resolution, output_event=True)

def reward_zone_entry(event):
    '''Reset lick count for current rz, starts timeout, and waits for licks'''
    if event == 'entry':
        v.lick_count___ = 0
        set_timer('reward_timer', v.reward_zone_open)
        disarm_timer('poll_timer')
    elif event == 'lick_1':
        goto_state('reward')
    elif event == 'reward_timer':
        goto_state('searching')

def reward_zone(event):
    '''
    Lick returns to this state. wait for licks and terminate if RZ is over.
    '''
    if event == 'lick_1':
        goto_state('reward')
    elif event == 'reward_timer':
        goto_state('searching')
    # find another way to check for RZ distance limit, as this results in goto during entry of this. mybe movr check into lick.
    elif event not in ('entry', 'exit'):
        p = get_abs_pos()
        if p < v.next_reward or p > v.next_reward + v.reward_zone_length:
            disarm_timer('reward_timer')
            goto_state('searching')


def reward(event):
    '''
    Separate state for opening the reward (so the solenoid can't stay on).
    '''
    if event == 'entry':
        v.lick_count___ += 1
        timed_goto_state('reward_zone', v.reward_duration)
        #we hope that the reward_timer event cannot be missed if it happens during this exit or searching's entry.
        solenoid.on()
        v.total_licks += 1
    elif event == 'exit':
        solenoid.off()
    #need to repeat listening for timeout event, so it's not missed by reward_zone.
    elif event == 'reward_timer':
        goto_state('searching')