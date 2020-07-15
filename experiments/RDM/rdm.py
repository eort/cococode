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
from IPython import embed as shell
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

###########################################
###         HANDLE INPUT DIALOG        ####
###########################################
# dialog with participants: Retrieve Subject number, session number, and practice
input_dict = dict(sub_id=0,sess_id=0,sess_type=sess_type)
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','sess_id','sess_type'])

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
# choose response functions
if response_info['resp_mode'] == 'meg':
    captureResponse = et.captureResponseMEG
elif response_info['resp_mode'] == 'keyboard': 
    captureResponse = et.captureResponseKB
if response_info['run_mode'] == 'dummy':
   captureResponse = et.captureResponseDummy

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

# prepare coherence levels of dots
if trial_info['sess_type'] != 'practice':
    coherence_lvls = param['coherence_lvl']  
else:
    coherence_lvls = [0.3+coh for coh in param['coherence_lvl']]
n_cohs = len(coherence_lvls)
noise_mean = timing_info['noise_mean']

# set response keys
resp_keys = [response_info['resp_left'],response_info['resp_right']]

# prepare a dataframe specifically for the stimulus positions
indices=pd.MultiIndex.from_tuples([(a+1,b+1) for a in range(n_blocks) for b in range(n_trials+param['n_zero'])], names=['block_no', 'trial_no'])
all_positions = pd.DataFrame(columns= {'positions':np.nan}, index=indices) 
################################
###    MAKE STIMULI          ###
################################
mon = monitors.Monitor('cocoLab',width = win_info['screen_width'],distance = win_info['screen_distance'])
mon.setSizePix(win_info['win_size'])
#create a window
win = visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscreen'], units='deg',screen=1, monitor = mon,autoLog=0)

# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()

# first all kind of structural messages
startBlock = visual.TextStim(win,text=stim_info["blockStart"],color=win_info['fg_color'],wrapWidth=win.size[0],units='pix',autoLog=0)
endBlock = visual.TextStim(win,text=stim_info["blockEnd"],color=win_info['fg_color'],wrapWidth=win.size[0],units='pix',autoLog=0)
endExp = visual.TextStim(win,text=stim_info["exp_outro"],color=win_info['fg_color'],wrapWidth=win.size[0],units='pix',autoLog=0)
warning = visual.TextStim(win,text=stim_info["warning"],color=win_info['fg_color'],wrapWidth=win.size[0],units='pix',autoLog=0)
feedback = visual.TextStim(win,text='',color=win_info['fg_color'],wrapWidth=win.size[0],units='pix',autoLog=0)
fixDot = et.fancyFixDot(win,fg_color = win_info['fg_color'],bg_color = win_info['bg_color'],size=18) 
cloud = visual.DotStim(win,color=win_info['fg_color'],units='deg',fieldSize=rdk['cloud_size'],nDots=rdk['n_dots'],dotLife=rdk['dotLife'] ,dotSize=rdk['size_dots'],speed=rdk['speed'],signalDots=rdk['signalDots'],noiseDots=rdk['noiseDots'],fieldShape = 'circle',coherence=0)

####################
###  SET TIMING  ###
####################
pause_frames = round(timing_info['pause_dur']*win_info['framerate'])
feed_frames = round(timing_info['feed_dur']*win_info['framerate'])
fix_frames = round(timing_info['fix_dur']*win_info['framerate'])
noise_seq = np.random.uniform(noise_mean-timing_info['noise_range'],noise_mean+timing_info['noise_range'], size=(n_blocks,n_trials+param['n_zero']))

###########################
###  START BLOCK LOOP # ###
###########################
for block_no in range(n_blocks):
    # create trial sequence
    trial_seq = np.tile(np.arange(n_cohs),int(n_trials/n_cohs))
    
    # add zero-coherence trials
    trial_seq = np.concatenate((trial_seq,np.ones(param['n_zero'],dtype=int)*n_cohs)) 

    # make sure no direction repetitions of coherence levels
    np.random.shuffle(trial_seq)
    while 0 in np.diff(trial_seq):
        np.random.shuffle(trial_seq)

    # make sure every coherence lvl is matched with both directions equal number of times
    dir_list = [-1,1]*int(n_trials/2/n_cohs)
    dir_dict = {}
    for coh in range(n_cohs):
        np.random.shuffle(dir_list)
        dir_dict[coh] =list(dir_list)

    # define direction sequence
    _dir_seq = []
    for coh in trial_seq:
        # allow for the option of having zero-coherence trials
        if coh == n_cohs:
            _dir_seq.append(0)
        else:
            _dir_seq.append(dir_dict[coh].pop())
    
    # add zero-coherence trials
    if param['n_zero']:
        coherence_lvls.append(0)
        n_trials = param['n_trials'] + param['n_zero'] 

    # create sequences
    dir_seq = [param['dir1'] if i==-1 else param['dir2'] if i==1 else 0  for i in _dir_seq]
    corr_resp_seq = [resp_keys[0] if i==-1 else resp_keys[1] if i==1 else None for i in _dir_seq]
    coh_seq = [coherence_lvls[i] for i in trial_seq ]
    trigger_seq = ['coh_{}_{}'.format(dir_seq[i],coherence_lvls.index(coh_seq[i])+1) for i in range(len(trial_seq))]

    # reset block variables
    trial_info['total_correct'] = 0 

    # show block intro 
    startBlock.text = stim_info["blockStart"].format(block_no+1,n_blocks)
    while True:
        et.drawFlip(win,[startBlock])                    
        cont=captureResponse(keys = [response_info['pause_resp']])    
        if cont == response_info['pause_resp']:
            break

    # send trigger
    logging.log(level=logging.INFO, msg='start_block')
    et.sendTriggers(trigger_info['block_on'],prePad=0.5,reset = 0.2)
    trial_info['block_no']=block_no+1

    ##########################
    ###  START TRIAL LOOP  ###
    ##########################
    for trial_no in range(n_trials):
        # force quite experiment
        escape = event.getKeys()
        if 'q' in escape:
            et.finishExperiment(win,data_logger)

        cloud.coherence = 0
        response=None
        # for timing tests, delete later
        trial_info['early_response'] = 0
        trial_info['timeout']=0
        # draw duration of fix cross from predefined distribution
        trial_info['noise_dur'] = noise_seq[block_no,trial_no]
        trial_info['trial_no'] = trial_no+1
        trial_info['trial_count']+=1
        # set specific orientations
        trial_info['corr_resp'] = corr_resp_seq[trial_no]
        trial_info['cur_coherence'] =coh_seq[trial_no]  
        trial_info['cur_dir'] = dir_seq[trial_no]
        trial_info['cur_trigger'] = trigger_seq[trial_no]    
         
        # draw RDK stimulus 
        if param['n_zero']:
            cloud.dir = trial_info['cur_dir']
        else:
            cloud.dir = None

        noise_frames = int(round(trial_info['noise_dur']*win_info['framerate']))
        stim_frames = noise_frames+int(round(timing_info['stim_dur']*win_info['framerate']))
        dot_frames = noise_frames+int(timing_info['resp_dur']*win_info['framerate'])

        ##########################
        ###  FIXATION PHASE    ###
        ##########################   
        # start trial and draw fixation and wait for 
        win.logOnFlip(level=logging.INFO, msg='start_fix\t{}'.format(trial_info['trial_count']))
        win.callOnFlip(et.sendTriggers,trigger_info['fix_on'],reset=0)  
        for frame in range(fix_frames):
            if frame == 5:
                win.callOnFlip(et.sendTriggers,0,reset=0)
            et.drawFlip(win,fixDot)  

        # remove premature responses
        event.clearEvents()
        t0 = core.getTime()
        # check whether a button in the response box is currently pressed & present a warning if so
        while captureResponse(keys=resp_keys+[None]) in resp_keys:
            if core.getTime()-t0>1.0: 
                et.drawFlip(win,[warning])  
       
        ##########################
        ###  STIMULUS PHASE    ###
        ##########################
        stimTime = dict(onset =np.nan)
        in_queue = queue.Queue()
        dot_positions = np.zeros((dot_frames,rdk['n_dots'],2))
        win.logOnFlip(level=logging.INFO, msg='start_noise\t{}\t{}'.format(trial_info['trial_count'],trial_info['noise_dur']))
        win.callOnFlip(et.sendTriggers,trigger_info['noise_on'],reset=0)
        for frame in range(dot_frames):     
            # start a parallel thread in the background that polls responses and doesnt interfere with the RDK
            respThread =  threading.Thread(target=captureResponse,kwargs={'keys':resp_keys + 250*[None],'in_queue':in_queue},daemon=1)
            respThread.start()   
            # show cloud
            if frame<stim_frames:
                if frame == 5: 
                    et.sendTriggers(0,reset=0)
                elif frame==noise_frames:
                    cloud.coherence = trial_info['cur_coherence']
                    win.logOnFlip(level=logging.INFO, msg='start_stim\t{}'.format(trial_info['trial_count']))
                    win.callOnFlip(et.sendTriggers,trial_info['cur_trigger'],reset=0)
                    win.timeOnFlip(stimTime,'onset')
                elif frame==noise_frames+5:
                    win.callOnFlip(et.sendTriggers,0,reset=0)     
                win.logOnFlip(level=logging.INFO, msg='cloud_frame\t{}\t{}'.format(trial_info['trial_count'],frame+1))
                et.drawFlip(win,fixDot + [cloud]) 
            else:               
                win.logOnFlip(level=logging.INFO, msg='nostim_frame\t{}\t{}'.format(trial_info['trial_count'],frame+1))
                et.drawFlip(win,fixDot)

            # save dot position
            dot_positions[frame,:,:] = cloud.verticesPix            

            # poll response break if a key was pressed
            try:
                response = in_queue.get(False)
            except queue.Empty:
                response = None
            if response in resp_keys:
                break

        win.logOnFlip(level=logging.INFO, msg='resp_time\t{}'.format(trial_info['trial_count']))
        et.drawFlip(win,fixDot)

        ##########################
        ###  POST PROCESSING   ###
        ##########################
        trial_info['resp_time'] = core.getTime()-stimTime['onset']
        trial_info['resp_key'] = response
        trial_info['correct'] = int(response==trial_info['corr_resp'])
        if trial_info['correct']:
            trial_info['total_correct']+=1  

        # check for too early or too late responses
        if frame == dot_frames-1:
            trial_info['timeout'] = 1
            feedback.text = 'Zu spät!'
        elif frame <= noise_frames:
            trial_info['early_response'] = 1
            feedback.text = 'Zu früh!' 

        # show feedback if no response was given       
        if trial_info['timeout'] == 1 or trial_info['early_response'] == 1:
            trial_info['correct'] = np.nan
            #et.sendTriggers(trigger_info['feedback_on'],prePad=0.01)
            win.logOnFlip(level=logging.INFO, msg='start_feed\t{}'.format(trial_info['trial_count']))
            win.callOnFlip(et.sendTriggers,trigger_info['feedback_on'],reset=0, prePad=0.024)
            for frame in range(feed_frames):
                if frame == 5:
                    win.callOnFlip(et.sendTriggers,0,reset=0)
                et.drawFlip(win,[feedback])   
        # end trial logging
        win.logOnFlip(level=logging.INFO, msg='end_trial\t{}'.format(trial_info['trial_count']))
        et.drawFlip(win,fixDot)
        
        # keep track of dot positions        
        all_positions.loc[(trial_info['block_no'],trial_info['trial_no']),'positions'] = dot_positions

        ##########################
        ###  LOGGING  PHASE    ###
        ########################## 
        if trial_info['trial_count'] == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['first_columns'])
        data_logger.writeTrial(trial_info)

    # show text at the end of a block 
    endBlock.text = stim_info["blockEnd"].format(block_no+1,int(100*trial_info['total_correct']/n_trials))
    win.logOnFlip(level=logging.INFO, msg='end_block\t{}'.format(trial_info['block_no']))
    for frame in range(pause_frames):
        et.drawFlip(win,[endBlock])
    event.clearEvents()

all_positions.to_csv(position_file,na_rep=pd.np.nan)
# end of experiment message
while True:
    et.drawFlip(win,[endExp])
    cont=captureResponse(keys = [response_info['pause_resp']])    
    if cont == response_info['pause_resp']:
        break
#cleanup
et.finishExperiment(win,data_logger,show_results=True)