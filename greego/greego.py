# created by Eduard Ort, 2019 
# based on Matlab code by Hannah Kurtenbach

#######################
###  import libraries  ###
#######################
from psychopy import visual, core, event,gui,logging,data #import some libraries from PsychoPy
import expTools as et # custom scripts
import json # to load configuration files
import sys, os # to interact with the operating system
from datetime import datetime # to get the current time
import numpy as np # to do fancy math shit
import glob # to search in system efficiently
from IPython import embed as shell # for debugging

# reset system
os.system('parashell 0x378 0')
#######################################
###  load config file (settings)  #####
#######################################
try:
    jsonfile = sys.argv[1]
except IndexError as e:
    print("No config file provided. Load default settings")
    jsonfile = 'default_cfg.json'
with open(jsonfile) as f:    
    param = json.load(f)

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
practice = param['practice']            # are we practicing or not
trigger = param['trigger']              # what are the MEG triggers

# dialog with participants: Retrieve Subject number, session number, and practice
input_dict = dict(sub_id=0,sess_id=0,practice=practice)
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','sess_id'])

# prepare the logfile and directories
et.prepDirectories()
logFile = os.path.join('log',param['logFile'].format(input_dict['sub_id'],input_dict['sess_id'],datetime.now()).replace(' ','-').replace(':','-'))
lastLog = logging.LogFile(logFile, level=logging.INFO, filemode='w')

# when did experiment start
start_exp_time = core.getTime() 

###########################################
###  Create Experimental Sequence      ####
###########################################

# counterbalance which greebles are used in which session
if input_dict['sub_id']%2:
    if input_dict['sess_id'] == 1:
        imageDir = param['imageDir'][0]
    elif input_dict['sess_id'] == 2:
        imageDir = param['imageDir'][1]
else:
    if input_dict['sess_id'] == 1:
        imageDir = param['imageDir'][1]
    elif input_dict['sess_id'] == 2:
        imageDir = param['imageDir'][0]

# load greeble file path 
image_paths = sorted(glob.glob(os.path.join(imageDir,'*.tif')))
# split greebles into families
if not practice:
    families = [image_paths[:n_exem],image_paths[n_exem:2*n_exem],image_paths[2*n_exem:]]
else:
    families = [[image_paths[0]],[image_paths[1]]]

# how many times each stimulus per mini block
n_unique = n_exem*n_fams
n_repeats = n_trials//n_unique
if n_trials%n_unique != 0:
    print('WARNING: {} unique trials cannot be shown equally often in {} trials.'.format(n_unique,n_trials))
    logging.warning('WARNING: {} unique orientations cannot be shown equally often in {} trials.'.format(n_unique,n_trials))

# init logger
# update the constant values (things that wont change)
trial_info = { "sub_id":input_dict['sub_id'],
            "sess_id":input_dict['sess_id'],
            "start_exp_time":start_exp_time,
            "block_on_trigger":trigger['block_on'],
            "block_off_trigger":trigger['block_off'],
            "trial_on_trigger":trigger['trial_on'],
            "trial_off_trigger":trigger['trial_off'],
            "go_greeble_trigger":trigger['go_greeble'],
            "nogo_greeble_trigger":trigger['nogo_greeble'],
            "greeble_off_trigger":trigger['greeble_off'],
            "fb_on_trigger":trigger['fb_on'],
            "fb_off_trigger":trigger['fb_off'],
            "index_trigger":trigger['index'],
            "end_block_time":np.nan}

for vari in param['logVars']:
    trial_info[vari] = param[vari]
# create a output file that collects all variables 
output_file = os.path.join('dat',param['expID'],param['output_file'].format(input_dict['sub_id'],input_dict['sess_id'],datetime.now()).replace(' ','-').replace(':','-'))
trial_info['logFile'] = logFile
trial_info['output_file'] = output_file

if param['mode'] == 'meg':
    resp_go = param['response_button']
else:
    resp_go = param['response_key']
# initialize the previous item to prevent greeble repeats
prev_item = None
################################
###  START ACTUAL EXPERIMENT ###
################################

#create a window
win = visual.Window(size=param['win_size'],color=param['bg_color'],fullscr=param['fullscreen'],monitor="testMonitor", units="pix",screen=1)

# set Mouse to be invisible
event.Mouse(win=None,visible=False)

#########################
###  prepare stimuli  ###
#########################
# first all kind of structural messages
startexp = visual.TextStim(win,text=param['startexp_text'],color=param['fg_color'],wrapWidth=win.size[0])
endExp = visual.TextStim(win,text=param['exp_outro'],color=param['fg_color'],wrapWidth=win.size[0])
pause = visual.TextStim(win,text=param['pause_text'],color=param['fg_color'],wrapWidth=win.size[0])
#feedback things    "trial_count":0,

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
# assign stimuli to go and no go category + shuffle 
all_stim = list(families)
if practice:
    go_stim = all_stim[0]*n_repeats
    nogo_stim = all_stim[1]*n_repeats
else:
    fam1,fam2,fam3 = all_stim
    for fam in [fam1,fam2,fam3]:
        np.random.shuffle(fam)
    
    # split families in half to assign to go and nogo
    go_stim=(fam1[:n_exem//2]+fam2[:n_exem//2]+fam3[:n_exem//2])
    nogo_stim=(fam1[n_exem//2:]+fam2[n_exem//2:]+fam3[n_exem//2:])

# add go/nogo stim to logfile        
trial_info['go_stim'] = go_stim
trial_info['nogo_stim'] = nogo_stim

# reset block variables
trial_info['total_correct'] = 0

# make a sequence of fix-stim jitter
fix_seq = np.random.uniform(fix_sleep_mean-fix_sleep_range,fix_sleep_mean+fix_sleep_range, size=(49,12))

# draw intro before starting block
startexp.draw()
# show intro
win.flip()
# wait for button press
if param['mode'] != 'dummy':
    event.waitKeys(keyList = ['space'])

# send trigger
et.sendTriggers(trigger['block_on'],mode=param['mode'])
trial_info['start_block_time'] = core.getTime()
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
    if not practice:
        while prev_item in [go_stim[0],nogo_stim[0]]:
            np.random.shuffle(go_stim)    
            np.random.shuffle(nogo_stim)
    go_seq=list(go_stim)
    nogo_seq=list(nogo_stim)
    
    # define correct response sequence
    corr_resp_seq = [resp_go if i==1 else trial_info['resp_nogo'] for i in trial_seq ]
    # convenience variable to know sequence of gos and nogos
    gonogo_seq = ['go' if i==1 else 'nogo' for i in trial_seq ]
    # actual file path sequence
    stim_seq = [go_seq.pop() if i==1 else nogo_seq.pop() for i in trial_seq]

    # If a pause block occur, interupt sequence and show a message
    # these pauses are the actual block breaks
    if miniblock_no+1 in trial_info['pause_blocks']:
        # send trigger for block off things
        trial_info['end_block_time'] = core.getTime()
        et.sendTriggers(trigger['block_off'],mode=param['mode'])
        pause.draw()
        win.flip()
        if param['mode'] != 'dummy':
            event.waitKeys(keyList = ['space'])
        # send trigger for block on things
        et.sendTriggers(trigger['block_on'],mode=param['mode'])


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
        trial_info['respDur_noresp'] = np.nan
        trial_info['stimDur_noresp']= np.nan
        trial_info['stimDur_resp']= np.nan
        trial_info['feedbackDur']= np.nan
        trial_info['fixDur']= np.nan

        # force quite experiment
        escape = event.getKeys()
        if 'q' in escape:
            et.finishExperiment(win,data_logger)
        
        trial_info['trial_no'] = trial_no+1
        trial_info['trial_count']+=1

        # draw duration of fix cross from predefined distribution
        trial_info['fix_sleep'] = fix_seq[miniblock_no,trial_no]

        # set trial-specific variables
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
        t0 = core.getTime()
        trial_info['start_trial_time'] = core.getTime()
        # send triggers
        et.sendTriggers(trigger['trial_on'],mode=param['mode'])
        # sleep during fixation
        core.wait(trial_info['fix_sleep']-0.02*int(param['mode']=='meg'))

        # draw stimulus
        greeble.draw()
        if trial_info['context'] == 'reward':
            progress_bar.draw()    
            progress_bar_start.draw()
            progress_bar_end.draw()   
            
        trial_info['start_stim_time'] = core.getTime()
        win.flip()
        t1 = core.getTime()
        # send trigger
        if trial_info['condition'] == 'go':
            et.sendTriggers(trigger['go_greeble'],mode=param['mode'])
        elif trial_info['condition'] == 'nogo':
            et.sendTriggers(trigger['nogo_greeble'],mode=param['mode'])

        # prepare response screen
        if trial_info['context'] == 'reward':    
            progress_bar.draw()    
            progress_bar_start.draw()
            progress_bar_end.draw()   
        
        # draw fixation 
        for elem in fixDot:
            elem.draw()       
        
        # start response time measure
        enter_respPhase = 1
        #define how long a response is waited for
        timeout = param['stim_sleep']-0.02*int(param['mode']=='meg')
        # get response
        while True:
            response = et.captureResponse(mode=param['mode'],key=resp_go,timeout= timeout)
            if response == resp_go:
                break

            if core.getTime()-trial_info['start_stim_time']>param['resp_sleep']:
                # define nogo response variables
                response = None
                t4 = core.getTime()
                trial_info['respDur_noresp'] = t4-t3
                break

            # remove stimulus
            if enter_respPhase == 1 and core.getTime()-trial_info['start_stim_time']>param['stim_sleep']:
                # draw fixation 
                win.flip()
                t3 = core.getTime()
                trial_info['stimDur_noresp'] = t3-t1
                et.sendTriggers(trigger['greeble_off'],mode=param['mode'])
                trial_info['end_stim_time'] = core.getTime()
                enter_respPhase = 0 
                timeout = param['resp_sleep']-0.02*int(param['mode']=='meg')

        ##########################
        ###  POST PROCESSING   ###
        ##########################
        if enter_respPhase == 1:
            win.flip()
            t2 = core.getTime()
            et.sendTriggers(trigger['greeble_off'],mode=param['mode'])
            trial_info['stimDur_resp'] = t2-t1
            trial_info['end_stim_time'] = core.getTime()

        # start handling response variables
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
        et.sendTriggers(trigger['fb_on'],mode=param['mode'])
        core.wait(param['feed_sleep']-0.02*int(param['mode']=='meg'))
        # add progress bar if in right context
        progress_bar.draw()    
        progress_bar_start.draw()
        progress_bar_end.draw()   
        win.flip()
        t7 = core.getTime()
        # triggers for fb off
        et.sendTriggers(trigger['fb_off'],mode=param['mode'])
        # timing checks
        trial_info['fixDur'] = t1-t0      
        trial_info['feedbackDur'] = (t7-t6)
        # write variables to logfile

        # trial off time
        trial_info['end_trial_time'] = core.getTime()
        et.sendTriggers(trigger['trial_off'],mode=param['mode'])
        if trial_info['trial_count'] == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info)
        data_logger.writeTrial(trial_info)

    # update the previous greeble which codes the last greeble in a miniblock
    prev_item = trial_info['stim']
    # end of miniblock message
    trial_info['end_block_time'] = core.getTime()

# end of experiment message + total feedback
if practice:
    endExp.text = 'Fertig. Deine Accuracy ist {}%'.format(int(100*trial_info['total_correct']/trial_info['trial_count']))
else:
    endExp.text = param['exp_outro'].format(max(0,trial_info['total_reward']))

endExp.draw()
win.flip()
if param['mode'] != 'dummy':
    event.waitKeys(keyList = ['space'])  

#cleanup
et.finishExperiment(win,data_logger,sort='lazy',show_results=True)