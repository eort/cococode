# created by Eduard Ort, 2019 
# based on Matlab code by Hannah Kurtenbach

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
#from IPython import embed as shell # for debugging

# reset system
os.system('parashell 0x378 0')
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
n_miniblocks = param['n_miniblocks']    # number total blocks
n_exem = param['n_exem']                # number exemplars per family
n_fams = param['n_fams']                # number families
fix_sleep_mean = param['fix_mean']      # mean presentation duration of fixdot
fix_sleep_range = param['fix_range']    # min and max range of fixdot
sess_type = param['sess_type']          # are we practicing or not
trigger = param['trigger']              # what are the MEG triggers

# dialog with participants: Retrieve Subject number, session number, and practice
input_dict = dict(sub_id=0,sess_id=0,sess_type=sess_type)
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','sess_id','sess_type'])
# check for input
if inputGUI.OK == False:
    print("Experiment aborted by user")
    core.quit()
while input_dict['sess_id'] not in [1,2,3]:
    print('WARNING: You need to specify a session number (1, 2, or 3)')
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

# init logger variables
# update the constant values (things that wont change)
trial_info = { "sub_id":input_dict['sub_id'],
            "sess_id":input_dict['sess_id'],
            "sess_type":input_dict['sess_type'],
            "start_exp_time":core.getTime() ,
            "end_block_time":np.nan}
# migrate info from logfile
for vari in param['logVars']:
    trial_info[vari] = param[vari]
# plus two more variables
trial_info['logFile'] = logFile
trial_info['output_file'] = output_file

###########################################
###  Create Experimental Sequence      ####
###########################################
# define the response button (flexible for with response box vs. keyboard)
if param['resp_mode'] == 'meg':
    resp_go = param['response_button']
    pause_resp = param['pause_button']
else:
    resp_go = param['response_key']
    pause_resp = param['pause_key']

resp_keys = [resp_go,param['resp_nogo']]
# initialize the previous item to prevent greeble repeats
prev_item = None

# how many times each stimulus per mini block
n_unique = n_exem*n_fams
n_repeats = n_trials//n_unique
if n_trials%n_unique != 0:
    print('WARNING: {} unique trials cannot be shown equally often in {} trials.'.format(n_unique,n_trials))
    logging.warning('WARNING: {} unique orientations cannot be shown equally often in {} trials.'.format(n_unique,n_trials))

# counterbalance which greebles are used in which session
if input_dict['sub_id']%2:
    if input_dict['sess_id'] == 1:
        imageDir = '{}_set1'.format(input_dict['sess_type'])
    elif input_dict['sess_id'] == 2:
        imageDir = '{}_set2'.format(input_dict['sess_type'])
else:
    if input_dict['sess_id'] == 1:
        imageDir = '{}_set2'.format(input_dict['sess_type'])
    elif input_dict['sess_id'] == 2:
        imageDir = '{}_set1'.format(input_dict['sess_type'])

# load greeble file paths
image_paths = sorted(glob.glob(os.path.join(imageDir,'*.tif')))
# split greebles into families, to go and no go category + shuffle 
families = np.array(image_paths).reshape((n_fams,n_exem))

if input_dict['sess_type']=='practice':
    go_stim = families[0].tolist()*n_repeats
    nogo_stim = families[1].tolist()*n_repeats
else:
    np.random.shuffle(families.T)
    go_stim = families[:,:n_exem//2].flatten()
    nogo_stim = families[:,n_exem//2:].flatten()

# add go/nogo stim to logfile        
trial_info['go_stim'] = go_stim
trial_info['nogo_stim'] = nogo_stim

# reset block variables
trial_info['total_correct'] = 0

# make a sequence of fix-stim jitter
fix_seq = np.random.uniform(fix_sleep_mean-fix_sleep_range,fix_sleep_mean+fix_sleep_range, size=(n_miniblocks,n_trials))

################################
###  START ACTUAL EXPERIMENT ###
################################
#create a window
win = visual.Window(size=param['win_size'],color=param['bg_color'],fullscr=param['fullscreen'],units="pix",screen=1)
# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()
#########################
###  prepare stimuli  ###
#########################
# first all kind of structural messages
startexp = visual.TextStim(win,text=param['startexp_text'],color=param['fg_color'],wrapWidth=win.size[0])
endExp = visual.TextStim(win,text=param['exp_outro'],color=param['fg_color'],wrapWidth=win.size[0])
pause = visual.TextStim(win,text=param['pause_text'],color=param['fg_color'],wrapWidth=win.size[0])
#feedback things   
smiley = visual.ImageStim(win,'smiley.png',contrast=-1) # good feedback
frowny = visual.ImageStim(win,'frowny.png',contrast=-1) # bad feedback
# progressbar 
progress_bar =visual.Rect(win,width=10,height=20,lineColor=param['fg_color'],fillColor=param['fg_color'],pos = [-500,-200])
progress_bar_start =visual.Rect(win,width=10,height=20,lineColor=param['fg_color'],fillColor=param['fg_color'],pos = [-500,-200])
progress_bar_end =visual.Rect(win,width=10,height=20,lineColor=param['fg_color'],fillColor=param['fg_color'],pos = [500,-200])
# Greeble and fixation dot
greeble = visual.ImageStim(win,image=image_paths[0],size=(240,270))
fixDot = et.fancyFixDot(win, bg_color = param['bg_color'],size=24) # fixation dot

# combine feedback stims to make it easier later
feedback_stims = [frowny,smiley]

###########################
###  PREPARE BLOCK VARS ###
###########################
# draw intro before starting block
startexp.draw()
# show intro
win.flip()
# wait for button press
if param['run_mode'] != 'dummy':
    event.waitKeys(keyList = [pause_resp])

# send trigger
et.sendTriggers(trigger['block_on'],mode=param['resp_mode'])
trial_info['start_block_time'] = core.getTime()
trial_info['block_no'] = 1

###########################
###  START BLOCK LOOP # ###
###########################
for miniblock_no in range(n_miniblocks):
    # we use fake blocks here. Better word would be building blocks
    # blocks are not separated by a pause screen or something like that
    # instead pauses are only added occasionally (predefined)

    # create trial sequence (within 12 trials, gos (1) and nogos (0) are equal)
    trial_seq = [0,1]*int(n_unique/2)
    trial_seq = trial_seq*n_repeats
    np.random.shuffle(trial_seq)

    # assign stimuli to trials
    np.random.shuffle(go_stim)
    np.random.shuffle(nogo_stim)
    # make sure twice the same stimulus in a row does not happen
    if trial_info['sess_type'] != 'practice':
        while prev_item in [go_stim[0],nogo_stim[0]]:
            np.random.shuffle(go_stim)    
            np.random.shuffle(nogo_stim)
    go_seq=list(go_stim)
    nogo_seq=list(nogo_stim)
    
    # define correct response sequence
    corr_resp_seq = [resp_keys[0] if i==1 else resp_keys[1] for i in trial_seq ]
    # convenience variable to know sequence of gos and nogos
    gonogo_seq = ['go' if i==1 else 'nogo' for i in trial_seq ]
    # actual file path sequence
    stim_seq = [go_seq.pop() if i==1 else nogo_seq.pop() for i in trial_seq]

    # If a pause block occur, interupt sequence and show a message
    # these pauses are the actual block breaks
    if miniblock_no+1 in trial_info['pause_blocks']:
        # send block off trigger 
        trial_info['end_block_time'] = core.getTime()
        et.sendTriggers(trigger['block_off'],mode=param['resp_mode'])
        if param['run_mode'] != 'dummy':
            pause.draw()
            win.flip()  
            core.wait(param['pause_sleep']) 
            # draw intro before starting block
            startexp.draw()
            # show intro
            win.flip()         
            event.waitKeys(keyList = [pause_resp])
        trial_info['block_no'] +=1
        # send trigger for block on things
        et.sendTriggers(trigger['block_on'],mode=param['resp_mode'])

        # time when block started
        trial_info['start_block_time'] = core.getTime()
    
    trial_info['miniblock_no']=miniblock_no+1
    
    # define context (based on pre-defined length and timing of noreward blocks)
    if miniblock_no+1 in trial_info['noreward_blocks']:
        trial_info['context'] = 'probe'
    elif miniblock_no+1 in trial_info['pre_blocks']:
        trial_info['context'] = 'reward' 
    elif miniblock_no+1 in trial_info['post_blocks']:
        trial_info['context'] = 'reward' 
          
    ##########################
    ###  START TRIAL LOOP  ###
    ##########################
    for trial_no in range(n_trials):
        trial_info['feedbackDur']= np.nan
        trial_info['end_stim_time']= np.nan
        # force quite experiment
        escape = event.getKeys()
        if 'q' in escape:
            et.finishExperiment(win,data_logger)
        
        # draw duration of fix cross from predefined distribution
        trial_info['fix_sleep'] = fix_seq[miniblock_no,trial_no]

        # set trial-specific variables
        trial_info['trial_no'] = trial_no+1
        trial_info['trial_count']+=1
        # go or nogo
        trial_info['condition'] = gonogo_seq[trial_no]
        # which greeble
        trial_info['stim'] = stim_seq[trial_no]
        # what is the correct response
        trial_info['corr_resp'] = corr_resp_seq[trial_no]
        # set current greeble image
        greeble.setImage(trial_info['stim'])

        # make presence of progress bar contingent on context
        if trial_info['context'] == 'reward':    
            # draw progress bar
            progress_bar.draw()    
            progress_bar_start.draw()
            progress_bar_end.draw()  

        # draw fixation 
        for elem in fixDot:
            elem.draw()        
        # present it
        win.flip()

        trial_info['start_trial_time'] = core.getTime()
        # send triggers
        et.sendTriggers(trigger['trial_on'],mode=param['resp_mode'])
        # sleep during fixation
        core.wait(trial_info['fix_sleep']-0.02*int(param['resp_mode']=='meg'))
        trial_info['fixDur'] = core.getTime()-trial_info['start_trial_time']
        # draw stimulus
        greeble.draw()
        if trial_info['context'] == 'reward':
            progress_bar.draw()    
            progress_bar_start.draw()
            progress_bar_end.draw()   
            
        trial_info['start_stim_time'] = core.getTime()
        win.flip()

        # send trigger
        if trial_info['condition'] == 'go':
            et.sendTriggers(trigger['go_greeble'],mode=param['resp_mode'])
        elif trial_info['condition'] == 'nogo':
            et.sendTriggers(trigger['nogo_greeble'],mode=param['resp_mode'])
        
        if param['resp_mode']=='keyboard':
            event.clearEvents()
        # start response time measure
        while core.getTime()-trial_info['start_stim_time']<param['resp_timeout']:
            # either get a real response or let the computer respond
            if param['run_mode']=='dummy':
                core.sleep(0.4) # arbitrarily defined
                response = np.random.choice(resp_keys)
            else:
                response = et.captureResponse(mode=param['resp_mode'],keys=resp_keys)
            # break if go
            if response == resp_go:
                if np.isnan(trial_info['end_stim_time']):
                    trial_info['end_stim_time'] = core.getTime()    
                core.wait(0.01)
                break
            # remove stimulus if timeout reached
            if (core.getTime()-trial_info['start_stim_time'])>param['stim_sleep']:
                if np.isnan(trial_info['end_stim_time']):
                    trial_info['end_stim_time'] = core.getTime()
                et.sendTriggers(trigger['greeble_off'],mode=param['resp_mode'])
                # prepare response screen
                if trial_info['context'] == 'reward':    
                    progress_bar.draw()    
                    progress_bar_start.draw()
                    progress_bar_end.draw()   
            
                # draw fixation 
                for elem in fixDot:
                    elem.draw()             
                win.flip()

        ##########################
        ###  POST PROCESSING   ###
        ##########################
        # start handling response variables
        trial_info['stim_dur'] = trial_info['end_stim_time']-trial_info['start_stim_time']
        trial_info['resp_dur'] = core.getTime()-trial_info['start_stim_time']
        trial_info['resp_time'] = core.getTime()-trial_info['start_stim_time']
        trial_info['resp_key'] = response
        trial_info['correct'] = int(response==trial_info['corr_resp'])

        #do reward math and adjust progress bar position and width
        trial_info['total_correct'] +=trial_info['correct']

        if trial_info['context'] == 'reward':
            if trial_info['resp_key']==resp_go: 
                if trial_info['correct']:
                    trial_info['total_reward']+= trial_info['reward_step']
                    progress_bar.width += 250*trial_info['reward_step']
                    progress_bar.pos[0] += 250*(trial_info['reward_step']/2)
                else:
                    trial_info['total_reward']-= trial_info['reward_step']
                    progress_bar.width -= (250*trial_info['reward_step'])
                    progress_bar.pos[0] -= (250*(trial_info['reward_step']/2))
                if progress_bar.width > 1000:
                    progress_bar.width=trial_info['rewad_step']
                    progress_bar.pos[0] = -500                
                elif progress_bar.width < 10:
                    progress_bar.width=10
                    progress_bar.pos[0] = -500

                # show feedback, depending on context   
                feedback_stims[int(trial_info['correct'])].draw()             
            
                # add progress bar if in right context
                progress_bar.draw()    
                progress_bar_start.draw()
                progress_bar_end.draw()   

                # show feedback (if any)
                t6 = core.getTime()
                win.flip()            
                et.sendTriggers(trigger['fb_on'],mode=param['resp_mode'])
                core.wait(param['feed_sleep']-0.02*int(param['resp_mode']=='meg'))
                # add progress bar if in right context
                if trial_info['context'] == 'reward':
                    progress_bar.draw()    
                    progress_bar_start.draw()
                    progress_bar_end.draw()   
                    win.flip()
                t7 = core.getTime()
                # triggers for fb off
                et.sendTriggers(trigger['fb_off'],mode=param['resp_mode'])
                # timing checks
                      
                trial_info['feedbackDur'] = t7-t6
                # write variables to logfile

        # trial off time
        trial_info['end_trial_time'] = core.getTime()
        et.sendTriggers(trigger['trial_off'],mode=param['resp_mode'])
        if trial_info['trial_count'] == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info)
        data_logger.writeTrial(trial_info)

    # update the previous greeble which codes the last greeble in a miniblock
    prev_item = trial_info['stim']
    # end of miniblock message
    trial_info['end_block_time'] = core.getTime()

# end of experiment message + total feedback
if trial_info['sess_type'] != 'practice':
    endExp.text = 'Fertig. Deine Accuracy ist {}%'.format(int(100*trial_info['total_correct']/trial_info['trial_count']))
else:
    endExp.text = param['exp_outro'].format(max(0,trial_info['total_reward']))

endExp.draw()
win.flip()
if param['run_mode'] != 'dummy':
    event.waitKeys(keyList = ['space'])  

#cleanup
et.finishExperiment(win,data_logger,sort='lazy',show_results=True)