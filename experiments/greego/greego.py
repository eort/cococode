# created by Eduard Ort, 2019 
# based on Matlab code by Hannah Kurtenbach

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
###          READ OUT JSON SIDECAR     ####
###########################################
timing_info =param['timing_info']                 # information on the timings of the sequence
stim_info=param['stim_info']                      # information on all stimuli to be drawn
win_info=param['win_info']                        # information on the psychopy window  
response_info=param['response_info']              # information on response collection  
reward_info=param['reward_info']                  # Information on the reward schedule
logging_info=param['logging_info']                # information on files and variables for logging
trigger_info = param['trigger_info']              # information on all the MEG trigger values and names
n_trials = param['n_trials']            # number trials per block
n_miniblocks = param['n_miniblocks']    # number total blocks
n_exem = param['n_exem']                # number exemplars per family
n_fams = param['n_fams']                # number families
sess_type = param['sess_type']          # are we practicing or not

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
    print('WARNING: You need to specify a session number (1, 2, or 3)')
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

# init logger variables
# update the constant values (things that wont change)
trial_info = { 'sub_id':input_dict['sub_id'],
                'sess_id':input_dict['sess_id'],
                'sess_type':input_dict['sess_type'],
                'logFileID':logFileID,
                'total_reward':0,
                'trial_count':0,
                'total_correct':0,
                'start_exp_time':core.getTime(),
                'end_block_time':np.nan}
# migrate info from logfile
for vari in logging_info['logVars']:
    trial_info[vari] = param[vari]

###########################################
###  PREPARE EXPERIMENTAL SEQUENCE     ####
###########################################
# define the response button (flexible for with response box vs. keyboard)
if response_info['resp_mode'] == 'meg':
    resp_go = response_info['response_button']
    pause_resp = response_info['pause_button']
else:
    resp_go = response_info['response_key']
    pause_resp = response_info['pause_key']

resp_keys = [resp_go,response_info['resp_nogo']]
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

####################
###  SET TIMING  ###
####################
# make a sequence of fix-stim jitter
fix_seq = np.random.uniform(timing_info['fix_mean']-timing_info['fix_range'],timing_info['fix_mean']+timing_info['fix_range'], size=(n_miniblocks,n_trials))

# convert timing to frames
pause_frames = round(timing_info['pause_sleep']*win_info['framerate'])
feed_frames = round(timing_info['feed_sleep']*win_info['framerate'])
fix_frames_seq = (fix_seq*win_info['framerate']).round().astype(int)

################################
###         MAKE STIMULI     ###
################################
#create a window
win = visual.Window(size=win_info['win_size'],color=win_info['bg_color'],fullscr=win_info['fullscreen'],units="pix",screen=1)
# set Mouse to be invisible
event.Mouse(win=None,visible=False)
event.clearEvents()
#########################
###  prepare stimuli  ###
#########################
# first all kind of structural messages
startexp = visual.TextStim(win,text=stim_info['startexp_text'],color=win_info['fg_color'],wrapWidth=win.size[0])
endExp = visual.TextStim(win,text=stim_info['exp_outro'],color=win_info['fg_color'],wrapWidth=win.size[0])
pause = visual.TextStim(win,text=stim_info['pause_text'],color=win_info['fg_color'],wrapWidth=win.size[0])
#feedback things   
smiley = visual.ImageStim(win,'smiley.png',contrast=-1) # good feedback
frowny = visual.ImageStim(win,'frowny.png',contrast=-1) # bad feedback
# progressbar 
progress_bar =visual.Rect(win,width=10,height=20,lineColor=win_info['fg_color'],fillColor=win_info['fg_color'],pos = [-500,-200])
progress_bar_start =visual.Rect(win,width=10,height=20,lineColor=win_info['fg_color'],fillColor=win_info['fg_color'],pos = [-500,-200])
progress_bar_end =visual.Rect(win,width=10,height=20,lineColor=win_info['fg_color'],fillColor=win_info['fg_color'],pos = [500,-200])
# Greeble and fixation dot
greeble = visual.ImageStim(win,image=image_paths[0],size=(320*stim_info['image_scale'],360*stim_info['image_scale']))
fixDot = et.fancyFixDot(win, bg_color = win_info['bg_color'],size=24) # fixation dot

# combine feedback stims to make it easier later
feedback_stims = [frowny,smiley]

###########################
###  START BLOCK LOOP # ###
###########################
# draw intro before starting block
startexp.draw()
trial_info['start_block_time']=win.flip()
if response_info['run_mode'] != 'dummy':
    while True:
        startexp.draw()
        win.flip()                        
        cont=et.captureResponse(mode=response_info['resp_mode'],keys = [pause_resp])    
        if cont == pause_resp:
            break

# send trigger
et.sendTriggers(trigger_info['start_block'],mode=response_info['resp_mode'])
trial_info['block_no'] = 1

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
    if miniblock_no+1 in param['pause_blocks']:
        # show pause and send block off trigger 
        pause.draw()
        trial_info['end_block_time'] = win.flip() 
        if response_info['run_mode'] != 'dummy':
            for frame in range(pause_frames):
                pause.draw()
                win.flip() 
            # show intro 
            while True:
                startexp.draw()
                win.flip()                        
                cont=et.captureResponse(mode=response_info['resp_mode'],keys = [pause_resp])    
                if cont == pause_resp:
                    break

        trial_info['block_no'] +=1
        # send trigger for block on things
        et.sendTriggers(trigger_info['start_block'],mode=response_info['resp_mode'])

        # time when block started
        trial_info['start_block_time'] = core.getTime()
    
    trial_info['miniblock_no']=miniblock_no+1
    
    # define context (based on pre-defined length and timing of noreward blocks)
    if miniblock_no+1 in param['noreward_blocks']:
        trial_info['context'] = 'probe'
    elif miniblock_no+1 in param['pre_blocks']:
        trial_info['context'] = 'reward' 
    elif miniblock_no+1 in param['post_blocks']:
        trial_info['context'] = 'reward' 
          
    ##########################
    ###  START TRIAL LOOP  ###
    ##########################
    for trial_no in range(n_trials):
        trial_info['start_feed_time']=np.nan
        trial_info['end_feed_time']=np.nan
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

        
        # send triggers
        et.sendTriggers(trigger_info['start_trial'],mode=response_info['resp_mode'])

        # fixation period
        for frame in range(fix_frames_seq[miniblock_no,trial_no]):
            # make presence of progress bar contingent on context
            if trial_info['context'] == 'reward':    
                et.drawCompositeStim([progress_bar,progress_bar_start,progress_bar_end])            
            et.drawCompositeStim(fixDot)    
            if frame == 0:
                # start trial
                trial_info['start_trial_time'] = win.flip() 
            else:
                trial_info['start_stim_time'] =win.flip()


        trial_info['fixDur'] =  trial_info['start_stim_time']-trial_info['start_trial_time']        
        # draw stimulus
        greeble.draw()
        if trial_info['context'] == 'reward':
            et.drawCompositeStim([progress_bar,progress_bar_start,progress_bar_end])            

        ##########################
        ###  STIM + RESPONSE   ###
        ##########################            
        trial_info['start_stim_time'] = win.flip()
        trial_info['fixDur'] =  trial_info['start_stim_time']-trial_info['start_trial_time']

        # send trigger
        if trial_info['condition'] == 'go':
            et.sendTriggers(trigger_info['go_greeble'],mode=response_info['resp_mode'])
        elif trial_info['condition'] == 'nogo':
            et.sendTriggers(trigger_info['nogo_greeble'],mode=response_info['resp_mode'])

        # do it framewise rather than timeout based
        resp_frames = round((timing_info['resp_timeout']-(core.getTime()-trial_info['start_stim_time']))*win_info['framerate'])
        stim_frames = round((timing_info['stim_sleep']-(core.getTime()-trial_info['start_stim_time']))*win_info['framerate'])

        if response_info['resp_mode']=='keyboard':
            event.clearEvents()
        if response_info['run_mode']=='dummy':
            dummy_resp_frame = np.random.choice(range(resp_frames))

        for frame in range(resp_frames):
            if frame<stim_frames:
                greeble.draw()
                if trial_info['context'] == 'reward':
                    et.drawCompositeStim([progress_bar,progress_bar_start,progress_bar_end])     
                trial_info['end_stim_time'] =win.flip()    
            else:
                if frame==stim_frames:
                    trial_info['end_stim_time'] = core.getTime()
                    et.sendTriggers(trigger_info['start_resp'],mode=response_info['resp_mode'])
                et.drawCompositeStim(fixDot)
                if trial_info['context'] == 'reward':
                    et.drawCompositeStim([progress_bar,progress_bar_start,progress_bar_end]) 
                win.flip()

            if response_info['run_mode']=='dummy':
                if dummy_resp_frame == frame:
                    response = np.random.choice(resp_keys)
                else: response = None
            else:
                response = et.captureResponse(mode=response_info['resp_mode'],keys=resp_keys)

            # break if go
            if response == resp_go:
                break           

        ##########################
        ###  POST PROCESSING   ###
        ##########################
        # start handling response variables
        trial_info['stim_dur'] = trial_info['end_stim_time']-trial_info['start_stim_time']
        trial_info['resp_time'] = core.getTime()-trial_info['start_stim_time']
        trial_info['resp_key'] = response
        trial_info['correct'] = int(response==trial_info['corr_resp'])

        #do reward math and adjust progress bar position and width
        trial_info['total_correct'] +=trial_info['correct']

        if trial_info['context'] == 'reward':
            if trial_info['resp_key']==resp_go: 
                if trial_info['correct']:
                    trial_info['total_reward']+= reward_info['conv_factor']
                    progress_bar.width += 250*reward_info['conv_factor']
                    progress_bar.pos[0] += 250*(reward_info['conv_factor']/2)
                else:
                    trial_info['total_reward']-= reward_info['conv_factor']
                    progress_bar.width -= (250*reward_info['conv_factor'])
                    progress_bar.pos[0] -= (250*(reward_info['conv_factor']/2))
                if progress_bar.width > 1000:
                    progress_bar.width=reward_info['conv_factor']
                    progress_bar.pos[0] = -500                
                elif progress_bar.width < 10:
                    progress_bar.width=10
                    progress_bar.pos[0] = -500

                # show feedback, depending on context   
                feedback_stims[int(trial_info['correct'])].draw()             

                # add progress bar if in right context
                et.drawCompositeStim([progress_bar,progress_bar_start,progress_bar_end])
                trial_info['start_feed_time'] = win.flip()                 
                et.sendTriggers(trigger_info['start_fb'],mode=response_info['resp_mode'])
                
                for frame in range(feed_frames):
                    # show feedback, depending on context   
                    feedback_stims[int(trial_info['correct'])].draw()             

                    # add progress bar if in right context
                    et.drawCompositeStim([progress_bar,progress_bar_start,progress_bar_end])  
                    win.flip()            
                    
                trial_info['end_feed_time'] = core.getTime()
                # timing checks      
                trial_info['feedbackDur'] = trial_info['end_feed_time']-trial_info['start_feed_time']

        # trial off time
        trial_info['end_trial_time'] = core.getTime()
        if trial_info['trial_count'] == 1:
            data_logger = et.Logger(outpath=output_file,nameDict = trial_info,first_columns = logging_info['first_columns'])
        data_logger.writeTrial(trial_info)

    # update the previous greeble which codes the last greeble in a miniblock
    prev_item = trial_info['stim']
    # end of miniblock message
    trial_info['end_block_time'] = core.getTime()

# end of experiment message + total feedback
if trial_info['sess_type'] != 'practice':
    endExp.text = 'Fertig. Deine Accuracy ist {}%'.format(int(100*trial_info['total_correct']/trial_info['trial_count']))
else:
    endExp.text = stim_info['exp_outro'].format(max(0,trial_info['total_reward']))

if response_info['run_mode'] != 'dummy':
    while True:
        endExp.draw()
        win.flip()
        cont=et.captureResponse(mode=response_info['resp_mode'],keys = [pause_resp])    
        if cont == pause_resp:
            break
#cleanup
et.finishExperiment(win,data_logger,sort='lazy',show_results=True)