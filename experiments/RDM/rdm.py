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
    port = parallel.Parallel()
elif response_info['resp_mode'] == 'keyboard': 
    port = None
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
n_dots = int(rdk['dotperdva']*0.5*rdk['cloud_size']**2*np.pi)

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
win=visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscr'],units='deg',monitor=mon,autoLog=0)
# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()
# first all kind of structural messages
startBlock = visual.TextStim(win,text=stim_info["blockStart"],color=win_info['fg_color'],height=0.4,autoLog=0)
endBlock = visual.TextStim(win,text=stim_info["blockEnd"],color=win_info['fg_color'],height=0.4,autoLog=0)
endExp = visual.TextStim(win,text=stim_info["exp_outro"],color=win_info['fg_color'],height=0.4,autoLog=0)
warning = visual.TextStim(win,text=stim_info["warning"],color=win_info['fg_color'],height=0.4,autoLog=0)
feedback = visual.TextStim(win,text='',color=win_info['fg_color'],height=0.4,autoLog=0)
fixDot = et.fancyFixDot(win,fg_color = win_info['fg_color'],bg_color = win_info['bg_color'],size=0.4) 
cloud=visual.DotStim(win,color=win_info['fg_color'],fieldSize=rdk['cloud_size'],nDots=n_dots,dotLife=rdk['dotLife'],dotSize=rdk['size_dots'],speed=rdk['speed'],signalDots=rdk['signalDots'],noiseDots=rdk['noiseDots'],fieldShape='circle',coherence=0)

# reset all triggers to zero
et.sendTriggers(port,0)

####################
###  SET TIMING  ###
####################
pause_frames = round(timing_info['pause_dur']*win_info['framerate'])
feed_frames = round(timing_info['feed_dur']*win_info['framerate'])
fix_frames = round(timing_info['fix_dur']*win_info['framerate'])
noise_seq = np.random.uniform(timing_info['noise_mean']-timing_info['noise_range'],timing_info['noise_mean']+timing_info['noise_range'], size=(n_blocks,n_trials+param['n_zero']))

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
    trigger_seq = ['rdk_{}_{}'.format(dir_seq[i],coherence_lvls.index(coh_seq[i])+1) for i in range(len(trial_seq))]

    # reset block variables
    trial_info['total_correct'] = 0 
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
        escape = event.getKeys()
        if 'q' in escape:
            et.finishExperiment(win,data_logger)

        # set/reset trial variables
        response=None
        trial_info['early_response']=0
        trial_info['timeout']=0
        trial_info['noise_dur'] = noise_seq[block_no,trial_no]
        trial_info['trial_no'] = trial_no+1
        trial_info['trial_count']+=1
        trial_info['corr_resp'] = corr_resp_seq[trial_no]
        trial_info['cur_coherence'] =coh_seq[trial_no]  
        trial_info['cur_dir'] = dir_seq[trial_no]
        trial_info['cur_trigger'] = trigger_seq[trial_no]    
        noise_frames = int(round(trial_info['noise_dur']*win_info['framerate']))
        stim_frames = noise_frames+int(round(timing_info['stim_dur']*win_info['framerate']))
        dot_frames = noise_frames+int(timing_info['resp_dur']*win_info['framerate'])

        # draw RDK stimulus 
        cloud.coherence = 0
        cloud.dir = trial_info['cur_dir']

        ##########################
        ###  FIXATION PHASE    ###
        ##########################   
        # start trial and draw fixation and wait for 
        win.logOnFlip(level=logging.INFO, msg='start_fix\t{}'.format(trial_info['trial_count']))
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
        stimTime = dict(onset=np.nan)
        dot_positions = np.zeros((dot_frames,n_dots,2))
        win.logOnFlip(level=logging.INFO, msg='start_noise\t{}\t{}'.format(trial_info['trial_count'],trial_info['noise_dur']))
        win.callOnFlip(et.sendTriggers,port,trigger_info['start_noise'])
        for frame in range(dot_frames):     
            # show cloud
            if frame<stim_frames:
                if frame == 5: 
                    et.sendTriggers(port,0)
                elif frame==noise_frames:
                    cloud.coherence = trial_info['cur_coherence']
                    win.logOnFlip(level=logging.INFO, msg='start_stim\t{}'.format(trial_info['trial_count']))
                    win.callOnFlip(et.sendTriggers,port,trial_info['cur_trigger'])
                    win.timeOnFlip(stimTime,'onset')
                elif frame==noise_frames+5:
                    win.callOnFlip(et.sendTriggers,port,0)     
                win.logOnFlip(level=logging.INFO, msg='cloud_frame\t{}\t{}'.format(trial_info['trial_count'],frame+1))
                et.drawFlip(win,fixDot + [cloud]) 
            else:               
                win.logOnFlip(level=logging.INFO, msg='nostim_frame\t{}\t{}'.format(trial_info['trial_count'],frame+1))
                et.drawFlip(win,fixDot)

            # save dot position
            dot_positions[frame,:,:] = cloud.verticesPix            

            # poll response break if a key was pressed
            if response_info['run_mode']=='dummy':
                response = np.random.choice(resp_keys + [None]*dot_frames)
            else:
                response = captureResponse(port,keys=resp_keys)
            # break if responded
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
        trial_info['total_correct']+=trial_info['correct']  

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
            win.logOnFlip(level=logging.INFO, msg='start_feed\t{}'.format(trial_info['trial_count']))
            win.callOnFlip(et.sendTriggers,port,trigger_info['start_feedback'], prePad=0.024)
            for frame in range(feed_frames):
                if frame == 5:
                    win.callOnFlip(et.sendTriggers,port,0)
                et.drawFlip(win,[feedback])   
        
        ##########################
        ###  LOGGING  PHASE    ###
        ########################## 
        win.logOnFlip(level=logging.INFO, msg='end_trial\t{}'.format(trial_info['trial_count']))
        et.drawFlip(win,fixDot)

        if trial_info['trial_count'] == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['first_columns'])
        data_logger.writeTrial(trial_info)

        # keep track of dot positions        
        all_positions.loc[(trial_info['block_no'],trial_info['trial_no']),'positions'] = dot_positions

    # show end of block text
    endBlock.text = stim_info["blockEnd"].format(block_no+1,int(100*trial_info['total_correct']/n_trials))
    win.logOnFlip(level=logging.INFO, msg='end_block\t{}'.format(trial_info['block_no']))
    for frame in range(pause_frames):
        et.drawFlip(win,[endBlock])
    event.clearEvents()

# end of experiment message
while et.captureResponseKB(port,keys = ['q']) != 'q':
    et.drawFlip(win,[endExp])

#cleanup
all_positions.to_csv(position_file,na_rep=pd.np.nan)
et.finishExperiment(win,data_logger,show_results=True)