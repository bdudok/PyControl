from . import utility
from . import timer
from . import framework as fw

# State machine variables.

user_task_file = None # State machine definition file

states = {} # Dictionary of {state_name: state_ID}

events = {} # Dictionary of {event_name: event_ID}

ID2name = {} # Dictionary of {ID: state_or_event_name}

transition_in_progress = False # Set to True during state transitions.

variables = None # User task variables object.

event_dispatch_dict = {} # {state_name: state behaviour function}

current_state = None

# State machine functions.

def setup_state_machine(task_file):
    global user_task_file, variables, transition_in_progress, states, events, ID2name, event_dispatch_dict

    user_task_file = task_file  # User task definition file module.
    variables = utility.v # User task variables object.
    transition_in_progress = False # Set to True during state transitions.

    # Adds state machine states and events to framework states and events dicts.
    states = {s: i+1 for s, i in zip(user_task_file.states, range(len(user_task_file.states)))}
    events = {e: i+1+len(user_task_file.states)
              for e, i in zip(user_task_file.events, range(len(user_task_file.events)))}

    ID2name = {ID: name for name, ID in list(states.items()) + list(events.items())}

    # Make dict mapping state names to state behaviour functiona.
    user_task_file_methods = dir(user_task_file)
    for state in list(user_task_file.states) + ['all_states', 'run_start', 'run_end']:
        if state in user_task_file_methods:
            event_dispatch_dict[state] = getattr(user_task_file, state)
        else:
            event_dispatch_dict[state] = None

def goto_state(next_state):
    # Transition to next state, calling exit action of old state
    # and entry action of next state.
    global transition_in_progress, current_state
    if type(next_state) is int: # ID passed in not name.
        next_state = ID2name[next_state]
    if transition_in_progress:
        raise fw.pyControlError("goto_state cannot not be called while processing 'entry' or 'exit' events.")
    if not next_state in states.keys():
        raise fw.pyControlError('Invalid state name passed to goto_state: ' + repr(next_state))
    transition_in_progress = True
    process_event('exit')
    timer.disarm_type(fw.state_typ) # Clear any timed_goto_states     
    if fw.data_output:
        fw.data_output_queue.put((fw.current_time, fw.state_typ, states[next_state]))
    current_state = next_state
    process_event('entry')
    transition_in_progress = False

def process_event(event):
    # Process event given event name by calling appropriate state event handler function.
    if type(event) is int: # ID passed in not name.
        event = ID2name[event]
    if event_dispatch_dict['all_states']:                  # If machine has all_states event handler function. 
        handled = event_dispatch_dict['all_states'](event) # Evaluate all_states event handler function.
        if handled: return                                 # If all_states event handler returns True, don't evaluate state specific behaviour.
    if event_dispatch_dict[current_state]:                 # If state machine has event handler function for current state.
        event_dispatch_dict[current_state](event)          # Evaluate state event handler function.

def start():
    global current_state
    # Called when run is started. Puts agent in initial state, and runs entry event.
    if event_dispatch_dict['run_start']:
        event_dispatch_dict['run_start']()
    current_state = user_task_file.initial_state
    if fw.data_output:
        fw.data_output_queue.put((fw.current_time, fw.state_typ, states[current_state]))
    process_event('entry')

def stop():
    # Calls user defined stop function at end of run if function is defined.
    if event_dispatch_dict['run_end']:
        event_dispatch_dict['run_end']()

def set_variable(v_name, v_str, checksum=None):
    # Set value of variable v.v_name to value eval(v_str).
    if checksum:
        str_sum = sum(v_str) if type(v_str) is bytes else sum(v_str.encode())
        if not str_sum == checksum:
            return False # Bad checksum.
    try:
        setattr(variables, v_name, eval(v_str))
        return True # Variable set OK.
    except Exception:
        return False # Bad variable name or invalid value string.

def get_variable(v_name):
    # Return string representing value of specified variable.
    try:
        return repr(getattr(variables, v_name))
    except Exception:
        return None

def get_events():
    # Print events as dict to USB serial.
    print(events)

def get_states():
    # Print states as a dict to USB serial.
    print(states)

def get_variables():
    # Print state machines variables as dict {v_name: repr(v_value)} to USB serial.
    print({k: repr(v) for k, v in variables.__dict__.items()})