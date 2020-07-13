# created by Eduard Ort, 2020

##########################
###  IMPORT LIBRARIES  ###
##########################
from psychopy import visual, core, event,gui,logging #import some libraries from PsychoPy
import expTools as et # custom scripts
import json # to load configuration files
import sys, os # to interact with the operating system
from datetime import datetime # to get the current time
import numpy as np # to do fancy math shit
import glob # to search in system efficiently
import pandas as pd # efficient table operations
import itertools as it # doing some combinatorics

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
reward_info=param['reward_info']                  # Information on the reward schedule
logging_info=param['logging_info']                # information on files and variables for logging
trigger_info = param['trigger_info']              # information on all the MEG trigger values and names
n_trials = param['n_trials']                      # number trials per block
n_blocks = param['n_blocks']                      # number total blocks
sess_type = param['sess_type']                    # are we practicing or not
bar = stim_info['progress_bar']                   # make drawing the progressbar less of a pain

###########################################
###         HANDLE INPUT DIALOG        ####
###########################################
# dialog with participants: Retrieve Subject number, session number, and practice
input_dict = dict(sub_id=0,sess_id=0,sess_type=sess_type)
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','sess_id','sess_type'])
# check  input
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
# save the current settings per session, so that the data files stay slim
settings_file = os.path.join('settings',param['exp_id'],logFileID+'.json')
for f in [settings_file,output_file,log_file]:
    if not os.path.exists(os.path.dirname(f)): 
        os.makedirs(os.path.dirname(f))
os.system('cp {} {}'.format(jsonfile,settings_file))
lastLog = logging.LogFile(log_file, level=logging.INFO, filemode='w')

# init logger:  update the constant values (things that wont change)
trial_info = {"sub_id":input_dict['sub_id'],
                "sess_id":input_dict['sess_id'],
                "sess_type":input_dict['sess_type'],
                'total_points':0,
                'block_no':0,
                'pause_no':0,
                'logFileID':logFileID,
                "start_exp_time":core.getTime(),
                "end_block_time":np.nan}
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

# select colors from predefined options based on sub id
if trial_info['sess_type']!='screening':
    color_idx = [(x,y,z) for (x,y,z) in it.product(range(3),range(3),range(3)) if x!=y and y!=z and x!=z][trial_info['sub_id']%6]
    colors = stim_info['color_combinations'][color_idx[trial_info['sess_id']-1]]
else:
    colors = stim_info['color_combinations'][0]
np.random.shuffle(colors)

# counterbalance the order of volatile and stable blocks across subs and sessions
block_type_order = ['sv','vs'][trial_info['sub_id']%2] # (v)olatile, (s)table
np.random.shuffle(param['volatile_blocks'])
if block_type_order == 'sv':
    block_types = ['stable']+['volatile']*round(len(param['volatile_blocks']))
    blocks = param['stable_blocks']+ param['volatile_blocks']
else:
    block_types = ['volatile']*round(len(param['volatile_blocks']))+['stable']
    blocks = param['volatile_blocks']+param['stable_blocks']

# create building blocks of possible location/validity combinations 
# currently it only works with 80-20%. Having 75 oder 70 will require reprogramming to allow for perfectly balanced trials
# proper ratio of valid and invalid trials (highlikely color will bring reward)
reward_ratio = np.array([1]*round(reward_info['high_prob']*5)+[0]*round((1-reward_info['high_prob'])*5))
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
    np.random.shuffle(reward_info['mags'])
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
# alternating between target colors across blocks
color_seq = [colors, colors[::-1]]*round(len(block_types)/2)
# define sequence when a block switch should occur
change_seq = np.cumsum(pd.Series(blocks).shift())
change_seq[0] = 0

# 0,1 target is on left, 2,3 target is on right
target_side_seq = [resp_keys[0] if i in [0,1] else resp_keys[1] for i in trial_seq]
# 0, 2 the high likely target won't get reward, 1,3 the high likely target will get reward
reward_validity_seq = ['valid' if i in [1,3] else 'invalid' for i in trial_seq]

####################
###  SET TIMING  ###
####################
fix_seq = np.random.uniform(timing_info['fix_mean']-timing_info['fix_range'],timing_info['fix_mean']+timing_info['fix_range'], size=trial_seq.shape)
select_seq = np.random.uniform(timing_info['select_mean']-timing_info['select_range'],timing_info['select_mean']+timing_info['select_range'], size=trial_seq.shape)
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
win = visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscreen'], units="pix",screen=1)

# and stimuli
startBlock = visual.TextStim(win,text=stim_info['startBlock_text'],color=win_info['fg_color'],wrapWidth=win.size[0])
endBlock = visual.TextStim(win,text= stim_info['endBlock_text'],color=win_info['fg_color'],wrapWidth=win.size[0])
endExp = visual.TextStim(win,text=stim_info['endExp_text'],color=win_info['fg_color'],wrapWidth=win.size[0])
progress_bar =visual.Rect(win,height=bar['height'],lineColor=None,fillColor=bar['color'],pos=[-bar['horiz_dist'],-bar['vert_dist']])
progress_update =visual.Rect(win,height=bar['height'],lineColor=None,fillColor=bar['color'])
progress_bar_start=visual.Rect(win,width=bar['width'],height=bar['height'],lineColor=None,fillColor=bar['color'],pos = [-bar['horiz_dist'],-bar['vert_dist']])
progress_bar_end =visual.Rect(win,width=bar['width'],height=bar['height'],lineColor=None,fillColor=bar['color'],pos = [bar['horiz_dist'],-bar['vert_dist']])
fixDot = et.fancyFixDot(win, bg_color = win_info['bg_color'],size=18) 
leftbox = visual.Rect(win,width=stim_info['box_edge'],height=stim_info['box_edge'],lineColor=win_info['bg_color'],pos = [-stim_info['box_x'],stim_info['box_y']])
rightbox = visual.Rect(win,width=stim_info['box_edge'],height=stim_info['box_edge'],lineColor=win_info['bg_color'],pos = [stim_info['box_x'],stim_info['box_y']])
selectbox = visual.Rect(win,width=stim_info['box_edge']*1.25,height=stim_info['box_edge']*1.25,lineColor=win_info['fg_color'],lineWidth=stim_info['lineWidth'])
leftMag = visual.TextStim(win,color=win_info['fg_color'],pos=[-stim_info['box_x'],stim_info['box_y']])
rightMag = visual.TextStim(win,color=win_info['fg_color'],pos=[stim_info['box_x'],stim_info['box_y']])
timeout_screen = visual.TextStim(win,text='Zu langsam!',color='white',wrapWidth=win.size[0])
smiley = visual.ImageStim(win,'smiley.png',contrast=-1,size=[stim_info['box_edge']-10,stim_info['box_edge']-10]) # good feedback
frowny = visual.ImageStim(win,'frowny.png',contrast=-1,size=[stim_info['box_edge']-10,stim_info['box_edge']-10]) # bad feedback

# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()

# experimental phases (unique things on screen)
fix_phase = fixDot[:] +[progress_bar,progress_bar_start,progress_bar_end]
stim_phase = fixDot[:] + [progress_bar,progress_bar_start,progress_bar_end,leftbox,rightbox,leftMag,rightMag]
select_phase = fixDot[:] +[progress_bar,progress_bar_start,progress_bar_end,selectbox,leftbox,rightbox,leftMag,rightMag]
feedback_phase = [progress_bar,progress_bar_start,progress_bar_end,progress_update,selectbox,leftbox,rightbox,leftMag,rightMag]
timeout_phase = [progress_bar,progress_bar_start,progress_bar_end,timeout_screen]

######################
###  START TRIALS  ###
######################

for trial_no in range(trial_seq.shape[0]):
    # set Block variables every time a context change occurred
    if trial_no in change_seq.values:
        trial_info['block_type'] = block_types[trial_info['block_no']]
        trial_info['block_length'] = blocks[trial_info['block_no']]
        high_prob_color = color_seq[trial_info['block_no']][0]
        low_prob_color = color_seq[trial_info['block_no']][1]
        trial_info['block_no'] += 1

    # start block message  
    if trial_no in pause_seq:
        # reset block variables
        trial_info['pause_no'] += 1     
        if response_info['run_mode'] != 'dummy':
            while True:
                startBlock.text = stim_info["startBlock_text"].format(trial_info['pause_no'])
                startBlock.draw()
                trial_info['start_block_time'] = win.flip()                        
                cont=et.captureResponse(mode=response_info['resp_mode'],keys = [response_info['pause_resp']])    
                if cont == response_info['pause_resp']:
                    break
            et.sendTriggers(trigger_info['start_block'],mode=response_info['resp_mode'],prePad=0.01)

    # force quite experiment
    escape = event.getKeys()
    if 'q' in escape:
        et.finishExperiment(win,data_logger)

    # reset variables
    reward=0
    response =None
    #selectbox.lineColor = win_info['fg_color'] # remove if we use smileys
    # set trial variables
    trial_info['corr_resp'] = target_side_seq[trial_no]
    trial_info['trial_no'] = trial_no+1
    trial_info['fix_dur'] = fix_seq[trial_no]
    trial_info['select_dur'] = select_seq[trial_no]
    trial_info['mag_left'] = magn_seq[trial_no][0]
    trial_info['mag_right'] = magn_seq[trial_no][1]
    trial_info['high_prob_side'] = target_side_seq[trial_no]
    trial_info['reward_validity'] = reward_validity_seq[trial_no]

    # set stimulus   
    if trial_info['high_prob_side'] == 'left':
        rightbox.fillColor = rgb_dict[high_prob_color]
        leftbox.fillColor = rgb_dict[low_prob_color]
    else:
        rightbox.fillColor = rgb_dict[low_prob_color]
        leftbox.fillColor = rgb_dict[high_prob_color]
    leftMag.text ='{:d}'.format(int(trial_info['mag_left']))
    rightMag.text ='{:d}'.format(int(trial_info['mag_right']))

    ##########################
    ###  FIXATION PHASE    ###
    ##########################    
    et.drawCompositeStim(fix_phase)
    trial_info['start_trial_time']=win.flip()
    et.sendTriggers(trigger_info['start_trial'],mode=response_info['resp_mode'])          
    for frame in range(fix_frames_seq[trial_no]):
        et.drawCompositeStim(fix_phase)
        trial_info['start_stim_time']=win.flip()  
    trial_info['fixDur'] =  trial_info['start_stim_time']-trial_info['start_trial_time']
    # clear any pending key presses
    event.clearEvents()

    # choose a random response frame if response mode is dummy     
    if response_info['run_mode']=='dummy':
        dummy_resp_frame = np.random.choice(range(resp_frames+20))

    ##########################
    ###  STIMULUS PHASE    ###
    ##########################    
    et.drawCompositeStim(stim_phase) 
    # start response time measure
    trial_info['start_stim_time'] = win.flip() 
    et.sendTriggers(trigger_info['start_stim'],mode=response_info['resp_mode'])   
    for frame in range(resp_frames):        
        if frame==resp_frames:
            et.drawCompositeStim(fix_phase)
        else:
            et.drawCompositeStim(stim_phase)
        trial_info['end_stim_time'] = win.flip()

        #sample response
        if response_info['run_mode']=='dummy':
            if dummy_resp_frame == frame:
                response = np.random.choice(resp_keys)
        else:
            response = et.captureResponse(mode=response_info['resp_mode'],keys=resp_keys)

        # break if responded
        if response in resp_keys:
            break  

    ##########################
    ###  POST PROCESSING   ###
    ##########################
    # start handling response variables        
    trial_info['start_select_time'] = core.getTime()
    trial_info['resp_time'] = trial_info['start_select_time']-trial_info['start_stim_time']
    trial_info['resp_key'] = response
    trial_info['correct'] = int(response==trial_info['corr_resp'])

    # set the location of selection box
    if trial_info['resp_key'] == resp_keys[0]:
        selectbox.pos = [-stim_info['box_x'],stim_info['box_y']]
    elif trial_info['resp_key'] == resp_keys[1]:
        selectbox.pos = [stim_info['box_x'],stim_info['box_y']]
    
    ##########################
    ###  SELECTION PHASE   ###
    ##########################    
    if response in resp_keys:
        trial_info['timeout'] = 0
        et.drawCompositeStim(select_phase)
        trial_info['start_select_time'] = win.flip()  
        #et.sendTriggers(trigger_info['start_select'],mode=response_info['resp_mode'])
        for frame in range(select_frames_seq[trial_no]):
            et.drawCompositeStim(select_phase)
            trial_info['end_select_time'] = win.flip()  
    else:
        trial_info['timeout'] = 1
        et.drawCompositeStim(timeout_phase)
        trial_info['start_select_time'] = win.flip()
        et.sendTriggers(trigger_info['timeout'],mode=response_info['resp_mode'],prePad=0.01)   
        for frame in range(select_frames_seq[trial_no]-1):
            et.drawCompositeStim(timeout_phase)
            trial_info['end_select_time'] = win.flip() 
    trial_info['selectDur'] =  trial_info['end_select_time']-trial_info['start_select_time']

    # handle reward
    if trial_info['high_prob_side']==resp_keys[0]:
        if trial_info['reward_validity']=='valid' and trial_info['resp_key'] == resp_keys[0]: 
            reward = trial_info['mag_left']
        elif trial_info['reward_validity']=='invalid' and trial_info['resp_key'] == resp_keys[1]: 
            reward = trial_info['mag_right']
    elif trial_info['high_prob_side']==resp_keys[1]:
        if trial_info['reward_validity'] =='valid' and trial_info['resp_key'] == resp_keys[1]: 
            reward = trial_info['mag_right']
        elif trial_info['reward_validity']=='invalid' and trial_info['resp_key'] == resp_keys[0]: 
            reward = trial_info['mag_left']
    trial_info['reward'] = reward
    
    ##########################
    ###  FEEDBACK PHASE    ###
    ########################## 
    if reward:   
        progress_update.pos = (progress_bar.width + progress_bar_start.pos[0]- progress_bar_start.width/2+ 0.9*reward,progress_bar_start.pos[1])
        progress_update.width =1.8*reward
        progress_bar.width += 1.8*reward
        progress_bar.pos[0] += 0.9*reward
    if progress_bar.width > 2*bar['horiz_dist']:
        progress_bar.width=bar['width']
        progress_bar.pos[0] = -bar['horiz_dist']  
        progress_update.pos = (progress_bar.width + progress_bar_start.pos[0]- progress_bar_start.width/2+ 0.9*reward,progress_bar_start.pos[1])
        progress_update.width = 0   
        trial_info['total_points']+=200          

    # draw feedback_phase phase
    if reward != 0:
        feedback = smiley
    else:
        feedback = frowny

    trial_info['start_feed_time'] = core.getTime()
    if not trial_info['timeout']:
        et.drawCompositeStim(feedback_phase + [feedback])
        trial_info['start_feed_time'] = win.flip()
        et.sendTriggers(trigger_info['start_feed'],mode=response_info['resp_mode'])
        for frame in range(feed_frames):
            et.drawCompositeStim(feedback_phase+ [feedback])
            trial_info['end_trial_time'] = win.flip()
    trial_info['end_trial_time'] = core.getTime()

    ##########################
    ###  LOGGING  PHASE    ###
    ##########################

    if trial_info['trial_no'] == 1:
        data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['first_columns'])
    data_logger.writeTrial(trial_info)

    # interrupt experiment if there is a pause
    if trial_info['trial_no'] in pause_seq:
        # end of block message    
        if response_info['resp_mode']=='keyboard':
            event.clearEvents()
        # show text at the end of a block 
        if response_info['run_mode'] != 'dummy':      
            endBlock.text = stim_info["endBlock_text"].format(trial_info['pause_no'],trial_info['total_points'])
            for frame in range(pause_frames):
                endBlock.draw()
                win.flip() 
        # clear any pending key presses
        event.clearEvents()

# end of experiment message
if response_info['run_mode'] != 'dummy':
    endExp.text = stim_info["endExp_text"].format(trial_info['total_points'])
    while True:
        endExp.draw()
        win.flip()
        cont=et.captureResponse(mode=response_info['resp_mode'],keys = [response_info['pause_resp']])    
        if cont == response_info['pause_resp']:
            break
#cleanup
et.finishExperiment(win,data_logger,show_results=True)