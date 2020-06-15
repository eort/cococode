# created by Eduard Ort, 2019 
##########################
###  IMPORT LIBRARIES  ###
##########################
from psychopy import visual, core, event,gui,logging, prefs #import some libraries from PsychoPy
import expTools as et # custom scripts
import json # to load configuration files
import sys, os # to interact with the operating system
from datetime import datetime # to get the current time
import numpy as np # to do fancy math shit
import glob # to search in system efficiently
#from IPython import embed as shell # for debugging

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
input_dict = dict(sub_id=0,sess_id=0,sess_type=sess_type,noise_duration=timing_info['noise_mean'])
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','sess_id','sess_type',"noise_duration"])

noise_mean = input_dict['noise_duration']
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
et.prepDirectories()
logFileID = logging_info['skeleton_file'].format(input_dict['sub_id'],input_dict['sess_id'],param['name'],str(datetime.now()).replace(' ','-').replace(':','-'))
log_file = os.path.join('log',logFileID+'.log')
lastLog = logging.LogFile(log_file, level=logging.INFO, filemode='w')
# create a output file that collects all variables 
output_file = os.path.join('dat',param['exp_id'],logFileID+'.csv')
# save the current settings per session, so that the data files stay slim
settings_file = os.path.join('settings',param['exp_id'],logFileID+'.json')
if not os.path.exists(os.path.dirname(settings_file)): 
    os.makedirs(os.path.dirname(settings_file))
os.system('cp {} {}'.format(jsonfile,settings_file))

# init logger: update the constant values (things that wont change)
trial_info = { "sub_id":input_dict['sub_id'],
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
    coherence_lvls = [0.2+coh for coh in param['coherence_lvl']]
n_cohs = len(coherence_lvls)

if response_info['resp_mode'] == 'meg':
    resp_left = response_info['resp1_button']
    resp_right = response_info['resp2_button']
    pause_resp = response_info['pause_button']
else:
    resp_left = response_info['resp1_key']
    resp_right = response_info['resp2_key']
    pause_resp = response_info['pause_key']
resp_keys = [resp_left,resp_right]

################################
###    MAKE STIMULI          ###
################################
#create a window
win = visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscreen'], units="pix",screen=1)

# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()

# first all kind of structural messages
startBlock = visual.TextStim(win,text=stim_info["blockStart"],color='white',wrapWidth=win.size[0])
endBlock = visual.TextStim(win,text=stim_info["blockEnd"],color='white',wrapWidth=win.size[0])
endExp = visual.TextStim(win,text=stim_info["exp_outro"],color='white',wrapWidth=win.size[0])
warning = visual.TextStim(win,text=stim_info["warning"],color='white',wrapWidth=win.size[0])
fixDot = et.fancyFixDot(win, fg_color = win_info['fg_color'],bg_color = win_info['bg_color']) 
cloud = visual.DotStim(win,units = 'pix',fieldSize=rdk['cloud_size'],nDots=rdk['n_dots'],dotLife=rdk['dotLife'] ,dotSize=rdk['size_dots'],speed=rdk['speed'],signalDots=rdk['signalDots'],noiseDots=rdk['noiseDots'],fieldShape = 'circle')
noise = visual.DotStim(win,units = 'pix',fieldSize=rdk['cloud_size'],nDots=rdk['n_dots'],dotLife=rdk['dotLife'] ,dotSize=rdk['size_dots'],speed=rdk['speed'],signalDots=rdk['signalDots'],noiseDots=rdk['noiseDots'],fieldShape = 'circle',coherence=0)
feedback = visual.TextStim(win,text='',color='white',wrapWidth=win.size[0])

####################
###  SET TIMING  ###
####################
pause_frames = round(timing_info['pause_dur']*win_info['framerate'])
feed_frames = round(timing_info['feed_dur']*win_info['framerate'])
fix_frames = round(timing_info['fix_dur']*win_info['framerate'])
stim_frames = round(timing_info['stim_dur']*win_info['framerate'])
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

    dir_seq = [param['dir1'] if i==-1 else param['dir2'] if i==1 else 0  for i in _dir_seq]
    corr_resp_seq = [resp_left if i==-1 else resp_right  if i==1 else None for i in _dir_seq]
    coh_seq = [coherence_lvls[i] for i in trial_seq ]
    
    # reset block variables
    trial_info['total_correct'] = 0 
   
    if response_info['run_mode'] != 'dummy':
        # show block intro 
        while True:
            startBlock.text = stim_info["blockStart"].format(block_no+1)
            startBlock.draw()
            trial_info['start_block_time'] = win.flip()                        
            cont=et.captureResponse(mode=response_info['resp_mode'],keys = [pause_resp])    
            if cont == pause_resp:
                break

    # send trigger
    et.sendTriggers(trigger_info['block_on'],mode=response_info['resp_mode'])
    trial_info['block_no']=block_no+1

    ##########################
    ###  START TRIAL LOOP  ###
    ##########################
    for trial_no in range(n_trials):
        # force quite experiment
        escape = event.getKeys()
        if 'q' in escape:
            et.finishExperiment(win,data_logger)

        # for timing tests, delete later
        trial_info['stimDur']= np.nan
        trial_info['end_feed_time']= np.nan
        trial_info['feedbackDur']= np.nan
        trial_info['early_response'] = 0
        trial_info['timeout']=0
        # draw duration of fix cross from predefined distribution
        trial_info['noise_dur'] = noise_seq[block_no,trial_no]
        trial_info['trial_no'] = trial_no+1
        trial_info['trial_count']+=1
        # set specific orientations
        trial_info['corr_resp'] = corr_resp_seq[trial_no]
        trial_info['cur_coherence'] = coh_seq[trial_no]  
        trial_info['cur_dir'] = dir_seq[trial_no]   
        # draw RDK stimulus
        cloud.coherence = trial_info['cur_coherence']
        if param['n_zero']:
            cloud.dir = trial_info['cur_dir']
        else:
            cloud.dir = None

        dot_frames = int(round((trial_info['noise_dur']+timing_info['resp_dur'])*win_info['framerate']))
        noise_frames = int(round(trial_info['noise_dur']*win_info['framerate']))
        # choose a dummy response mode response frame
        if response_info['run_mode']=='dummy':
            dummy_resp_frame = max(noise_frames+1,np.random.choice(range(dot_frames)))

        ##########################
        ###  FIXATION PHASE    ###
        ##########################   
        # start trial and draw fixation and wait for 
        et.drawCompositeStim(fixDot)
        trial_info['start_trial_time'] =win.flip()  
        et.sendTriggers(trigger_info['fix_on'],mode=response_info['resp_mode'])   
        for frame in range(fix_frames):
            et.drawCompositeStim(fixDot)
            trial_info['end_fix_time'] = win.flip()

        # remove premature responses
        if response_info['resp_mode']=='keyboard':
            event.clearEvents()
        else:
            # check whether a button in the response box is currently pressed & present a warning if so
            while et.captureResponse(mode=response_info['resp_mode'],keys=resp_keys) in resp_keys:
                trial_info['start_stim_time']=win.flip()
                if trial_info['start_stim_time']-trial_info['end_fix_time']>1.0:
                    warning.draw()
                    win.flip()        
        ##########################
        ###  STIMULUS PHASE    ###
        ########################## 
        et.drawCompositeStim(fixDot+[noise])
        trial_info['start_noise_time'] =win.flip() 
        et.sendTriggers(trigger_info['noise_on'],mode=response_info['resp_mode'])
        for frame in range(dot_frames):        
            if frame<noise_frames:
                et.drawCompositeStim(fixDot + [noise])
                trial_info['end_stim_time']=trial_info['start_stim_time']=win.flip()    
            elif frame<stim_frames:
                # send trigger on the first frame
                if frame==noise_frames:
                    et.sendTriggers(trigger_info['coh_{}_{}'.format(trial_info['cur_dir'],coherence_lvls.index(trial_info['cur_coherence'])+1)],mode=response_info['resp_mode'])                
                et.drawCompositeStim(fixDot + [cloud])
                trial_info['end_stim_time'] =win.flip()    
            else:
                et.drawCompositeStim(fixDot)
                win.flip()

            #sample response
            if response_info['run_mode']=='dummy':
                if dummy_resp_frame == frame:
                    response = np.random.choice(resp_keys)
                else: response = None
            else:
                response = et.captureResponse(mode=response_info['resp_mode'],keys=resp_keys)

            # break if go
            if response in resp_keys:
                break

        time_response = core.getTime()
        # check for too early or too late responses
        if frame == dot_frames-1:
            trial_info['timeout'] = 1
            feedback.text = 'Zu spät!'
        elif frame <= noise_frames:
            trial_info['early_response'] = 1
            feedback.text = 'Zu früh!'            

        ##########################
        ###  POST PROCESSING   ###
        ##########################
        # start handling response variables
        trial_info['stimDur'] = trial_info['end_stim_time']-trial_info['start_stim_time']
        trial_info['noiseDur'] = trial_info['start_stim_time']-trial_info['start_noise_time']
        trial_info['resp_time'] = time_response-trial_info['start_stim_time']
        trial_info['resp_key'] = response
        trial_info['correct'] = int(response==trial_info['corr_resp'])

        # show feedback if no response was given       
        if trial_info['timeout'] == 1 or trial_info['early_response'] == 1:
            trial_info['correct'] = np.nan
            et.sendTriggers(trigger_info['feedback_on'],mode=response_info['resp_mode'])
            for frame in range(feed_frames):
                feedback.draw()
                win.flip()

        if trial_info['correct']:
            trial_info['total_correct']+=1      
        
        # send triggers
        trial_info['end_trial_time'] = core.getTime()
        
        ##########################
        ###  LOGGING  PHASE    ###
        ########################## 
        if trial_info['trial_count'] == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['first_columns'])
        data_logger.writeTrial(trial_info)

    # send triggers
    if response_info['resp_mode']=='keyboard':
        event.clearEvents()
    # show text at the end of a block 
    if response_info['run_mode'] != 'dummy':      
        endBlock.text = stim_info["blockEnd"].format(block_no+1,int(100*trial_info['total_correct']/n_trials))
        for frame in range(pause_frames):
            endBlock.draw()
            win.flip() 
        if response_info['resp_mode']=='keyboard':
                event.clearEvents()
# end of experiment message
if response_info['run_mode'] != 'dummy':
    while True:
        endExp.draw()
        win.flip()
        cont=et.captureResponse(mode=response_info['resp_mode'],keys = [pause_resp])    
        if cont == pause_resp:
            break
#cleanup
et.finishExperiment(win,data_logger,show_results=True)