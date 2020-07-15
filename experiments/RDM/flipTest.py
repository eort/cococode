# created by Eduard Ort, 2019 
##########################
###  IMPORT LIBRARIES  ###
##########################
from psychopy import visual, core, event,gui,logging, monitors #import some libraries from PsychoPy
import expTools as et # custom scripts
import json # to load configuration files
import sys, os # to interact with the operating system
from datetime import datetime # to get the current time
import numpy as np # to do fancy math shit
import glob # to search in system efficiently
import threading # parallel response collection
import queue # parallel response collection
import pandas as pd # export 

# reset all triggers to zero
os.system("/usr/local/bin/parashell 0x378 0")
#######################################
###          LOAD CONFIG FILE     #####
#######################################
try:
    jsonfile = sys.argv[1]
except IndexError as e:
    print("No config file provided. Stop it here.")
    sys.exit(-1)
try:
    with open(jsonfile) as f:    
        param = json.load(f)
except FileNotFoundError as e:
    print("{} is not a valid config file. Stop it here.".format(jsonfile))
    sys.exit(-1)

###########################################
###          READ OUT JSON SIDECAR     ####
###########################################
timing_info =param['timing_info']                 # information on the timings of the sequence
stim_info=param['stim_info']                      # information on all stimuli to be drawn
win_info=param['win_info']                        # information on the psychopy window  
response_info=param['response_info']              # information on response collection  
logging_info=param['logging_info']                # information on files and variables for logging
trigger_info = param['trigger_info']              # information on all the MEG trigger values and names
n_trials = param['n_trials']                      # number trials per block
n_blocks = param['n_blocks']                      # number total blocks
sess_type = param['sess_type']                    # are we practicing or not
rdk = stim_info['cloud_specs']                    # info on RDK

# unable trigger setting if we are not in the scanner
if response_info['resp_mode']=='meg':
    def doNothing(*args,**kwargs): pass
    et.sendTriggers = doNothing

###########################################
###         HANDLE INPUT DIALOG        ####
###########################################
# dialog with participants: Retrieve Subject number, session number, and practice
input_dict = dict(sub_id=0,sess_id=0,sess_type=sess_type,noise_duration=timing_info['noise_mean'])
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','sess_id','sess_type',"noise_duration"])

# check for input
if inputGUI.OK == False:
    print("Experiment aborted by user")
    core.quit()
while input_dict['sess_id'] not in [1,2,3]:
    print('WARNING: You need to specify a session number (1,2,3)')
    inputGUI.show()
    if inputGUI.OK == False:
        print("Experiment aborted by user")
        core.quit()

# check whether settings match config file
if sess_type!=input_dict['sess_type']:
    print('WARNING: specified session type does not fit config file. This might cause issues further down the stream...')
    logging.warning('WARNING: specified session type does not fit config file. This might cause issues further down the stream...')

###########################################
###           SET UP OVERHEAD          ####
###########################################

# prepare the logfile (general log file, not data log file!) and directories
logFileID = logging_info['skeleton_file'].format(input_dict['sub_id'],input_dict['sess_id'],param['name'],str(datetime.now()).replace(' ','-').replace(':','-'))
log_file = os.path.join('log',param['exp_id'],logFileID+'.log')
# create a output file that collects all variables 
output_file = os.path.join('dat',param['exp_id'],logFileID+'.csv')
# one more outputfile for the dot position per frame block,trial
position_file = os.path.join('positions',param['exp_id'],logFileID+'.csv')
# save the current settings per session, so that the data files stay slim
settings_file = os.path.join('settings',param['exp_id'],logFileID+'.json')
for f in [log_file,position_file,settings_file,output_file]:
    if not os.path.exists(os.path.dirname(f)): 
        os.makedirs(os.path.dirname(f))
os.system('cp {} {}'.format(jsonfile,settings_file))
lastLog = logging.LogFile(log_file, level=logging.INFO, filemode='w')

# init logger: update the constant values (things that wont change)
trial_info = {"sub_id":input_dict['sub_id'],
                "sess_id":input_dict['sess_id'],
                "sess_type":input_dict['sess_type'],
                "start_exp_time":core.getTime(),
                "end_block_time":np.nan,
                "trial_count":0,
                'logFileID':logFileID}

for vari in logging_info['logVars']:
    trial_info[vari] = param[vari]

###########################################
###  PREPARE EXPERIMENTAL SEQUENCE     ####
###########################################

resp_keys = [response_info['resp_left'],response_info['resp_right']]

mon = monitors.Monitor('cocoLab',width = win_info['screen_width'],distance = win_info['screen_distance'])
mon.setSizePix(win_info['win_size'])
#create a window
win = visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscreen'], units='deg',screen=1, monitor = mon)

# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()

fixDot = et.fancyFixDot(win, fg_color = win_info['fg_color'],bg_color = win_info['bg_color'],size=18) 
cloud = visual.DotStim(win,units='deg',fieldSize=rdk['cloud_size'],nDots=rdk['n_dots'],dotLife=rdk['dotLife'] ,dotSize=rdk['size_dots'],speed=rdk['speed'],signalDots=rdk['signalDots'],noiseDots=rdk['noiseDots'],fieldShape = 'circle',coherence=0)

###########################
###  START BLOCK LOOP # ###
###########################
for block_no in range(n_blocks):

    escape = event.getKeys()
    if 'q' in escape:
        et.finishExperiment(win,data_logger)    
    noise_frames = int(round(1*win_info['framerate']))
    dot_frames = noise_frames+int(2*win_info['framerate'])
 
    ##########################
    ###  STIMULUS PHASE    ###
    ##########################
    in_queue = queue.Queue()
    #et.sendTriggers(trigger_info['noise_on'],reset=0)
    for frame in range(1,dot_frames):     
        # start a parallel thread in the background that polls responses and doesnt interfere with the RDK
        respThread =  threading.Thread(target=et.captureResponse,kwargs={'resp_mode':response_info['resp_mode'],'run_mode':response_info['run_mode'],'keys':resp_keys,'in_queue':in_queue},daemon=1)
        respThread.start()   

        et.drawCompositeStim(fixDot)#+ [cloud])
        win.logOnFlip(level=logging.INFO, msg='stim_frame_{}'.format(frame))
        win.flip()
 
        # poll response break if a key was pressed
        try:
            response = in_queue.get(False)
        except queue.Empty:
            response = None
        if response in resp_keys:
            break
    win.flip()
    ##########################
    ###  LOGGING  PHASE    ###
    ##########################
    trial_info['trial_count'] +=1 
    if trial_info['trial_count'] == 1:
        data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['first_columns'])
    data_logger.writeTrial(trial_info)


#cleanup
et.finishExperiment(win,data_logger,show_results=True)