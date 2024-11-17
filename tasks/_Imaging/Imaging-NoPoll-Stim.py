# Treadmill with random reward
from devices.frame_trigger import Frame_trigger
from pyControl.utility import *
from devices import *
import gc
#a version for sessions with no reward - position is not checked by regular poll. still everything is recorded
'''---------------------------------------------------- STIM CONFIG--------------------------------------------------'''
train_period = 3 #a stim train will be triggered in evey X sec #0 to never trigger.
train_count = None # number of max trains per session, use None for unlimited

v.houselight = False  # to turn on blue LED during task

'''------------------------------------------------------END CONFIG--------------------------------------------------'''

# calibration
cm = 41.5  # quad/cm
ul = 24  # ms/microliter

v.train_period = train_period * second #photostim train interval
v.train_count = train_count

# other settings
v.verbose = 1

# init attributes for use within states:
v.lap_counter = 0
v.last_lap_end = 0  # position at the end of last lap


board = Breakout_1_2()  # Breakout board.

# Instantiate hardware - would normally be in a seperate hardware definition file.

# Running wheel must be plugged into port 1 of breakout board.
belt_pos = Rotary_encoder(name='pos', sampling_rate=15, output='position', threshold=100, )

# lap_reset_tag_cp = Digital_input(board.port_3.DIO_A, rising_event='RFID_CP', falling_event=None, debounce=5, pull='down')
# cp has no signal, use TIR pin instead
lap_reset_tag = Digital_input(board.port_3.DIO_B, rising_event='RFID_TIR', falling_event=None, debounce=1000,
                              pull='down')

# house light led
led_power = Digital_output(pin=board.port_3.POW_B)

session_output = Digital_output(pin=board.BNC_1, ) #(not used with Recorder control)
opto_stim_ttl = Digital_output(pin=board.DAC_1, )
sync_output = Rsync(pin=board.BNC_2, mean_IPI=1000, event_name='rsync')  # sync signnal

# States and events.

states = ['trial_start',
          'recording',
          ]

events = [
    'lick_1',  # lick port
    'RFID_TIR',  # RFID tag in range
    # 'sol_on', 'sol_off',  # for control
    # 'manual_reward', 'manual_open', 'manual_toggle',  # for gui controls
    'manual_stim',  'photostim_train',# for optogenetics
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
    v.lap_counter += 1
    print_variables(['lap_counter', ])
    v.last_lap_end = belt_pos.position

def set_stim():
    '''
    Sets the stim timer
    '''
    if v.train_count is None or v.train_count:
        set_timer('photostim_train', v.train_period, output_event=True)
        if v.train_count is not None:
            v.train_count -= 1
    # gc.collect()  # this is a good time to garbage collect as nothing urgent can happen

def run_start():
    belt_pos.record()  # Start streaming wheel velocity to computer.
    session_output.pulse(10, duty_cycle=50, n_pulses=1)  # start microscope (not used with Recorder control)
    if v.houselight:
        led_power.on()

def run_end():
    session_output.pulse(10, duty_cycle=50, n_pulses=1)  # stop microscope (not used with Recorder control)
    led_power.off()

# State behaviour functions.
def trial_start(event):
    if event == 'entry':
        set_stim()
        timed_goto_state('recording', 1 * second)


def all_states(event):
    if event == 'RFID_TIR':  # called by the lap reset sensor
        lap_reset()
    elif event == 'manual_stim':
        opto_stim_ttl.pulse(10, duty_cycle=50, n_pulses=1)
    elif event == 'photostim_train':
        opto_stim_ttl.pulse(10, duty_cycle=10, n_pulses=1)
        set_stim()

def recording(event):
    pass #we don't have to do anything other than recording position and waiting for triggers