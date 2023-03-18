# Example of using a rotary encoder to measure running speed and trigger events when
# running starts and stops. The subject must run for 10 seconds to trigger reward delivery,
# then stop running for 5 seconds to initiate the next trial.

from pyControl.utility import *
from devices import *


board = Breakout_1_2() # Breakout board.

analog_input = Analog_input(pin=board.BNC_1, name='BNC1', sampling_rate=1000)


# States and events.

states = [
          'searching',
          ]
          
events = [

]

initial_state = 'searching'


def searching(event):
    if event == 'entry':
        pass