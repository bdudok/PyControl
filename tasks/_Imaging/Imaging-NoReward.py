# Treadmill with random reward
from devices.frame_trigger import Frame_trigger
from pyControl.utility import *
from devices import *
import gc

'''---------------------------------------------------- TASK CONFIG--------------------------------------------------'''
n_zones = 1  # number of zones per lap
rz_open_time = 5  # s
rz_length = 10  # cm
max_lick_per_zone = 10
hidden_zones = True
drop_size = 2  # microliters

'''------------------------------------------------------END CONFIG--------------------------------------------------'''

# calibration
cm = 41.5  # quad/cm
ul = 24  # ms/microliter

# task parameters
v.reward_zone_open = rz_open_time * second  # reward availability after RZ entry
v.reward_zone_length = int(rz_length * cm)
v.reward_duration = int(drop_size * ul)  # Time reward solenoid is open for. - calibrated to microliters
v.max_lick_per_zone = max_lick_per_zone
v.is_hidden = hidden_zones  # if not hidden, reward always given on reward zone entry
v.houselight = True  # to turn on blue LED suring task

# other settings
v.reward_zone_distance = int(200 / n_zones * cm)  # distance between zones
v.poll_resolution = 1000 * ms  # Time to push events to the search state - mouse can't find new reward zone between polls
v.force_lap_reset = int(220 * cm)  # lap reset triggered if not reset tag
v.manual_valve_open = 1 * second
v.verbose = 1

# init attributes for use within states:
v.next_reward = 0  # starting reward zone
v.lap_counter = 0
v.lick_count___ = 0
v.reward_zone_entry_time___ = 0
v.reward_zone_lapsed___ = False
v.last_lap_end = 0  # position at the end of last lap
v.total_licks = 0
v.sol_toggle___ = 0

board = Breakout_1_2()  # Breakout board.

# Instantiate hardware - would normally be in a seperate hardware definition file.

# Running wheel must be plugged into port 1 of breakout board.
belt_pos = Rotary_encoder(name='pos', sampling_rate=15, output='position', threshold=100, )
# rising_event='started_running',
# falling_event='stopped_running')

lick_port = Lickometer(board.port_2, debounce=50)

# lap_reset_tag_cp = Digital_input(board.port_3.DIO_A, rising_event='RFID_CP', falling_event=None, debounce=5, pull='down')
# cp has no signal, use TIR pin instead
lap_reset_tag = Digital_input(board.port_3.DIO_B, rising_event='RFID_TIR', falling_event=None, debounce=1000,
                              pull='down')

# led control and power
led_power = Digital_output(pin=board.port_3.POW_B)
# led_control = Digital_output(pin=board.port_3.POW_A)

solenoid = lick_port.SOL_1  # Reward delivery solenoid.

session_output = Digital_output(pin=board.BNC_1, )
opto_stim_ttl = Digital_output(pin=board.DAC_1, )
sync_output = Rsync(pin=board.BNC_2, mean_IPI=1000, event_name='rsync')  # sync signnal
# frame_trigger = Frame_trigger(pin=board.DAC_1, pulse_rate=30, name='frame_trigger')

# States and events.

states = ['trial_start',
          'searching', 'reward_zone_entry', 'reward_zone', 'reward',  # RZ behavior
          ]

events = [
    'lick_1',  # lick port
    'RFID_TIR',  # RFID tag in range
    'poll_timer', 'reward_timer',  # internal timers
    'sol_on', 'sol_off',  # for control
    'manual_reward', 'manual_open', 'manual_toggle',  # for gui controls
    'manual_stim',  # for optogenetics
    'rsync',  # 'frame_trigger'#utility 'started_running', 'stopped_running',
]

initial_state = 'trial_start'


# functions used by states

def lap_reset(force=False):
    '''
    This is called when either the abs pos reaches a threshold set in v.force_lap reset,
    or when the lap reset tag is activated
    Should work from any state, should not change state
    '''
    # disarm_timer('poll_timer')
    v.lap_counter += 1
    print_variables(['lap_counter', ])
    v.last_lap_end = belt_pos.position
    # refresh reward zones - not for RF as rewards are in abs_pos
    # set_reward()


# def get_abs_pos(): not used for RF
#     '''
#     return absolute belt position
#     assumes that the rotary position counter never overflows
#     this is also the mechanism to check for force reset - any time this is called.
#     Should work from any state, should not change state
#     '''
#     curr_pos = belt_pos.position - v.last_lap_end
#     if curr_pos > v.force_lap_reset:
#         lap_reset(force=True)
#         return curr_pos - v.force_lap_reset
#     return curr_pos

def get_random_distance(m):
    # return min(m*2, max(m/2, random() * m * 1.5))
    return min(m * 2, max(m / 2, gauss_rand(m, m / 4)))


def close_reward_zone():
    v.reward_zone_lapsed___ = True
    set_timer('reward_timer', 10)


def set_reward():
    '''
    Set the position of the next reward zone. we are working one by one, always setting just the next
    Also sets a poll timer
    '''
    v.next_reward = belt_pos.position + get_random_distance(v.reward_zone_distance)
    if v.verbose:
        print_variables(['next_reward', ])
    set_timer('poll_timer', v.poll_resolution, output_event=True)


def run_start():
    belt_pos.record()  # Start streaming wheel velocity to computer.
    session_output.pulse(10, duty_cycle=50, n_pulses=1)  # start microscope
    # start LED light
    # led_control.pulse(100, duty_cycle=10, n_pulses=False)
    if v.houselight:
        led_power.on()


def run_end():
    session_output.pulse(10, duty_cycle=50, n_pulses=1)  # stop microscope
    led_power.off()
    # led_control.off()


# State behaviour functions.
def trial_start(event):
    timed_goto_state('searching', 1 * second)


def all_states(event):
    if event == 'RFID_TIR':  # called by the lap reset sensor
        lap_reset()
    elif event == 'sol_on':
        solenoid.on()
    elif event == 'sol_off':
        solenoid.off()
    elif event == 'manual_reward':
        set_timer('sol_off', 1 + v.reward_duration)
        publish_event('sol_on')
    elif event == 'manual_open':
        set_timer('sol_off', 1 + v.manual_valve_open)
        publish_event('sol_on')
    elif event == 'manual_toggle':
        if v.sol_toggle___:
            publish_event('sol_on')
        else:
            publish_event('sol_off')
    elif event == 'manual_stim':
        opto_stim_ttl.pulse(10, duty_cycle=50, n_pulses=1)


def searching(event):
    '''
    this is the default state. periodically check if the next RZ has been reached.
    '''
    if event == 'entry':
        set_reward()
        gc.collect()  # this is a good time to garbage collect as nothing urgent can happen
    elif event == 'poll_timer':
        if belt_pos.position > v.next_reward:
            goto_state('reward_zone_entry')
        else:
            set_timer('poll_timer', v.poll_resolution, output_event=True)


def reward_zone_entry(event):
    '''Reset lick count for current rz, starts timeout, and waits for licks'''
    if event == 'entry':
        disarm_timer('poll_timer')
        v.lick_count___ = 0
        v.reward_zone_entry_time___ = get_current_time()
        v.reward_zone_lapsed___ = False
        if not v.is_hidden:
            set_timer('lick_1', 10 * ms)
        set_timer('reward_timer', v.reward_zone_open)
    elif event == 'lick_1':
        goto_state('reward')
    elif event == 'reward_timer':
        goto_state('searching')


def reward_zone(event):
    '''
    Lick returns to this state. wait for licks and terminate if RZ is over.
    '''
    if event == 'entry':
        if v.lick_count___ >= v.max_lick_per_zone:
            close_reward_zone()
        elif get_current_time() > v.reward_zone_entry_time___ + v.reward_zone_open:
            close_reward_zone()
        elif belt_pos.position > (v.next_reward + v.reward_zone_length):  # abort if zone size passed
            close_reward_zone()
    elif event == 'lick_1':
        if not v.reward_zone_lapsed___:
            goto_state('reward')
        else:
            goto_state('searching')
    elif event == 'reward_timer':
        goto_state('searching')


def reward(event):
    '''
    Separate state for opening the reward (so the solenoid can't stay on).
    '''
    if event == 'entry':
        v.lick_count___ += 1
        if v.verbose:
            print_variables(['total_licks', ])
        timed_goto_state('reward_zone', v.reward_duration)
        # we hope that the reward_timer event cannot be missed if it happens during this exit or searching's entry. - it can.
        solenoid.on()
        v.total_licks += 1
    elif event == 'exit':
        solenoid.off()
    else:
        if v.lick_count___ >= v.max_lick_per_zone:
            close_reward_zone()
        elif get_current_time() > (v.reward_zone_entry_time___ + v.reward_zone_open):
            close_reward_zone()
        elif belt_pos.position > (v.next_reward + v.reward_zone_length):
            close_reward_zone()
