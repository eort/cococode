from psychopy import visual,event,core,logging
import pandas as pd
import os
import anal
from IPython import embed as shell

def prepDirectories():
    """
    make folders that are expected to exist
    """
    dirs = ['log','dat']
    for arg in dirs:
        if not os.path.exists(arg):
              os.makedirs(arg)   

def fancyFixDot(window,bg_color,fg_color='white'):
    """
    Objectively the best fixation dot: https://www.sciencedirect.com/science/article/pii/S0042698912003380
    No costumization implemented
    """
    # define two circles and a cross
    bigCircle = visual.Circle(win=window, size=30,units="pix", pos=[0,0],lineColor=fg_color,fillColor=fg_color)
    rect_horiz = visual.Rect(win=window,units="pix",width=30,height=5,fillColor=bg_color,lineColor=bg_color)
    rect_vert = visual.Rect(win=window,units="pix",width=5,height=30,fillColor=bg_color,lineColor=bg_color)
    smallCircle = visual.Circle(win=window, size=6,units="pix", pos=[0,0],lineColor=fg_color,fillColor=fg_color)
    return [bigCircle,rect_horiz,rect_vert,smallCircle]


def handleResponse(start_time,corr_resp,resp=None,sleep=None,allowed_resp=None):
    """Function supposed to handle 2 scenarios:
        1) process an already pressed key to format into response dict
        2) poll for more responses if nothing has been pressed yet
        returns a response dict with the key pressed, response time, and correctness
    """

    response = dict(resp_key=None,resp_time=None,correct=None,timeout=0)

    if resp != None:
        response['resp_key']=resp[0]
        response['resp_time'] = resp[-1]-start_time
    else:
        keys = event.waitKeys(keyList=[allowed_resp[0],allowed_resp[1],allowed_resp[2]], maxWait=sleep, timeStamped=True)

        if keys== None:
            response['resp_key']=None
            response['timeout']=1
        elif allowed_resp[0] in keys[-1]:
            response['resp_key'] = allowed_resp[0]
        elif allowed_resp[1] in keys[-1]:
            response['resp_key'] = allowed_resp[1]
            response['resp_time'] = keys[-1][-1]-start_time
        elif allowed_resp[2] in keys[-1]:
            response['resp_key'] = allowed_resp[2]
            response['resp_time'] = keys[-1][-1]-start_time
    
    response['correct'] = response['resp_key']==corr_resp
    return response

def finishExperiment(window,dataLogger,show_results=False):
    """gracefully finish experiment"""
    window.close()
    dataLogger.write2File()
    if show_results:
        anal.runAnal(dataLogger.outpath)
    core.quit()


def repCheck(seq,cutoff=4):
    """Checks whether too many repetitions of the same category in a binary sequence
    Retuns 1 if so, 0 if not
    """
    for sI,s in enumerate(seq[cutoff-1:]):
        if sum(seq[sI:cutoff+sI]) in [0,cutoff]:
            return 1
    return 0

class Logger(object):
    """
    A class to set up a data logger file, log the data, and store the data as a panda dataframe
    csv file
    """
    def __init__(self,outpath,nameDict):
        self.columns = nameDict.keys()
        self.trial_dict = dict()
        self.outpath= outpath
        self.outdir= os.path.dirname(outpath)

        if len(self.columns)!=len(set(self.columns)):
            logging.warn("There are duplicate file names in the logfile!")

        self.data = pd.DataFrame(columns=self.columns)
        self.defaultTrial = nameDict
        self.curRowIdx = 0

    def updateDefaultTrial(self,key,value):
        self.defaultTrial[key]= value

    def writeTrial(self,trial_info):
        self.data.loc[self.curRowIdx]=trial_info
        self.curRowIdx += 1

    def write2File(self):
        # make directories if they don't exist yet
        if not os.path.exists(self.outdir): 
            os.makedirs(self.outdir)
        self.data = self.data[sorted(self.data.columns.tolist())]
        self.data.to_csv(self.outpath,na_rep=pd.np.nan)        
