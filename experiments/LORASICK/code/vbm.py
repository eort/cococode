# created by Eduard Ort, 2019 

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

#######################################
###          LOAD CONFIG FILE     #####
#######################################
try:
    jsonfile = sys.argv[1]
except IndexError as e:
    logging.warning("No config file provided. Stop it here.")
    sys.exit(-1)
try:
    with open(jsonfile) as f:    
        param = json.load(f)
except FileNotFoundError as e:
    logging.warning("{} is not a valid config file. Stop it here.".format(jsonfile))
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
bar = stim_info['progress_bar']                   # trigger for defined events

###########################################
###         HANDLE INPUT DIALOG        ####
###########################################
# dialog with participants: Retrieve Subject number, session number, and practice
input_dict = dict(sub_id=0,sess_id=0)
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','sess_id'])
# check for input
if inputGUI.OK == False:
    logging.warning("Experiment aborted by user")
    core.quit()
while input_dict['sess_id'] not in list(range(1,param['n_sess']+1))+['prac','scr']:
    logging.warning('WARNING: You need to specify a session number in the range {}'.format(list(range(1,param['n_sess']+1))))
    inputGUI.show()
    if inputGUI.OK == False:
        logging.warning("Experiment aborted by user")
        core.quit()

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
logFileID = logging_info['skeleton_file'].format(input_dict['sub_id'],input_dict['sess_id'],param['name'],str(datetime.now()).replace(' ','-').replace(':','-'))
log_file = os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.log').format(input_dict['sub_id'],input_dict['sess_id'],'log')
# create a output file that collects all variables 
output_file = os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.csv').format(input_dict['sub_id'],input_dict['sess_id'],'beh')
# save the current settings per session, so that the data files stay slim
settings_file=os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.json').format(input_dict['sub_id'],input_dict['sess_id'],'settings')
for f in [log_file,output_file,settings_file]:
    if not os.path.exists(os.path.dirname(f)): 
        os.makedirs(os.path.dirname(f))
os.system('cp {} {}'.format(jsonfile,f))
lastLog = logging.LogFile(log_file, level=logging.INFO, filemode='w')

# init logger:  update the constant values (things that wont change)
trial_info = {"sub_id":input_dict['sub_id'],
                "sess_id":input_dict['sess_id'],
                'total_points':0,
                'trial_count':0,
                'logFileID':logFileID}
# add variables to the logfile that are defined in config file
for vari in logging_info['logVars']:
    trial_info[vari] = param[vari]

###########################################
###  PREPARE EXPERIMENTAL SEQUENCE     ####
###########################################

# load sequence info
sequence = pd.read_csv(param['sequence'])
sequence.prob1 = 100*sequence.prob1
sequence.prob2 = 100*sequence.prob2
# shuffle
sequence = sequence.sample(frac=1).reset_index(drop=True)
# response
resp_keys = [response_info['resp_left'],response_info['resp_right']]

####################
###  SET TIMING  ###
####################
# convert timing to frames
pause_frames = round(timing_info['pause_dur']*win_info['framerate'])
feed_frames = round(timing_info['feed_dur']*win_info['framerate'])
resp_frames = round(timing_info['resp_dur']*win_info['framerate'])
# make a sequence of fix-stim jitter
fix_seq = np.random.uniform(timing_info['fix_mean']-timing_info['fix_range'],timing_info['fix_mean']+timing_info['fix_range'], size=(n_blocks,n_trials))
fix_frames_seq = (fix_seq*win_info['framerate']).round().astype(int)
select_seq = np.random.uniform(timing_info['select_mean']-timing_info['select_range'],timing_info['select_mean']+timing_info['select_range'], size=(n_blocks,n_trials))
select_frames_seq = (select_seq*win_info['framerate']).round().astype(int)

##################################
###      MAKE STIMULI          ###
##################################
mon = monitors.Monitor('cocoLab',width = win_info['screen_width'],distance = win_info['screen_distance'])
mon.setSizePix(win_info['win_size'])
win=visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscr'],units="deg",autoLog=0,monitor=mon)

# and text stuff
startBlock = visual.TextStim(win,text=stim_info['startBlock_text'],color=win_info['fg_color'],height=0.35,autoLog=0)
endBlock = visual.TextStim(win,text=stim_info['endBlock_text'],color=win_info['fg_color'],autoLog=0,height=0.35)
endExp = visual.TextStim(win,text=stim_info['endExp_text'],color=win_info['fg_color'],autoLog=0,height=0.35)
warning = visual.TextStim(win,text=stim_info["warning"],color='white',autoLog=0,height=0.35)
timeout_screen = visual.TextStim(win,text='Zu langsam!',color='white',height=0.35,autoLog=0)
# and stimuli
progress_bar =visual.Rect(win,height=bar['height'],width=bar['width'],lineColor=None,fillColor=bar['color'],pos=[-bar['horiz_dist'],-bar['vert_dist']],autoLog=0)
progress_update =visual.Rect(win,height=bar['height'],width=0,lineColor=None,fillColor=bar['color'],autoLog=0,pos=(-bar['horiz_dist'],-bar['vert_dist']))
progress_bar_start=visual.Rect(win,width=bar['width'],height=bar['height'],lineColor=None,fillColor=bar['color'],pos = [-bar['horiz_dist'],-bar['vert_dist']],autoLog=0)
progress_bar_end =visual.Rect(win,width=bar['width'],height=bar['height'],lineColor=None,fillColor=bar['color'],pos = [bar['horiz_dist'],-bar['vert_dist']],autoLog=0)
fixDot = et.fancyFixDot(win, bg_color = win_info['bg_color']) 
leftframe = visual.Rect(win,width=stim_info['bar_width'],height=stim_info['bar_height'],lineColor=win_info['fg_color'],fillColor=None,pos = [-stim_info['bar_x'],stim_info['bar_y']],autoLog=0)
rightframe = visual.Rect(win,width=stim_info['bar_width'],height=stim_info['bar_height'],lineColor=win_info['fg_color'],fillColor=None,pos = [stim_info['bar_x'],stim_info['bar_y']],autoLog=0)
leftbar = visual.Rect(win,width=stim_info['bar_width'],lineColor=None,fillColor=win_info['fg_color'],autoLog=0)
rightbar = visual.Rect(win,width=stim_info['bar_width'],lineColor=None,fillColor=win_info['fg_color'],autoLog=0)
selectbar = visual.Rect(win,width=stim_info['bar_width']*1.7,height=stim_info['bar_height']*1.7,lineColor=win_info['fg_color'],fillColor=None,autoLog=0)
leftProb = visual.TextStim(win,height=0.4,color=win_info['fg_color'],pos=[-stim_info['bar_x'],-0.8*stim_info['bar_height']+stim_info['bar_y']],autoLog=0)
rightProb = visual.TextStim(win,height=0.4,color=win_info['fg_color'],pos=[stim_info['bar_x'],-0.8*stim_info['bar_height']+stim_info['bar_y']],autoLog=0)

# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()

# reset all triggers to zero
et.sendTriggers(port,0)

# experimental phases (unique things on screen)
fix_phase = fixDot[:] +[progress_bar,progress_bar_start,progress_bar_end]
stim_phase = fixDot[:] + [progress_bar,progress_bar_start,progress_bar_end,leftframe,rightframe,leftbar,rightbar,leftProb,rightProb]
select_phase = fixDot[:] +[progress_bar,progress_bar_start,progress_bar_end,selectbar,rightframe,leftframe,leftbar,rightbar,leftProb,rightProb]
feedback_phase = fixDot[:] +[progress_bar,progress_bar_start,progress_bar_end,progress_update,selectbar,rightframe,leftframe,leftbar,rightbar,leftProb,rightProb]

######################
###  START BLOCKS  ###
######################
for block_no in range(n_blocks):
    trial_info['block_no']=block_no+1
    
    # start block message
    startBlock.text = stim_info["startBlock_text"].format(block_no+1, n_blocks)
    while True:
        et.drawFlip(win,[startBlock])                
        cont=captureResponse(port,keys = [response_info['pause_resp'],None])    
        if cont == response_info['pause_resp']:            
            while captureResponse(port,keys=resp_keys+ [None]) in resp_keys:
                win.flip()
            win.callOnFlip(et.sendTriggers,port,trigger_info['start_block'],reset=0.5)
            win.logOnFlip(level=logging.INFO, msg='start_block\t{}'.format(trial_info['block_no']))
            win.flip()
            break
        
    ####################
    ###  trial loop  ###
    ####################
    for trial_no in range(n_trials):
        # force quite experiment
        escape = event.getKeys()
        if 'q' in escape:
            et.finishExperiment(win,data_logger)

        # reset variables
        trial_info['reward']=0
        response =None
        trial_info['timeout'] = 0
        leftbar.fillColor = win_info['fg_color']
        rightbar.fillColor = win_info['fg_color']

        # set trial variables
        trial_info['trial_no'] = trial_no+1
        trial_info['fix_dur'] = fix_seq[block_no,trial_no]
        trial_info['select_dur'] = select_seq[block_no,trial_no]
        trial_info['corr_resp'] = resp_keys[int((sequence.iloc[trial_info['trial_count']].CorrectLeftRight)-1)]
        trial_info['mag_left'] = sequence.iloc[trial_info['trial_count']].mag1
        trial_info['mag_right']= sequence.iloc[trial_info['trial_count']].mag2
        trial_info['prob_left'] = sequence.iloc[trial_info['trial_count']].prob1
        trial_info['prob_right'] = sequence.iloc[trial_info['trial_count']].prob2
        trial_info['rew_left'] = sequence.iloc[trial_info['trial_count']].fb1
        trial_info['rew_right'] = sequence.iloc[trial_info['trial_count']].fb2
        trial_info['ev_left'] = sequence.iloc[trial_info['trial_count']].ev1
        trial_info['ev_right'] = sequence.iloc[trial_info['trial_count']].ev2
        trial_info['nb'] = sequence.iloc[trial_info['trial_count']]['Nb']
        trial_info['corrSM'] = sequence.iloc[trial_info['trial_count']].CorrectLeftRight
        trial_info['trial_count']+=1
        fix_frames = fix_frames_seq[block_no,trial_no]
        select_frames = select_frames_seq[block_no,trial_no]

        # set stimulus
        leftbar.height = 0.1*stim_info['bar_height']*trial_info['mag_left']
        leftbar.pos=[-stim_info['bar_x'],stim_info['bar_y']-0.5*stim_info['bar_height']+0.05*stim_info['bar_height']*trial_info['mag_left']]
        rightbar.height =0.1*stim_info['bar_height']* trial_info['mag_right']
        rightbar.pos=[stim_info['bar_x'],stim_info['bar_y']-0.5*stim_info['bar_height']+0.05*stim_info['bar_height']*trial_info['mag_right']]
        leftProb.text =  '{:02d}%'.format(int(trial_info['prob_left']))
        rightProb.text = '{:02d}%'.format(int(trial_info['prob_right']))

        # check whether a button in the response box is currently pressed & present a warning if so
        t0 = core.getTime()
        if response_info['resp_mode']=='meg':
            while captureResponse(port,keys=resp_keys) in resp_keys:
                if core.getTime()-t0>1.0:
                    et.drawFlip(win,[warning]) 
        
        ##########################
        ###  FIXATION PHASE    ###
        ########################## 
        win.logOnFlip(level=logging.INFO, msg='start_fix\t{}\t{}'.format(trial_info['trial_count'],trial_info['fix_dur']))
        win.callOnFlip(et.sendTriggers,port,trigger_info['start_trial']) 
        for frame in range(fix_frames):
            if frame == 5:
                win.callOnFlip(et.sendTriggers,port,0)
            et.drawFlip(win,fix_phase) 
              
        ##########################
        ###  STIMULUS PHASE    ###
        ##########################
        event.clearEvents()
        win.logOnFlip(level=logging.INFO, msg='start_stim\t{}'.format(trial_info['trial_count']))
        win.callOnFlip(et.sendTriggers,port,trigger_info['start_stim']) 
        for frame in range(resp_frames): 
            # reset trigger
            if frame == 5:
                win.callOnFlip(et.sendTriggers,port,0)
            # show stim
            if frame==resp_frames-1:
                et.drawFlip(win,fix_phase) 
            elif frame ==0:
                trial_info['start_stim_time'] = et.drawFlip(win,stim_phase) 
            else:
                et.drawFlip(win,stim_phase) 

            #sample response
            if response_info['run_mode']=='dummy':
                response = np.random.choice(resp_keys + [None]*resp_frames)
            else:
                response = captureResponse(port,keys=resp_keys)

            # break if responded
            if response in resp_keys:
                break  

        if frame == resp_frames-1:
            trial_info['timeout'] = 1

        ##########################
        ###  POST PROCESSING   ###
        ##########################
        # start handling response variables        
        trial_info['resp_time'] = core.getTime()-trial_info['start_stim_time']
        trial_info['resp_key'] = response
        trial_info['correct'] = int(response==trial_info['corr_resp'])
        
        # define incremental reward value and define selection box
        if trial_info['resp_key'] == resp_keys[0]:
            selectbar.pos = [-stim_info['bar_x'],stim_info['bar_y']-0.2*stim_info['bar_height']]
            if trial_info['rew_left']:
                trial_info['reward'] = int(trial_info['mag_left'] *trial_info['rew_left'])
        elif trial_info['resp_key'] == resp_keys[1]:
            selectbar.pos = [stim_info['bar_x'],stim_info['bar_y']-0.2*stim_info['bar_height']]
            if trial_info['rew_right']:
                trial_info['reward'] = int(trial_info['mag_right'] *trial_info['rew_right'])

        # draw selection phase if response given
        if not trial_info['timeout']:
            win.logOnFlip(level=logging.INFO, msg='start_select\t{}\t{}'.format(trial_info['trial_count'],trial_info['select_dur']))
            for frame in range(select_frames):
                et.drawFlip(win,select_phase)
        elif trial_info['timeout']:
            win.logOnFlip(level=logging.INFO, msg='start_timeout\t{}'.format(trial_info['trial_count']))
            win.callOnFlip(et.sendTriggers,port,trigger_info['timeout'],prePad=0.012)
            for frame in range(select_frames):
                if frame == 5:
                    win.callOnFlip(et.sendTriggers,port,0)
                et.drawFlip(win,[timeout_screen])
        
        # show update bar
        if trial_info['reward']:   
            progress_update.width = param['conv_factor']*trial_info['reward']
            progress_update.pos[0] = progress_bar.pos[0]+progress_bar.width/2 + progress_update.width/2
            progress_bar.width+=progress_update.width
            progress_bar.pos[0]+=progress_update.width/2
            if progress_bar.width > 2*bar['horiz_dist']:
                progress_bar.width=0
                progress_bar.pos[0] = -bar['horiz_dist']  
                progress_update.pos[0] = progress_bar.pos[0]+progress_bar.width/2
                trial_info['total_points']+=200          

        # draw feedback_phase 
        if trial_info['rew_left'] == 1:
            leftbar.fillColor = bar['corr_color']
        else:
            leftbar.fillColor = bar['incorr_color']
        if trial_info['rew_right'] == 1:
            rightbar.fillColor = bar['corr_color']
        else:
            rightbar.fillColor = bar['incorr_color']
 
        if trial_info['timeout'] ==0:    
            win.logOnFlip(level=logging.INFO, msg='start_feed\t{}'.format(trial_info['trial_count']))
            win.callOnFlip(et.sendTriggers,port,trigger_info['start_feed'])
            for frame in range(feed_frames):
                if frame == 5:
                    win.callOnFlip(et.sendTriggers,port,0)
                et.drawFlip(win,feedback_phase)
        
        ##########################
        ###  LOGGING  PHASE    ###
        ##########################
        win.logOnFlip(level=logging.INFO, msg='end_trial\t{}'.format(trial_info['trial_no']))
        et.drawFlip(win,fix_phase)

        if trial_info['trial_count'] == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['first_columns'])
        data_logger.writeTrial(trial_info)

    # end of block message
    if trial_info['block_no'] !=n_blocks:
        endBlock.text = stim_info["endBlock_text"].format(block_no+1,trial_info['total_points'])
        win.logOnFlip(level=logging.INFO, msg='end_block\t{}'.format(trial_info['block_no']))  
        for frame in range(pause_frames):
            et.drawFlip(win,[endBlock])
    
    # clear any pending key presses
    event.clearEvents()

# end of experiment message
endExp.text = stim_info["endExp_text"].format(trial_info['total_points'])
while et.captureResponseKB(port,keys = ['q']) != 'q':
    et.drawFlip(win,[endExp])

#cleanup
et.finishExperiment(win,data_logger,show_results=logging_info['show_results'])