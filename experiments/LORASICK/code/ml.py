# created by Eduard Ort, 2020

##########################
###  IMPORT LIBRARIES  ###
##########################
from psychopy import visual, core, event,gui,logging, monitors  # import some libraries from PsychoPy
import expTools as et                                           # custom scripts
import json                                                     # to load configuration files
import sys, os                                                  # to interact with the operating system
from datetime import datetime                                   # to get the current time
import numpy as np                                              # to do fancy math shit
import glob                                                     # to search in system efficiently
import pandas as pd                                             # neat way of storing and writing data
import parallel                                                 # communication with the parallel port
import itertools as it                                          # doing some combinatorics

#######################################
###          LOAD CONFIG FILE     #####
#######################################
try:
    jsonfile = sys.argv[1]
except IndexError as e:
    logging.error("No config file provided. Stop it here.")
    sys.exit(-1)
try:
    with open(jsonfile) as f:    
        param = json.load(f)
except FileNotFoundError as e:
    logging.error("{} is not a valid config file. Stop it here.".format(jsonfile))
    sys.exit(-1)

###########################################
###          READ OUT JSON SIDECAR     ####
###########################################
timing_info =param['timing_info']                 # information on the timings of the sequence
stim_info=param['stim_info']                      # information on all stimuli to be drawn
win_info=param['win_info']                        # information on the psychopy window  
response_info=param['response_info']              # information on response collection  
reward_info=param['reward_info']                  # Information on the reward schedule
logging_info=param['logging_info']                # information on files and variables for logging
trigger_info = param['trigger_info']              # information on all the MEG trigger values and names
bar = stim_info['progress_bar']                   # make drawing the progressbar less of a pain

###########################################
###         HANDLE INPUT DIALOG        ####
###########################################
# dialog with participants: Retrieve Subject number, session number, and practice
input_dict = dict(sub_id=0,ses_id=param['ses_id'])
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','ses_id'],show=False)
while True:
    inputGUI.show()
    if inputGUI.OK == False:
        logging.warning("Experiment aborted by user")
        core.quit()
    if input_dict['ses_id'] in ['{:02d}'.format(i) for i in range(1,param['n_ses']+1)] +['scr','prac','intake']:
        break
    else:
        logging.warning('WARNING: {} is not a valid ses_id'.format(input_dict['ses_id']))

# check whether settings match config file
if reward_info['rep_block']*reward_info['high_prob']!=int(reward_info['rep_block']*reward_info['high_prob']):
    logging.warning('Current reward settings do not allow proper counterbalancing: Adjust the reward probabilities or the size of the building blocks.')
if sum([bl%(2*reward_info['rep_block']) for bl in param['volatile_blocks']])!=0:
    logging.warning('Current reward settings do not allow proper counterbalancing: Adjust block length of volatile blocks or the size of the building blocks.')

###########################################
###           SET UP OVERHEAD          ####
###########################################
# choose response functions
if response_info['resp_mode'] == 'meg':
    captureResponse = et.captureResponseMEG
    port = parallel.Parallel()
elif response_info['resp_mode'] == 'keyboard': 
    captureResponse = et.captureResponseKB
    port = None
if response_info['run_mode'] == 'dummy':
   captureResponse = et.captureResponseDummy

# prepare the logfile (general log file, not data log file!) and directories
logFileID = logging_info['skeleton_file'].format(input_dict['sub_id'],input_dict['ses_id'],param['name'],param['proj_id'],str(datetime.now()).replace(' ','-').replace(':','-'))
log_file = os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.log').format(input_dict['sub_id'],input_dict['ses_id'],'log')
# create a output file that collects all variables 
output_file = os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.csv').format(input_dict['sub_id'],input_dict['ses_id'],'beh')
# save the current settings per session, so that the data files stay slim
settings_file=os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.json').format(input_dict['sub_id'],input_dict['ses_id'],'settings')

# make output directories
for f in [settings_file,output_file,log_file]:
    os.makedirs(os.path.dirname(f), exist_ok=True)
os.system('cp {} {}'.format(jsonfile,settings_file))
lastLog = logging.LogFile(log_file, level=logging.INFO, filemode='w')

# init logger:  update the constant values (things that wont change)
trial_info = {"sub_id":input_dict['sub_id'],
                "ses_id":input_dict['ses_id'],
                'phase_no':0,
                'block_no':0,
                'high_prob':reward_info['high_prob'],
                'logFileID':logFileID}

# add variables to the logfile that are defined in config file
for vari in logging_info['logVars']:
    trial_info[vari] = param[vari]

# set response keys
resp_keys = [response_info['resp_left'],response_info['resp_right']]

###########################################
###  PREPARE EXPERIMENTAL SEQUENCE     ####
###########################################
# load predefined RGB codes
rgb_dict = stim_info['stim_colors']

# select colors from predefined options based on sub id and sess id, separately for screening and real sessions
perms = list(it.permutations(range(param['n_ses'])))
if trial_info['ses_id'] not in  ['{:02d}'.format(i) for i in range(1,param['n_ses']+1)]:
    color_idx = 0
else:
    color_idx=perms[trial_info['sub_id']%len(perms)][trial_info['ses_id']-1]
colors = stim_info['color_combinations'][color_idx]
np.random.shuffle(colors)
trial_info['color1'] = colors[0]
trial_info['color2'] = colors[1]
total_points = 0
# counterbalance the order of volatile and stable blocks across subs and sessions (make sure that balancing is orthogonal to color counterbalancing)
trial_info['phase_type_order'] = ['sv','vs'][trial_info['sub_id']%(len(perms)*2)<len(perms)] # (v)olatile, (s)table

np.random.shuffle(param['volatile_blocks'])
if trial_info['phase_type_order'] == 'sv':
    phase_types = ['stable']+['volatile']*round(len(param['volatile_blocks']))
    blocks = param['stable_blocks']+ param['volatile_blocks']
else:
    phase_types = ['volatile']*round(len(param['volatile_blocks']))+['stable']
    blocks = param['volatile_blocks']+param['stable_blocks']

# create building blocks of possible location/validity combinations 
reward_ratio = np.array([1]*round(reward_info['high_prob']*reward_info['rep_block'])+[0]*round((1-reward_info['high_prob'])*reward_info['rep_block']))
# extend this balanced ratio to location (left,right)
# 0 unreward left, 1 rewarded left, 2 unrewarded right, rewarded right
reward_ratio_both_sides = np.concatenate((reward_ratio,reward_ratio+2))

# initialize full trial list
trial_seq = []
magn_seq = []
for n_trials in blocks:
    # per consistent block, generate all trial types
    target_reward_side = np.repeat(reward_ratio_both_sides,n_trials/len(reward_ratio_both_sides)).tolist()
    # per consistent block, generate all magnitude options (unbalanced)
    magnitudes = np.array(reward_info['mags'])
    for reps in range(round(n_trials/len(reward_info['mags']))-1):
        magnitudes = np.concatenate((magnitudes,reward_info['mags'])).tolist()
    # shuffle all the orders and add them to the full trial list
    np.random.shuffle(magnitudes)
    np.random.shuffle(target_reward_side)
    trial_seq+=target_reward_side
    magn_seq+=magnitudes
# make everything sequence that will later be used
trial_seq = np.array(trial_seq)
magn_seq = np.array(magn_seq)
# when will there be pauses in the experiment?
pause_seq = np.arange(0,trial_seq.shape[0],param['pause_interval'])

# alternating between target colors across blocks (if uneven number of blocks, round up, and drop extra blocks implicitly)
color_seq = [colors, colors[::-1]]*np.ceil(len(phase_types)/2).astype(int)

# define sequence when a block switch should occur
change_seq = np.cumsum([0]+blocks[:-1])

# 0,1 target is on left, 2,3 target is on right
high_prob_side = [resp_keys[0] if i in [0,1] else resp_keys[1] for i in trial_seq]
# 0, 2 the high likely target won't get reward, 1,3 the high likely target will get reward
reward_validity_seq = ['valid' if i in [1,3] else 'invalid' for i in trial_seq]

####################
###  SET TIMING  ###
####################
fix_seq=np.random.uniform(timing_info['fix_mean']-timing_info['fix_range'],timing_info['fix_mean']+timing_info['fix_range'],size=trial_seq.shape)
select_seq=np.random.uniform(timing_info['select_mean']-timing_info['select_range'],timing_info['select_mean']+timing_info['select_range'],size=trial_seq.shape)
# convert timing to frames
pause_frames = round(timing_info['pause_dur']*win_info['framerate'])
feed_frames = round(timing_info['feed_dur']*win_info['framerate'])
resp_frames = round(timing_info['resp_dur']*win_info['framerate'])
fix_frames_seq = (fix_seq*win_info['framerate']).round().astype(int)
select_frames_seq = (select_seq*win_info['framerate']).round().astype(int)
 
##################################
###      MAKE STIMULI          ###
##################################
#create a window
mon = monitors.Monitor('cocoLab',width = win_info['screen_width'],distance = win_info['screen_distance'])
mon.setSizePix(win_info['win_size'])
win=visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscr'],units="deg",autoLog=0,monitor=mon)

# and text stuff
startExp = visual.TextStim(win,text='Willkommen zur Lernaufgabe!\nGleich geht es los.',color=win_info['fg_color'],height=0.6,autoLog=0)
startBlock = visual.TextStim(win,text=stim_info['startBlock_text'],color=win_info['fg_color'],height=0.6,autoLog=0)
endBlock = visual.TextStim(win,text=stim_info['endBlock_text'],color=win_info['fg_color'],autoLog=0,height=0.6)
endExp = visual.TextStim(win,text=stim_info['endExp_text'],color=win_info['fg_color'],autoLog=0,height=0.6)
warning = visual.TextStim(win,text=stim_info["warning"],color='white',autoLog=0,height=0.6)
timeout_screen = visual.TextStim(win,text='Zu langsam!',color='white',height=0.6,autoLog=0)
# and stimuli
progress_bar =visual.Rect(win,height=bar['height'],width=bar['width'],lineColor=None,fillColor=bar['color'],pos=[-bar['horiz_dist'],-bar['vert_dist']],autoLog=0)
progress_update =visual.Rect(win,height=bar['height'],width=0,lineColor=None,fillColor=bar['color'],autoLog=0,pos=(-bar['horiz_dist'],-bar['vert_dist']))
progress_bar_start=visual.Rect(win,width=bar['width'],height=bar['height'],lineColor=None,fillColor=bar['color'],pos = [-bar['horiz_dist'],-bar['vert_dist']],autoLog=0)
progress_bar_end =visual.Rect(win,width=bar['width'],height=bar['height'],lineColor=None,fillColor=bar['color'],pos = [bar['horiz_dist'],-bar['vert_dist']],autoLog=0)
fixDot = et.fancyFixDot(win, bg_color = win_info['bg_color'],size=0.4) 
leftframe = visual.Rect(win,width=stim_info['bar_width'],height=stim_info['bar_height'],fillColor=None,pos=[-stim_info['bar_x'],stim_info['bar_y']],lineWidth=stim_info['line_width'],autoLog=0)
rightframe = visual.Rect(win,width=stim_info['bar_width'],height=stim_info['bar_height'],fillColor=None,pos=[stim_info['bar_x'],stim_info['bar_y']],lineWidth=stim_info['line_width'],autoLog=0)
leftbar = visual.Rect(win,width=stim_info['bar_width'],lineColor=None,autoLog=0)
rightbar = visual.Rect(win,width=stim_info['bar_width'],lineColor=None,autoLog=0)
selectbar = visual.Rect(win,width=stim_info['bar_width']*1.7,height=stim_info['bar_height']*1.4,lineColor=win_info['fg_color'],fillColor=None,lineWidth=stim_info['line_width'],autoLog=0)
smiley = visual.ImageStim(win,'code/smiley.png',contrast=-1,size=[1.1*stim_info['bar_width'],1.1*stim_info['bar_width']],autoLog=0)
frowny = visual.ImageStim(win,'code/frowny.png',contrast=-1,size=[1.1*stim_info['bar_width'],1.1*stim_info['bar_width']],autoLog=0)

# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()

# reset all triggers to zero
et.sendTriggers(port,0)

# experimental phases (unique things on screen)
fix_phase = fixDot[:] +[progress_bar,progress_bar_start,progress_bar_end]
stim_phase = fixDot[:] + [progress_bar,progress_bar_start,progress_bar_end,leftframe,rightframe,leftbar,rightbar]
select_phase = fixDot[:] +[progress_bar,progress_bar_start,progress_bar_end,selectbar,rightframe,leftframe,leftbar,rightbar]
feedback_phase = [progress_bar,progress_bar_start,progress_bar_end,progress_update,selectbar,rightframe,leftframe,leftbar,rightbar]

####################
###  START EXP   ###
####################
while 'c' not in event.getKeys():
    et.drawFlip(win,[startExp])          

######################
###  START TRIALS  ###
######################
for trial_no in range(trial_seq.shape[0]):
    # set Block variables every time a context change occurred
    if trial_no in change_seq:
        trial_info['phase_type'] = phase_types[trial_info['phase_no']]
        trial_info['phase_length'] = blocks[trial_info['phase_no']]
        trial_info['high_prob_color'] = color_seq[trial_info['phase_no']][0]
        trial_info['low_prob_color'] = color_seq[trial_info['phase_no']][1]
        trial_info['phase_no'] += 1
        trial_info['trialInPhase_no'] =0

    # start block message  
    if trial_no in pause_seq:
        # save data of a block to file (behavior is updated after every block)
        if trial_info['block_no']>1: data_logger.write2File()
        event.clearEvents()
        # reset block variables
        block_correct = 0
        trial_info['block_no'] += 1     
        startBlock.text = stim_info["startBlock_text"].format(trial_info['block_no'],pause_seq.shape[0])
        while True:
            et.drawFlip(win,[startBlock])                       
            cont=captureResponse(port,keys = [response_info['pause_resp'],None])    
            if cont == response_info['pause_resp']:            
                while captureResponse(port, keys=resp_keys+[None]) in resp_keys:
                    win.flip()
                win.callOnFlip(et.sendTriggers,port,trigger_info['start_block'],reset =.5)
                win.logOnFlip(level=logging.INFO, msg='start_block\t{}'.format(trial_info['phase_no']))
                win.flip()
                break

    # force quite experiment
    if 'q' in event.getKeys():
        et.finishExperiment(win,data_logger)

    #######################
    ###  SET VARIABLES  ###
    #######################
    # first reset
    trial_info['reward'] = 0  
    trial_info['resp_key']=None
    trial_info['timeout']=0   
    trial_info['choice'] = None
    trial_info['choice_side'] = None
    leftbar.fillColor = win_info['bg_color']
    rightbar.fillColor = win_info['bg_color'] 

    # read out trial variables
    trial_info['trial_no'] = trial_no+1
    trial_info['trialInPhase_no']+=1
    trial_info['mag_left'] = magn_seq[trial_no][0]
    trial_info['mag_right'] = magn_seq[trial_no][1]
    trial_info['high_prob_side'] = high_prob_side[trial_no]
    trial_info['reward_validity'] = reward_validity_seq[trial_no]
    trial_info['position1'] = 'left'     # where was option 1
    trial_info['position2'] = 'left'     # where was option 1
    trial_info['mag1'] = trial_info['mag_left'] # what magnitude had option 1
    trial_info['mag2'] = trial_info['mag_left'] # what magnitude had option 2
    trial_info['prob1'] = trial_info['high_prob'] # what magnitude had option 1

    # some parameters depend on the stimulus side  
    if trial_info['high_prob_side'] == resp_keys[0]:
        leftColor = et.rgb2psypy(rgb_dict[trial_info['high_prob_color']])
        rightcolor = et.rgb2psypy(rgb_dict[trial_info['low_prob_color']])
        trial_info['color_left'] = trial_info['high_prob_color']
        trial_info['color_right'] = trial_info['low_prob_color']   
        trial_info['prob_left'] = trial_info['high_prob']
        trial_info['prob_right'] = 1-trial_info['high_prob']     
        trial_info['ev_left'] = trial_info['mag_left'] * reward_info['high_prob']
        trial_info['ev_right'] =trial_info['mag_right'] * (1-reward_info['high_prob'])
    
        if trial_info['color_right'] == trial_info['color1']:
            trial_info['prob1'] = 1-trial_info['high_prob']

    elif trial_info['high_prob_side'] == resp_keys[1]:
        leftColor = et.rgb2psypy(rgb_dict[trial_info['low_prob_color']])
        rightcolor = et.rgb2psypy(rgb_dict[trial_info['high_prob_color']])
        trial_info['color_left'] = trial_info['low_prob_color']
        trial_info['color_right'] = trial_info['high_prob_color'] 
        trial_info['prob_left'] = 1-trial_info['high_prob']
        trial_info['prob_right'] = trial_info['high_prob'] 
        trial_info['ev_left'] = trial_info['mag_left'] * (1-reward_info['high_prob'])
        trial_info['ev_right'] =trial_info['mag_right'] * reward_info['high_prob']
 
        if trial_info['color_left'] == trial_info['color1']:
            trial_info['prob1'] = 1-trial_info['high_prob']

    # define correct responses
    trial_info['ev_corr_resp'] = resp_keys[int(trial_info['ev_left']<trial_info['ev_right'])]
    trial_info['prob_corr_resp'] = resp_keys[int(trial_info['prob_left']<trial_info['prob_right'])]
    trial_info['mag_corr_resp'] = resp_keys[int(trial_info['mag_left']<=trial_info['mag_right'])]

    # define option-based variables (regardless of side), useful for RL models/regressions
    # where is option 1/2
    trial_info['prob2'] = 1-trial_info['prob1']
    if trial_info['color_left']==trial_info['color1']:
        trial_info['position2'] = 'right'
        trial_info['mag2'] = trial_info['mag_right']
    else:
        trial_info['position1'] = 'right'
        trial_info['mag1'] = trial_info['mag_right']

    trial_info['ev1'] = trial_info['mag1']*trial_info['prob1']
    trial_info['ev2'] = trial_info['mag2']*trial_info['prob2']

    # what is the outcome of option 1/2
    if trial_info['high_prob_color']==trial_info['color1']:
        trial_info['outcome1']=int(trial_info['reward_validity']=='valid')
    elif trial_info['low_prob_color']==trial_info['color1']:
        trial_info['outcome1']=int(trial_info['reward_validity']=='invalid')
    trial_info['outcome2'] = trial_info['outcome1']^1
    
    if trial_info['prob_left']>trial_info['prob_right'] and trial_info['mag_left']>=trial_info['mag_right']:
        trial_info['no_brain'] = 1
    elif trial_info['prob_left']<trial_info['prob_right'] and trial_info['mag_left']<trial_info['mag_right']:
        trial_info['no_brain'] = 1
    else:
        trial_info['no_brain'] = 0

    # set dynamic stimulus features for the upcoming trial
    rightbar.fillColor = rightcolor
    rightframe.lineColor = rightcolor
    leftbar.fillColor = leftColor
    leftframe.lineColor = leftColor 
    leftbar.pos=[-stim_info['bar_x'],stim_info['bar_y']-0.5*stim_info['bar_height']+0.05*stim_info['bar_height']*trial_info['mag_left']]
    leftbar.height=0.1*stim_info['bar_height']*trial_info['mag_left']
    rightbar.pos=[stim_info['bar_x'],stim_info['bar_y']-0.5*stim_info['bar_height']+0.05*stim_info['bar_height']*trial_info['mag_right']]
    rightbar.height=0.1*stim_info['bar_height']* trial_info['mag_right']

    # check whether a button in the response box is currently pressed & present a warning if so
    t0 = core.getTime()
    while captureResponse(port,keys=resp_keys+[None]) in resp_keys:
        if core.getTime()-t0>1.0:
            et.drawFlip(win,[warning]) 

    ##########################
    ###  FIXATION PHASE    ###
    ##########################    
    win.logOnFlip(level=logging.INFO, msg='start_fix\t{}\t{}'.format(trial_info['trial_no'],fix_seq[trial_no]))
    win.callOnFlip(et.sendTriggers,port,trigger_info['start_trial'])
    for frame in range(fix_frames_seq[trial_no]):
        if frame == 5:
            win.callOnFlip(et.sendTriggers,port,0)
        et.drawFlip(win,fix_phase) 
 
    ##########################
    ###  STIMULUS PHASE    ###
    ##########################    
    event.clearEvents()
    win.logOnFlip(level=logging.INFO, msg='start_stim\t{}'.format(trial_info['trial_no']))
    win.callOnFlip(et.sendTriggers,port,trigger_info['start_stim']) 
    for frame in range(resp_frames): 
        # reset trigger
        if frame == 5:
            win.callOnFlip(et.sendTriggers,port,0)
        # show stim
        if frame==resp_frames-1:
            et.drawFlip(win,fix_phase) 
        elif frame==0:
            start_stim_time = et.drawFlip(win,stim_phase) 
        else:
            et.drawFlip(win,stim_phase) 

        #sample response
        if response_info['run_mode']=='dummy':
            trial_info['resp_key'] = np.random.choice(resp_keys+[None]*resp_frames)
        else:
            trial_info['resp_key'] = captureResponse(port,keys=resp_keys)

        # break if responded
        if trial_info['resp_key'] in resp_keys:
            break  

    ##########################
    ###  POST PROCESSING   ###
    ##########################
    # start handling response variables        
    trial_info['resp_time'] = core.getTime()-start_stim_time
    trial_info['ev_correct'] = int(trial_info['resp_key']==trial_info['ev_corr_resp'])
    trial_info['prob_correct'] = int(trial_info['resp_key']==trial_info['prob_corr_resp'])
    trial_info['mag_correct'] = int(trial_info['resp_key']==trial_info['mag_corr_resp'])
    block_correct += trial_info['ev_correct']
    if trial_info['resp_key'] == resp_keys[0]:
        trial_info['choice'] = 1+(trial_info['color_left'] == trial_info['color2'])
        trial_info['choice_side'] = 0
    elif trial_info['resp_key'] == resp_keys[1]:
        trial_info['choice'] = 1+(trial_info['color_right'] == trial_info['color2'])
        trial_info['choice_side'] = 1

    # set the location of selection box
    if trial_info['resp_key'] == resp_keys[0]:
        selectbar.pos = [-stim_info['bar_x'],stim_info['bar_y']]
    elif trial_info['resp_key'] == resp_keys[1]:
        selectbar.pos = [stim_info['bar_x'],stim_info['bar_y']]
    
    ##########################
    ###  SELECTION PHASE   ###
    ##########################    
    if trial_info['resp_key'] in resp_keys:
        win.logOnFlip(level=logging.INFO, msg='start_select\t{}\t{}'.format(trial_info['trial_no'],select_seq[trial_no])) 
        for frame in range(select_frames_seq[trial_no]):
            et.drawFlip(win,select_phase)
    else:
        trial_info['timeout'] = 1
        win.logOnFlip(level=logging.INFO, msg='start_timeout\t{}'.format(trial_info['trial_no']))
        win.callOnFlip(et.sendTriggers,port,trigger_info['timeout'],prePad=0.012)
        for frame in range(select_frames_seq[trial_no]):
            if frame == 5:
                win.callOnFlip(et.sendTriggers,port,0)
            et.drawFlip(win,[timeout_screen])

    # handle reward
    if trial_info['high_prob_side']==resp_keys[0]:
        if trial_info['reward_validity']=='valid' and trial_info['resp_key'] == resp_keys[0]: 
            trial_info['reward']= trial_info['mag_left']
        elif trial_info['reward_validity']=='invalid' and trial_info['resp_key'] == resp_keys[1]: 
            trial_info['reward']= trial_info['mag_right']
    elif trial_info['high_prob_side']==resp_keys[1]:
        if trial_info['reward_validity'] =='valid' and trial_info['resp_key'] == resp_keys[1]: 
            trial_info['reward']= trial_info['mag_right']
        elif trial_info['reward_validity']=='invalid' and trial_info['resp_key'] == resp_keys[0]: 
            trial_info['reward']= trial_info['mag_left']
    prev_reward = trial_info['reward']

    ##########################
    ###  FEEDBACK PHASE    ###
    ########################## 
    if trial_info['reward']:   
        feedback = smiley
        progress_update.width = reward_info['conv_factor']*trial_info['reward']
        progress_update.pos[0] = progress_bar.pos[0]+progress_bar.width/2 + progress_update.width/2
        progress_bar.width+=progress_update.width
        progress_bar.pos[0]+=progress_update.width/2
        if progress_bar.width > 2*bar['horiz_dist']:
            progress_bar.width=0
            progress_bar.pos[0] = -bar['horiz_dist']  
            progress_update.pos[0] = progress_bar.pos[0]+progress_bar.width/2
            total_points+=200          
    else:
        feedback = frowny

    # show it
    if not trial_info['timeout']:
        win.logOnFlip(level=logging.INFO, msg='start_feed\t{}'.format(trial_info['trial_no']))
        win.callOnFlip(et.sendTriggers,port,trigger_info['start_feed'])
        for frame in range(feed_frames):
            if frame == 5:
                win.callOnFlip(et.sendTriggers,port,0)
            et.drawFlip(win,feedback_phase+ [feedback])    

    ##########################
    ###  LOGGING  PHASE    ###
    ##########################
    win.logOnFlip(level=logging.INFO, msg='end_trial\t{}'.format(trial_info['trial_no']))
    et.drawFlip(win,fix_phase)
    
    if trial_info['trial_no'] == 1:
        data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['log_order'])
    data_logger.writeTrial(trial_info)

    # interrupt experiment if there is a pause
    if trial_info['trial_no'] in pause_seq:
        # show text at the end of a block 
        endBlock.text = stim_info["endBlock_text"].format(trial_info['block_no'],total_points)
        win.logOnFlip(level=logging.INFO, msg='end_block\t{}'.format(trial_info['block_no']))    
        for frame in range(pause_frames):
            et.drawFlip(win,[endBlock])

# end of experiment message
performance = int(100*block_correct/trial_info['trial_no'])   
if trial_info['ses_id'] == 'prac': 
    if performance>55:
        endExp.text = endExp.text.format(str(performance)+'% korrekt. Gut gemacht!','Das Experiment kann jetzt beginnen.')
    else:
        endExp.text = endExp.text.format(str(performance)+'% korrekt.','Bitte wiederhole die Übung.')
else:
    endExp.text = stim_info["endExp_text"].format(total_points)
while 'q' not in event.getKeys():
    et.drawFlip(win,[endExp])    

# clean up
et.finishExperiment(win,data_logger,show_results=True)  