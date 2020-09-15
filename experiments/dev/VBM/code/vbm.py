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
bar = stim_info['progress_bar']                   # trigger for defined events

###########################################
###         HANDLE INPUT DIALOG        ####
###########################################
# dialog with participants: Retrieve Subject number, session number
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
for f in [log_file,output_file,settings_file]:
    os.makedirs(os.path.dirname(f), exist_ok=True)
os.system('cp {} {}'.format(jsonfile,settings_file))
lastLog = logging.LogFile(log_file, level=logging.INFO, filemode='w')

# init logger:  update the constant values (things that wont change)
trial_info = {"sub_id":input_dict['sub_id'],
                "ses_id":input_dict['ses_id'],
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
total_points = 0
trial_count=0
####################
###  SET TIMING  ###
####################
# convert timing to frames
pause_frames = round(timing_info['pause_dur']*win_info['framerate'])
feed_frames = round(timing_info['feed_dur']*win_info['framerate'])
resp_frames = round(timing_info['resp_dur']*win_info['framerate'])
# make a sequence of fix-stim jitter
fix_seq = np.random.uniform(timing_info['fix_mean']-timing_info['fix_range'],timing_info['fix_mean']+timing_info['fix_range'], size=(param['n_blocks'],param['n_trials']))
fix_frames_seq = (fix_seq*win_info['framerate']).round().astype(int)
select_seq = np.random.uniform(timing_info['select_mean']-timing_info['select_range'],timing_info['select_mean']+timing_info['select_range'], size=(param['n_blocks'],param['n_trials']))
select_frames_seq = (select_seq*win_info['framerate']).round().astype(int)

##################################
###      MAKE STIMULI          ###
##################################
mon = monitors.Monitor('cocoLab',width=win_info['screen_width'],distance=win_info['screen_distance'])
mon.setSizePix(win_info['win_size'])
win=visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscr'],units="deg",autoLog=0,monitor=mon)

# and text stuff
startExp = visual.TextStim(win,text='Willkommen zur Casinoaufgabe!\nGleich geht es los.',color=win_info['fg_color'],height=0.35,autoLog=0)
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
leftframe = visual.Rect(win,width=stim_info['bar_width'],height=stim_info['bar_height'],lineColor=win_info['fg_color'],fillColor=None,pos = [-stim_info['bar_x'],stim_info['bar_y']],lineWidth=stim_info['line_width'],autoLog=0)
rightframe = visual.Rect(win,width=stim_info['bar_width'],height=stim_info['bar_height'],lineColor=win_info['fg_color'],fillColor=None,pos = [stim_info['bar_x'],stim_info['bar_y']],lineWidth=stim_info['line_width'],autoLog=0)
leftbar = visual.Rect(win,width=stim_info['bar_width'],lineColor=None,fillColor=win_info['fg_color'],autoLog=0)
rightbar = visual.Rect(win,width=stim_info['bar_width'],lineColor=None,fillColor=win_info['fg_color'],autoLog=0)
selectbar = visual.Rect(win,width=stim_info['bar_width']*1.7,height=stim_info['bar_height']*1.7,lineColor=win_info['fg_color'],fillColor=None,lineWidth=stim_info['line_width'],autoLog=0)
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

####################
###  START EXP   ###
####################
while 'c' not in event.getKeys():
    et.drawFlip(win,[startExp])          

######################
###  START BLOCKS  ###
######################
for block_no in range(param['n_blocks']):
    trial_info['block_no']=block_no+1
    block_correct = 0
    # start block message
    startBlock.text = stim_info["startBlock_text"].format(block_no+1, param['n_blocks'])
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
    for trial_no in range(param['n_trials']):
        # force quite experiment
        if 'q' in event.getKeys():
            et.finishExperiment(win,data_logger)

        #######################
        ###  SET VARIABLES  ###
        #######################  
        # reset variables
        trial_info['reward']=0
        trial_info['resp_key']=None
        trial_info['timeout']=0
        trial_info['choice_side'] = None
        leftbar.fillColor=win_info['fg_color']
        rightbar.fillColor=win_info['fg_color']

        # set trial variables
        trial_info['trial_no'] = trial_no+1
        trial_info['mag_left'] = sequence.loc[trial_count,'mag1']
        trial_info['mag_right']= sequence.loc[trial_count,'mag2']
        trial_info['prob_left'] = sequence.loc[trial_count,'prob1']
        trial_info['prob_right'] = sequence.loc[trial_count,'prob2']
        trial_info['outcome_left'] = sequence.loc[trial_count,'fb1']
        trial_info['outcome_right'] = sequence.loc[trial_count,'fb2']
        trial_info['ev_left'] = sequence.loc[trial_count,'ev1']
        trial_info['ev_right'] = sequence.loc[trial_count,'ev2']
        
        trial_info['ev_corr_resp'] = resp_keys[sequence.loc[trial_count,'CorrectLeftRight']-1]
        trial_info['prob_corr_resp'] = resp_keys[int(trial_info['prob_left']<trial_info['prob_right'])]
        trial_info['mag_corr_resp'] = resp_keys[int(trial_info['mag_left']<trial_info['mag_right'])]
        
        trial_count+=1
        fix_frames = fix_frames_seq[block_no,trial_no]
        select_frames = select_frames_seq[block_no,trial_no]
        # set stimulus
        leftbar.height = 0.1*stim_info['bar_height']*trial_info['mag_left']
        leftbar.pos=[-stim_info['bar_x'],stim_info['bar_y']-0.5*stim_info['bar_height']+0.05*stim_info['bar_height']*trial_info['mag_left']]
        rightbar.height =0.1*stim_info['bar_height']* trial_info['mag_right']
        rightbar.pos=[stim_info['bar_x'],stim_info['bar_y']-0.5*stim_info['bar_height']+0.05*stim_info['bar_height']*trial_info['mag_right']]
        leftProb.text =  '{:.0f}%'.format(trial_info['prob_left'])
        rightProb.text = '{:.0f}%'.format(trial_info['prob_right'])

        # check whether a button in the response box is currently pressed & present a warning if so
        t0 = core.getTime()
        if response_info['resp_mode']=='meg':
            while captureResponse(port,keys=resp_keys) in resp_keys:
                if core.getTime()-t0>1.0:
                    et.drawFlip(win,[warning]) 
        
        ##########################
        ###  FIXATION PHASE    ###
        ########################## 
        win.logOnFlip(level=logging.INFO, msg='start_fix\t{}\t{}'.format(trial_count,fix_seq[block_no,trial_no]))
        win.callOnFlip(et.sendTriggers,port,trigger_info['start_trial']) 
        for frame in range(fix_frames):
            if frame == 5:
                win.callOnFlip(et.sendTriggers,port,0)
            et.drawFlip(win,fix_phase) 
              
        ##########################
        ###  STIMULUS PHASE    ###
        ##########################
        event.clearEvents()
        win.logOnFlip(level=logging.INFO, msg='start_stim\t{}'.format(trial_count))
        win.callOnFlip(et.sendTriggers,port,trigger_info['start_stim']) 
        for frame in range(resp_frames): 
            # reset trigger
            if frame == 5:
                win.callOnFlip(et.sendTriggers,port,0)
            # show stim
            if frame==resp_frames-1:
                et.drawFlip(win,fix_phase) 
            elif frame ==0:
                start_stim_time = et.drawFlip(win,stim_phase) 
            else:
                et.drawFlip(win,stim_phase) 

            #sample response
            if response_info['run_mode']=='dummy':
                trial_info['resp_key'] = np.random.choice(resp_keys + [None]*resp_frames)
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

        # define incremental reward value and define selection box
        if trial_info['resp_key'] == resp_keys[0]:
            trial_info['choice_side'] = 0
            selectbar.pos = [-stim_info['bar_x'],stim_info['bar_y']-0.2*stim_info['bar_height']]
            if trial_info['outcome_left']:
                trial_info['reward'] = int(trial_info['mag_left'] *trial_info['outcome_left'])
        elif trial_info['resp_key'] == resp_keys[1]:
            trial_info['choice_side'] = 1
            selectbar.pos = [stim_info['bar_x'],stim_info['bar_y']-0.2*stim_info['bar_height']]
            if trial_info['outcome_right']:
                trial_info['reward'] = int(trial_info['mag_right']*trial_info['outcome_right'])
        else:
            trial_info['timeout'] = 1

        # draw selection phase if response given
        if not trial_info['timeout']:
            win.logOnFlip(level=logging.INFO, msg='start_select\t{}\t{}'.format(trial_count,select_seq[block_no,trial_no]))
            for frame in range(select_frames):
                et.drawFlip(win,select_phase)
        elif trial_info['timeout']:
            win.logOnFlip(level=logging.INFO, msg='start_timeout\t{}'.format(trial_count))
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
                total_points+=200          

        # draw feedback_phase 
        if trial_info['outcome_left'] == 1:
            leftbar.fillColor = bar['corr_color']
        else:
            leftbar.fillColor = bar['incorr_color']
        if trial_info['outcome_right'] == 1:
            rightbar.fillColor = bar['corr_color']
        else:
            rightbar.fillColor = bar['incorr_color']
 
        if trial_info['timeout'] ==0:    
            win.logOnFlip(level=logging.INFO, msg='start_feed\t{}'.format(trial_count))
            win.callOnFlip(et.sendTriggers,port,trigger_info['start_feed'])
            for frame in range(feed_frames):
                if frame == 5:
                    win.callOnFlip(et.sendTriggers,port,0)
                et.drawFlip(win,feedback_phase)
        
        ##########################
        ###  LOGGING  PHASE    ###
        ##########################
        win.logOnFlip(level=logging.INFO, msg='end_trial\t{}'.format(trial_count))
        et.drawFlip(win,fix_phase)

        if trial_count == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['log_order'])
        data_logger.writeTrial(trial_info)

    # save data of a block to file (behavior is updated after every block)
    data_logger.write2File()
    # end of block message 
    if trial_info['block_no'] !=param['n_blocks']:
        endBlock.text = stim_info["endBlock_text"].format(block_no+1,total_points)
        win.logOnFlip(level=logging.INFO, msg='end_block\t{}'.format(trial_info['block_no']))  
        for frame in range(pause_frames):
            et.drawFlip(win,[endBlock])
    
    # clear any pending key presses
    event.clearEvents()

# end of experiment message
performance = int(100*block_correct/param['n_trials'])   
if trial_info['ses_id'] == 'prac': 
    if performance>60:
        endExp.text = endExp.text.format(str(performance)+'% korrekt. Gut gemacht!','Das Experiment kann jetzt beginnen.')
    else:
        endExp.text = endExp.text.format(str(performance)+'% korrekt.','Bitte wiederhole die Übung.')
else:
    endExp.text = stim_info["endExp_text"].format(total_points)
while 'q' not in event.getKeys():
    et.drawFlip(win,[endExp])    

#cleanup
et.finishExperiment(win,data_logger,show_results=logging_info['show_results'])