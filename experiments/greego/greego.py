# created by Eduard Ort, 2019 
# based on Matlab code by Hannah Kurtenbach
from psychopy import visual, core, event,gui,logging,data #import some libraries from PsychoPy
from IPython import embed
import expTools as et
import json
import sys, os
from datetime import datetime
import numpy as np
import glob
from IPython import embed as shell
#######################
###  load settings  ###
#######################
try:
    jsonfile = sys.argv[1]
except IndexError as e:
    print("No config file provided. Load default settings")
    jsonfile = 'default_cfg.json'
with open(jsonfile) as f:    
    param = json.load(f)

####################
###  Overhead    ###
####################
# read out json sidecar
n_trials = param['n_trials']            # number trials per block
n_blocks = param['n_blocks']            # number total blocks
n_exem = param['n_exem']                # number trials per block
n_fams = param['n_fams']                # number total blocks
stim_sleep = param['stim_sleep']        # presentation duration of stim
resp_sleep = param['resp_sleep']        # time window to give response after stim
fix_sleep_mean = param['fix_mean']      # presentation duration of fixdot
fix_sleep_range = param['fix_range']    # presentation duration of fixdot
feed_sleep = param['feed_sleep']        # presentation duration of feedback
startexp_text = param['startexp_text']   # block start message
blockOut_reward = param['blockOut_rew'] # block end message for reward context
exp_outro = param['exp_outro']          # experiment end message
total_euro = param['total_euro']        # start amount of cash
practice = param['practice']
# get session data
start_exp_time = core.getTime()

input_dict = dict(sub_id=0,sess_id=0,practice=practice)
inputGUI =gui.DlgFromDict(input_dict,title='Experiment Info',order=['sub_id','sess_id'])
# write log file for all events that occurred
et.prepDirectories()
logFile = os.path.join('log',param['logFile'].format(input_dict['sub_id'],input_dict['sess_id'],datetime.now()).replace(' ','-').replace(':','-'))
lastLog = logging.LogFile(logFile, level=logging.INFO, filemode='w')

# counterbalance the greebles that are used

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

# load greeble info
image_paths = sorted(glob.glob(os.path.join(imageDir,'*.tif')))
if not practice:
    families = [image_paths[:n_exem],image_paths[n_exem:2*n_exem],image_paths[2*n_exem:]]
else:
    families = [[image_paths[0]],[image_paths[1]]]

# how many times each stimulus
n_unique = n_exem*n_fams
n_repeats = n_trials//n_unique
if n_trials%n_unique != 0:
    print('WARNING: {} unique trials cannot be shown equally often in {} trials.'.format(n_unique,n_trials))
    logging.warning('WARNING: {} unique orientations cannot be shown equally often in {} trials.'.format(n_unique,n_trials))

# initialize the previous item, to make coding easier
prev_item = None

# create a logger file that collects all variables
output_file = os.path.join('dat',param['expID'],param['output_file'].format(input_dict['sub_id'],input_dict['sess_id'],datetime.now()).replace(' ','-').replace(':','-'))
data_logger = et.Logger(outpath=output_file,nameDict = param)
# update the constance values
updateDict = dict(blockOut_rew=None,
                    exp_outro=None,
                    start_exp_time=start_exp_time,
                    output_file=output_file,
                    logFile=logFile,
                    practice=input_dict['practice'],
                    sub_id = input_dict['sub_id'],
                    sess_id = input_dict['sess_id'])
for k,v in updateDict.items():
    data_logger.updateDefaultTrial(k,v)
# a helper dict to collect variables
trial_info = data_logger.defaultTrial
####################
###  experiment  ###
####################
#create a window
mywin = visual.Window(size=param['win_size'],color=param['bg_color'],fullscr=param['fullscreen'],monitor="testMonitor", units="pix",screen=1)

#########################
###  prepare stimuli  ###
#########################
# first all kind of structural messages
greeble = visual.ImageStim(mywin,image=image_paths[0],size=(240,270))
startexp = visual.TextStim(mywin,text=startexp_text,color=param['fg_color'],wrapWidth=mywin.size[0])
endBlockRew = visual.TextStim(mywin,text=blockOut_reward,color=param['fg_color'],wrapWidth=mywin.size[0])
endExp = visual.TextStim(mywin,text=exp_outro,color=param['fg_color'],wrapWidth=mywin.size[0])
pause = visual.TextStim(mywin,text='Kurze Pause\nLeertase zum Weitermachen',color=param['fg_color'],wrapWidth=mywin.size[0])
progress_bar =visual.Rect(mywin,width=10,height=20,lineColor=param['fg_color'],fillColor=param['fg_color'],pos = [-500,-200])
progress_bar_start =visual.Rect(mywin,width=10,height=20,lineColor=param['fg_color'],fillColor=param['fg_color'],pos = [-500,-200])
progress_bar_end =visual.Rect(mywin,width=10,height=20,lineColor=param['fg_color'],fillColor=param['fg_color'],pos = [500,-200])
fixDot = et.fancyFixDot(mywin, bg_color = param['bg_color']) # fixation dot
smiley = visual.ImageStim(mywin,'smiley.png') # good feedback
frowny = visual.ImageStim(mywin,'frowny.png') # bad feedback

# combine feedback stims to make it easier later
feedback_stims = [frowny,smiley]

####################
###  block loop  ###
####################
# show intro before starting experiment
startexp.draw()
mywin.flip()
event.waitKeys(keyList = ['space'])
    
# assign stimuli to go and no go category
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
        
trial_info['go_stim'] = go_stim
trial_info['nogo_stim'] = nogo_stim
# reset block variables
trial_info['total_correct'] = 0

for block_no in range(n_blocks):
    # we use fake blocks here. Better word would be building blocks
    # blocks are not separated by a pause screen or something like that
    # instead pauses are only added occasionally (predefined)

    # create trial sequence (within 12 trials, gos and nogos are equal)
    trial_seq = [0,1]*int(n_unique/2)
    trial_seq = trial_seq*n_repeats
    np.random.shuffle(trial_seq)

    # make go and nogo sequences
    np.random.shuffle(go_stim)
    np.random.shuffle(nogo_stim)

    # make sure twice the same stimulus in a row does not happen
    if not practice:
        while prev_item in [go_stim[0],nogo_stim[0]]:
            np.random.shuffle(go_stim)    
            np.random.shuffle(nogo_stim)
    go_seq=list(go_stim)
    nogo_seq=list(nogo_stim)
    
    # define correct response and sequence of go/nogo trials
    corr_resp_seq = [param['resp1'] if i==0 else param['resp2'] for i in trial_seq ]
    gonogo_seq = ['go' if i==1 else 'nogo' for i in trial_seq ]
    stim_seq = [go_seq.pop() if i==1 else nogo_seq.pop() for i in trial_seq]

    # pause 
    if block_no+1 in trial_info['pause_blocks']:
        pause.draw()
        mywin.flip()
        event.waitKeys(keyList = ['space'])

    # time when block started
    trial_info['start_block_time'] = core.getTime()
    trial_info['block_no']=block_no+1
    
    # define context (based on pre-defined length and timing of noreward blocks)
    if block_no+1 in trial_info['noreward_blocks']:
        trial_info['context'] = 'no_reward'
    else:
        trial_info['context'] = 'reward' 

    ####################
    ###  trial loop  ###
    ####################
    for trial_no in range(n_trials):
        trial_info['trial_no'] = trial_no+1
        trial_info['trial_count']+=1

        if trial_info['context'] == 'reward':    
            # draw progress bar
            progress_bar.draw()    
            progress_bar_start.draw()
            progress_bar_end.draw()  

        # draw fixation and wait for 
        for elem in fixDot:
            elem.draw()        
        mywin.flip()
        trial_info['start_trial_time'] = core.getTime()

        # jitter the fix duration
        trial_info['fix_sleep'] = np.random.uniform(fix_sleep_mean-fix_sleep_range,fix_sleep_mean+fix_sleep_range)
        core.wait(trial_info['fix_sleep'])

        # set specific orientations
        trial_info['condition'] = gonogo_seq[trial_no]
        trial_info['stim'] = stim_seq[trial_no]
        trial_info['corr_resp'] = corr_resp_seq[trial_no]
        greeble.setImage(trial_info['stim'])
        
        # clear any pending key presses
        event.clearEvents()
        # draw stimulus
        greeble.draw()
        if trial_info['context'] == 'reward':
            progress_bar.draw()    
            progress_bar_start.draw()
            progress_bar_end.draw()   
            
        mywin.flip()

        if trial_info['context'] == 'reward':    
            progress_bar.draw()    
            progress_bar_start.draw()
            progress_bar_end.draw()   
        
        # start response time measure
        trial_info['start_stim_time']  = core.getTime()
        # sleep for stimulus duration while already waiting for response
        core.wait(stim_sleep,hogCPUperiod=stim_sleep)
        # remove stimulus
        mywin.flip()
        trial_info['end_stim_time'] = core.getTime()

        # check whether key was pressed. If so, process it. If not, wait longer
        resp = event.getKeys(timeStamped=True)
        if len(resp) > 0 and resp[-1][0] in [param['resp1'],param['resp2']]:
            response = et.handleResponse(start_time=trial_info['start_stim_time'],corr_resp = trial_info['corr_resp'],resp=resp[-1])
        else:
            response = et.handleResponse(start_time=trial_info['start_stim_time'],corr_resp = trial_info['corr_resp'],sleep = resp_sleep,allowed_resp = [param['resp_exit'],param['resp1'],param['resp2']])


        trial_info['time_buttonPress'] = core.getTime()
        for resp_key,resp_val in response.items():
            trial_info[resp_key] = resp_val

        # if q was pressed, stop experiment
        if response['resp_key']==param['resp_exit']:
            trial_info['aborted'] = 1
            et.finishExperiment(mywin,data_logger)

        #do reward math
        trial_info['total_correct'] +=response['correct']
        if trial_info['context'] == 'reward':
            if trial_info['resp_key']==param['resp2']: 
                if response['correct']:
                    trial_info['total_euro']+= trial_info['reward_step']
                    progress_bar.width += 250*trial_info['reward_step']
                    progress_bar.pos[0] += 250*(trial_info['reward_step']/2)
                else:
                    trial_info['total_euro']-= trial_info['punish_step']
                    progress_bar.width -= (250*trial_info['punish_step'])
                    progress_bar.pos[0] -= (250*(trial_info['punish_step']/2))
                if progress_bar.width > 1000:
                    progress_bar.width=trial_info['reward_step']
                    progress_bar.pos[0] = -500                
                elif progress_bar.width < 10:
                    progress_bar.width=10
                    progress_bar.pos[0] = -500

                # show feedback, depending on context   
                feedback_stims[response['correct']].draw()
            progress_bar.draw()    
            progress_bar_start.draw()
            progress_bar_end.draw()   

        mywin.flip()
        core.wait(feed_sleep)
        trial_info['end_trial_time'] = core.getTime()
        # log variables
        data_logger.writeTrial(trial_info)

    prev_item = trial_info['stim']
    # end of block message
    trial_info['end_prev_block_time'] = core.getTime()

# end of experiment message
if practice:
    endExp.text = exp_outro.format(int(100*trial_info['total_correct']/trial_info['trial_count']))    
else:
    endExp.text = exp_outro.format(trial_info['total_euro'])
endExp.draw()
mywin.flip()
event.waitKeys(keyList = ['space'], timeStamped=True)      

#cleanup
et.finishExperiment(mywin,data_logger,show_results=True)
