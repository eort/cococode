# created by Eduard Ort, 2019 
#######################
###  import libraries  ###
#######################
from psychopy import visual, core, event,gui,logging #import some libraries from PsychoPy
import expTools as et # custom scripts
import json # to load configuration files
import sys, os # to interact with the operating system
from datetime import datetime # to get the current time
import numpy as np # to do fancy math shit
import glob # to search in system efficiently
from IPython import embed as shell # for debugging

# reset all triggers to zero
os.system("/usr/local/bin/parashell 0x378 0")
#######################################
###  load config file (settings)  #####
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
###  Create Parameters / do Overhead   ####
###########################################
# read out json sidecar
n_trials = param['n_trials']            # number trials per block
n_blocks = param['n_blocks']            # number total blocks
fix_sleep_mean = param['fix_mean']      # presentation duration of fixdot
fix_sleep_range = param['fix_range']    # presentation duration of fixdot
feed_sleep = param['feed_sleep']        # presentation duration of feedback
sess_type = param['sess_type']            # are we practicing or not
trigger = param['trigger']              # trigger for defined events
rdk = param['cloud_specs']              # info on RDK

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

# prepare the logfile (general log file, not data log file!) and directories
et.prepDirectories()
logFile = os.path.join('log',param['logFile'].format(input_dict['sub_id'],input_dict['sess_id'],datetime.now()).replace(' ','-').replace(':','-'))
lastLog = logging.LogFile(logFile, level=logging.INFO, filemode='w')
# create a output file that collects all variables 
output_file = os.path.join('dat',param['exp_id'],param['output_file'].format(input_dict['sub_id'],input_dict['sess_id'],datetime.now()).replace(' ','-').replace(':','-'))

# init logger
# update the constant values (things that wont change)
trial_info = { "sub_id":input_dict['sub_id'],
                "sess_id":input_dict['sess_id'],
                "sess_type":input_dict['sess_type'],
                "start_exp_time":core.getTime(),
                "end_block_time":np.nan}

for vari in param['logVars']:
    trial_info[vari] = param[vari]
trial_info['logFile'] = logFile
trial_info['output_file'] = output_file

###########################################
###  Prepare Experimental Sequence     ####
###########################################

# prepare coherence levels of dots
coherence_lvls = param['coherence_lvl']   
n_cohs = len(coherence_lvls)

if param['resp_mode'] == 'meg':
    resp_left = param['resp1_button']
    resp_right = param['resp2_button']
    pause = param['pause_button']
else:
    resp_left = param['resp1_key']
    resp_right = param['resp2_key']
    pause = param['pause_key']
resp_keys = [resp_left,resp_right]
# make a sequence of fix-stim jitter
fix_seq = np.random.uniform(fix_sleep_mean-fix_sleep_range,fix_sleep_mean+fix_sleep_range, size=(n_blocks,n_trials))

################################
###  START ACTUAL EXPERIMENT ###
################################
#create a window
win = visual.Window(size=param['win_size'],color=param['bg_color'],fullscr=trial_info['fullscreen'], units="pix",screen=1)
for i in range(10):
    win.flip()
# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()
#########################
###  prepare stimuli  ###
#########################

# first all kind of structural messages
startBlock = visual.TextStim(win,text=param["blockStart"],color='white',wrapWidth=win.size[0])
endBlock = visual.TextStim(win,text=param["blockEnd"],color='white',wrapWidth=win.size[0])
endExp = visual.TextStim(win,text=param["exp_outro"],color='white',wrapWidth=win.size[0])
fixDot = et.fancyFixDot(win, fg_color = param['fg_color'],bg_color = param['bg_color']) # fixation dot
cloud = visual.DotStim(win,units = 'pix',fieldSize=rdk['cloud_size'],nDots=rdk['n_dots'],dotLife=rdk['dotLife'] ,dotSize=rdk['size_dots'],speed=rdk['speed'],signalDots=rdk['signalDots'],noiseDots=rdk['noiseDots'],fieldShape = 'circle')
timeout_scr = visual.TextStim(win,text='Zu langsam!',color='white',wrapWidth=win.size[0])
     
###########################
###  START BLOCK LOOP # ###
###########################
for block_no in range(n_blocks):
    # create trial sequence
    trial_seq = np.tile(np.arange(n_cohs),int(n_trials/n_cohs) )
    # make sure no direction repetitions of coherence levels
    np.random.shuffle(trial_seq)
    if not trial_info['sess_type']:
        while 0 in np.diff(trial_seq):
            np.random.shuffle(trial_seq)

    # make sure every coherence lvl is matched with both directions equal number of times
    dir_list = [0,1]*int(n_trials/2/n_cohs)
    dir_dict = {}
    for coh in range(n_cohs):
        np.random.shuffle(dir_list)
        dir_dict[coh] =list(dir_list)

    # define direction sequence
    _dir_seq = []
    for coh in trial_seq:
        _dir_seq.append(dir_dict[coh].pop())

    dir_seq = [param['dir1'] if i==0 else param['dir2']  for i in _dir_seq ]
    corr_resp_seq = [resp_left if i==0 else resp_right  for i in _dir_seq]
    coh_seq = [coherence_lvls[i] for i in trial_seq ]
    
    # reset block variables
    trial_info['total_correct'] = 0 
   
    # wait for button press
    if param['run_mode'] != 'dummy':
        startBlock.text = param["blockStart"].format(block_no+1)
        startBlock.draw()
        win.flip()
        event.waitKeys(keyList = [pause])

    # time when block started
    trial_info['start_block_time'] = core.getTime()
    trial_info['block_no']=block_no+1

    # send trigger
    et.sendTriggers(trigger['block_on'],mode=param['resp_mode'])

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
        trial_info['feedbackDur']= np.nan
        
        # draw duration of fix cross from predefined distribution
        trial_info['fix_sleep'] = fix_seq[block_no,trial_no]
        trial_info['trial_no'] = trial_no+1
        trial_info['trial_count']+=1
        # set specific orientations
        trial_info['corr_resp'] = corr_resp_seq[trial_no]
        trial_info['cur_dir'] = dir_seq[trial_no]
        trial_info['cur_coherence'] = coh_seq[trial_no]     
        # draw RDK stimulus
        cloud.coherence = trial_info['cur_coherence']
        cloud.dir = trial_info['cur_dir']

        # start trial
        trial_info['start_trial_time'] = core.getTime()

        # draw fixation and wait for 
        for elem in fixDot:
            elem.draw()  
        win.flip()        
        # send triggers
        et.sendTriggers(trigger['trial_on'],mode=param['resp_mode'])
        core.wait(trial_info['fix_sleep']-0.02*int(param['resp_mode']=='meg'))
        
        trial_info['fixDur']= core.getTime()-trial_info['start_trial_time']
        
        # send triggers
        et.sendTriggers(trigger['coh_{}_{}'.format(param['dir1'],coherence_lvls.index(cloud.coherence)+1)],mode=param['resp_mode'])
        # start response time measure
        trial_info['start_stim_time'] = core.getTime()
        
        # present stims
        drawStim = True
        while core.getTime()-trial_info['start_stim_time']<param['resp_timeout']:
            # remove stimulus
            if core.getTime()-trial_info['start_stim_time']>=param['stim_sleep']:
                if drawStim:
                    # end times of stimulation
                    et.sendTriggers(trigger['stim_off'],mode=param['resp_mode'])
                    trial_info['end_stim_time'] = core.getTime()
                    trial_info['stimDur'] = trial_info['end_stim_time']-trial_info['start_stim_time']
                    drawStim=False
                for elem in fixDot:
                    elem.draw()      
                win.flip()
            # show cloud
            else:
                for elem in fixDot:
                    elem.draw()      
                cloud.draw()
                win.flip()

            # get response
            if param['run_mode']=='dummy':
                    response = np.random.choice(resp_keys+[None]*int(param['framerate']*param['resp_timeout']))
            else:
                response = et.captureResponse(mode=param['resp_mode'],keys=resp_keys)        

            # check the response
            if response in resp_keys:
                time_response = core.getTime()  
                trial_info['end_stim_time'] = time_response
                core.wait(0.01) # sleep to make responses not overlap with following stim
                break

        ##########################
        ###  POST PROCESSING   ###
        ##########################
        if response == None:
            time_response = core.getTime()
        # start handling response variables
        trial_info['resp_time'] = time_response-trial_info['start_stim_time']
        trial_info['resp_key'] = response
        trial_info['correct'] = int(response==trial_info['corr_resp'])

        # show feedback if no response was given       
        if response != None:
            trial_info['timeout'] = 0
        else:
            trial_info['timeout'] = 1
            timeout_scr.draw()
            win.flip()
            et.sendTriggers(trigger['timeout_on'],mode=param['resp_mode'])
            core.wait(param['feed_sleep']-0.02*int(param['resp_mode']=='meg'))
            win.flip()
            t7 = core.getTime()
            et.sendTriggers(trigger['timeout_off'],mode=param['resp_mode'])
            trial_info['feedbackDur'] = t7-time_response

        if trial_info['correct']:
            trial_info['total_correct']+=1      
        
        # send triggers
        trial_info['end_trial_time'] = core.getTime()
        et.sendTriggers(trigger['trial_off'],mode=param['resp_mode'])
        
        # logging
        if trial_info['trial_count'] == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info)
        data_logger.writeTrial(trial_info)

    # send triggers
    et.sendTriggers(trigger['block_off'],mode=param['resp_mode'])

    # show text at the end of a block 
    if param['run_mode'] != 'dummy':      
        endBlock.text = param["blockEnd"].format(block_no+1,int(100*trial_info['total_correct']/n_trials))
        endBlock.draw()
        win.flip()
        core.wait(param['pause_sleep'])      

# end of experiment message
endExp.draw()
win.flip()
if param['run_mode'] != 'dummy':
    event.waitKeys(keyList = ['space'])    

#cleanup
et.finishExperiment(win,data_logger,show_results=True)