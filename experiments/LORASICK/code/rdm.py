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
logging_info=param['logging_info']                # information on files and variables for logging
trigger_info = param['trigger_info']              # information on all the MEG trigger values and names
n_trials = param['n_trials']                      # number trials per block
n_blocks = param['n_blocks']                      # number total blocks
coherence_lvls = param['coherence_lvl']           # coherence levels
rdk = stim_info['cloud_specs']                    # info on RDK

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
    if  input_dict['ses_id'] in ['{:02d}'.format(i) for i in range(1,param['n_ses']+1)] +['scr','prac','pilot','intake']:
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
    port = None
    captureResponse = et.captureResponseKB
if response_info['run_mode'] == 'dummy':
   captureResponse = et.captureResponseDummy

# prepare the logfile (general log file, not data log file!) and directories
logFileID = logging_info['skeleton_file'].format(input_dict['sub_id'],input_dict['ses_id'],param['name'],str(datetime.now()).replace(' ','-').replace(':','-'))
log_file = os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.log').format(input_dict['sub_id'],input_dict['ses_id'],'log')
# create a output file that collects all variables 
output_file = os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.csv').format(input_dict['sub_id'],input_dict['ses_id'],'beh')
# save the current settings per session, so that the data files stay slim
settings_file=os.path.join('sub-{:02d}','ses-{}','{}',logFileID+'.json').format(input_dict['sub_id'],input_dict['ses_id'],'settings')
# save dot positions for each dot on each frame, trial and block
position_file = os.path.join(os.path.join('sub-{:02d}','ses-{}','{}').format(input_dict['sub_id'],input_dict['ses_id'],'dot_xy'),logFileID+'_block-{:02d}.pkl')

for f in [log_file,position_file,settings_file,output_file]:
    if not os.path.exists(os.path.dirname(f)): 
        os.makedirs(os.path.dirname(f))
os.system('cp {} {}'.format(jsonfile,settings_file))
lastLog = logging.LogFile(log_file, level=logging.INFO, filemode='w')

# init logger: update the constant values (things that wont change)
trial_info = {'sub_id':input_dict['sub_id'],
                'ses_id':input_dict['ses_id'],
                'logFileID':logFileID}

for vari in logging_info['logVars']:
    trial_info[vari] = param[vari]

###########################################
###  PREPARE EXPERIMENTAL SEQUENCE     ####
###########################################
n_cohs = len(coherence_lvls)
n_dots = int(rdk['dotperdva']*0.5*rdk['cloud_size']**2*np.pi)
trial_count=0
# set response keys
resp_keys = [response_info['resp_left'],response_info['resp_right']]
# prepare a dataframe specifically for the stimulus positions
all_positions = pd.DataFrame(columns= {'positions':np.nan}, index={'trial_no':[(b+1) for b in range(n_trials+param['n_zero'])]})

################################
###    MAKE STIMULI          ###
################################
mon = monitors.Monitor('cocoLab',width = win_info['screen_width'],distance = win_info['screen_distance'])
mon.setSizePix(win_info['win_size'])
#create a window
win=visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscr'],units='deg',monitor=mon,autoLog=0)
# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()
# first all kind of structural messages
startExp = visual.TextStim(win,text='Willkommen zur Weltallaufgabe!\n Gleich geht es los.',color=win_info['fg_color'],height=0.4,autoLog=0)
startBlock = visual.TextStim(win,text=stim_info["blockStart"],color=win_info['fg_color'],height=0.4,autoLog=0)
endBlock = visual.TextStim(win,text=stim_info["blockEnd"],color=win_info['fg_color'],height=0.4,autoLog=0)
endExp = visual.TextStim(win,text=stim_info["exp_outro"],color=win_info['fg_color'],height=0.4,autoLog=0)
warning = visual.TextStim(win,text=stim_info["warning"],color=win_info['fg_color'],height=0.4,autoLog=0)
feedback = visual.TextStim(win,text='',color=win_info['fg_color'],height=0.4,autoLog=0)
fixDot = et.fancyFixDot(win,fg_color = win_info['fg_color'],bg_color = win_info['bg_color'],size=0.4) 
cloud=visual.DotStim(win,color=win_info['fg_color'],fieldSize=rdk['cloud_size'],nDots=n_dots,dotLife=rdk['dotLife'],dotSize=rdk['size_dots'],speed=rdk['speed'],signalDots=rdk['signalDots'],noiseDots=rdk['noiseDots'],fieldShape='circle',coherence=0)
middle = visual.Circle(win, size=rdk['annulus'], pos=[0,0],lineColor=None,fillColor=win_info['bg_color'],autoLog=0)
# reset all triggers to zero
et.sendTriggers(port,0)

####################
###  SET TIMING  ###
####################
pause_frames = round(timing_info['pause_dur']*win_info['framerate'])
feed_frames = round(timing_info['feed_dur']*win_info['framerate'])
fix_frames = round(timing_info['fix_dur']*win_info['framerate'])
noise_seq = np.random.uniform(timing_info['noise_mean']-timing_info['noise_range'],timing_info['noise_mean']+timing_info['noise_range'], size=(n_blocks,n_trials+param['n_zero']))

####################
###  START EXP   ###
####################
# show block intro 
while 'c' not in event.getKeys():
    et.drawFlip(win,[startExp])          

###########################
###  START BLOCK LOOP # ###
###########################
for block_no in range(n_blocks):
    # create trial sequence
    trial_seq = np.tile(np.arange(n_cohs),int(n_trials/n_cohs))
    
    # add zero-coherence trials
    trial_seq = np.concatenate((trial_seq,np.ones(param['n_zero'],dtype=int)*n_cohs)) 

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
    trigger_seq = ['rdk_{}_{}'.format(dir_seq[i],coherence_lvls.index(coh_seq[i])+1) for i in range(len(trial_seq))]

    # reset block variables
    total_correct = 0 
    trial_info['block_no']=block_no+1

    # show block intro 
    startBlock.text = stim_info["blockStart"].format(trial_info['block_no'],n_blocks)
    while True:
        et.drawFlip(win,[startBlock])                    
        cont=captureResponse(port,keys = [response_info['pause_resp']])    
        if cont == response_info['pause_resp']:
            while captureResponse(port,keys=resp_keys+[None]) in resp_keys:
                win.flip()
            win.callOnFlip(et.sendTriggers,port,trigger_info['start_block'],reset = 0.5)
            win.logOnFlip(level=logging.INFO, msg='start_block\t{}'.format(trial_info['block_no']))
            win.flip()
            break  

    ##########################
    ###  START TRIAL LOOP  ###
    ##########################
    for trial_no in range(n_trials):
        # force quite experiment
        if 'q' in event.getKeys():
            et.finishExperiment(win,data_logger)

        # set/reset trial variables
        trial_info['resp_key']=None
        trial_info['early_response']=0
        trial_info['timeout']=0
        trial_info['trial_no'] = trial_no+1
        trial_count+=1
        trial_info['corr_resp'] = corr_resp_seq[trial_no]
        trial_info['cur_coherence'] =coh_seq[trial_no]  
        trial_info['cur_dir'] = dir_seq[trial_no]
        trial_info['cur_trigger'] = trigger_seq[trial_no]    
        noise_frames = int(round(noise_seq[block_no,trial_no]*win_info['framerate']))
        stim_frames = noise_frames+int(round(timing_info['stim_dur']*win_info['framerate']))
        dot_frames = noise_frames+int(timing_info['resp_dur']*win_info['framerate'])

        # draw RDK stimulus 
        cloud.coherence = 0
        cloud.dir = trial_info['cur_dir']

        ##########################
        ###  FIXATION PHASE    ###
        ##########################   
        t0 = core.getTime()
        # make sure the response of the previous trial has stopped
        while captureResponse(port,keys=resp_keys+[None]) in resp_keys:
            if core.getTime()-t0>1.0: 
                et.drawFlip(win,[warning])  

        # start trial and draw fixation and wait for 
        win.logOnFlip(level=logging.INFO, msg='start_fix\t{}\t{}'.format(trial_count,timing_info['fix_dur']+0.008))
        win.callOnFlip(et.sendTriggers,port,trigger_info['start_fix'])  
        for frame in range(fix_frames):
            if frame == 5:
                win.callOnFlip(et.sendTriggers,port,0)
            t0=et.drawFlip(win,fixDot)  

        # remove premature responses
        event.clearEvents()
        # check whether a button in the response box is currently pressed & present a warning if so
        while captureResponse(port,keys=resp_keys+[None]) in resp_keys:
            if core.getTime()-t0>1.0: 
                et.drawFlip(win,[warning])  
       
        ##########################
        ###  STIMULUS PHASE    ###
        ##########################
        stimTime=dict(onset=np.nan)
        dot_positions = np.zeros((dot_frames,n_dots,2))
        win.logOnFlip(level=logging.INFO, msg='start_noise\t{}\t{}'.format(trial_count,noise_seq[block_no,trial_no]))
        win.callOnFlip(et.sendTriggers,port,trigger_info['start_noise'])
        for frame in range(dot_frames):     
            # show cloud
            if frame<stim_frames:
                if frame == 5: 
                    et.sendTriggers(port,0)
                elif frame==noise_frames:
                    cloud.coherence = trial_info['cur_coherence']
                    win.logOnFlip(level=logging.INFO, msg='start_stim\t{}'.format(trial_count))
                    win.callOnFlip(et.sendTriggers,port,trigger_info[trial_info['cur_trigger']])
                    win.timeOnFlip(stimTime,'onset')
                elif frame==noise_frames+5:
                    win.callOnFlip(et.sendTriggers,port,0)     
                if rdk['annulus']>0:
                    et.drawCompositeStim([cloud,middle]+fixDot)
                else:
                    et.drawCompositeStim([cloud]+fixDot)
            else:               
                et.drawCompositeStim(fixDot)
            win.logOnFlip(level=logging.INFO, msg='stim_frame\t{}\t{}'.format(trial_count,frame+1))
            win.flip()
                
            # save dot position
            dot_positions[frame,:,:] = cloud.verticesPix            

            # poll response break if a key was pressed
            if response_info['run_mode']=='dummy':
                trial_info['resp_key']=np.random.choice(resp_keys + [None]*dot_frames)
            else:
                trial_info['resp_key']=captureResponse(port,keys=resp_keys)
            # break if responded
            if trial_info['resp_key'] in resp_keys:
                break  

        ##########################
        ###  POST PROCESSING   ###
        ##########################
        trial_info['resp_time'] = core.getTime()-stimTime['onset']
        trial_info['resp_key'] = trial_info['resp_key']
        trial_info['correct'] = int(trial_info['resp_key']==trial_info['corr_resp'])
        total_correct+=trial_info['correct']  

        win.logOnFlip(level=logging.INFO, msg='resp_time\t{}\t{}'.format(trial_count,trial_info['resp_time']))
        et.drawFlip(win,fixDot)

        # check for too early or too late responses
        if frame == dot_frames-1:
            trial_info['timeout'] = 1
            feedback.text = 'Zu spät!'
        # don't allow responses within the noise + 200 ms of signal (anticipatory responses)
        elif frame <= noise_frames + 0.2*win_info['framerate']:
            trial_info['early_response'] = 1
            feedback.text = 'Zu früh!' 

        # show feedback if no response was given       
        if trial_info['timeout'] == 1 or trial_info['early_response'] == 1:
            trial_info['correct'] = np.nan
            win.logOnFlip(level=logging.INFO, msg='start_feed\t{}\t{}'.format(trial_count,timing_info['feed_dur']+0.008))
            win.callOnFlip(et.sendTriggers,port,trigger_info['start_feedback'], prePad=0.024)
            for frame in range(feed_frames):
                if frame == 5:
                    win.callOnFlip(et.sendTriggers,port,0)
                et.drawFlip(win,[feedback])   
        
        ##########################
        ###  LOGGING  PHASE    ###
        ########################## 
        win.logOnFlip(level=logging.INFO, msg='end_trial\t{}'.format(trial_count))
        et.drawFlip(win,fixDot)

        if trial_count == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['first_columns'])
        data_logger.writeTrial(trial_info)

        # keep track of dot positions        
        all_positions.loc[trial_info['trial_no'],'positions'] = dot_positions

    # show end of block text
    performance = int(100*total_correct/n_trials)
    if trial_info['block_no'] != n_blocks:
        endBlock.text = stim_info["blockEnd"].format(block_no+1,performance)
        win.logOnFlip(level=logging.INFO, msg='end_block\t{}'.format(trial_info['block_no']))
        for frame in range(pause_frames):
            et.drawFlip(win,[endBlock])
    event.clearEvents()
    # save data of a block to file (behavior is updated, dot positions writes a file per block)
    all_positions.to_pickle(position_file.format(trial_info['block_no']))
    data_logger.write2File()

# end of experiment message
if trial_info['ses_id'] == 'prac': 
    if performance>75:
        endExp.text = endExp.text.format(str(performance)+'% korrekt. Gut gemacht!','Das Experiment kann jetzt beginnen.')
    else:
        endExp.text = endExp.text.format(str(performance)+'% korrekt. ','Bitte wiederhole die Übung.')
while 'q' not in event.getKeys():
    et.drawFlip(win,[endExp])          

#cleanup
et.finishExperiment(win,data_logger,show_results=True)