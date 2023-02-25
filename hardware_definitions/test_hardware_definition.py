# This hardware definition specifies that 3 pokes are plugged into ports 1-3 and a speaker into
# port 4 of breakout board version 1.2.  The houselight is plugged into the center pokes solenoid socket.

from devices import *
from devices.breakout_1_2 import Breakout_1_2
from devices.rotary_encoder import Rotary_encoder

board = Breakout_1_2()

# Instantiate Devices.
rotary = Rotary_encoder(name='pos', sampling_rate=15, output='position', )
# on frame trigger can be read by calling rotary.read_sample()

