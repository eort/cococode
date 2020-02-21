from psychopy import visual,event,core,logging
import pandas as pd
import os
import anal
import random
from IPython import embed as shell

def prepDirectories():
    """
    make folders that are expected to exist
    """
    dirs = ['log','dat']
    for arg in dirs:
        if not os.path.exists(arg):
              os.makedirs(arg)   

def captureResponse(mode='meg',key = 'm',timeout=1):
    """
    Depending on the machine the experiment is running on, it either captures response from
    parallel port (mode='meg'), randomly (mode='dummy') or by key press (keyboard)
    """    
    if mode=='meg':
        return os.system("/usr/local/bin/pin 0x379")
    elif mode=='dummy':
        core.wait(timeout)
        return random.choice([key,None])
    elif mode=='keyboard':
        resp = event.waitKeys(keyList=[key], maxWait=timeout, timeStamped=False)
        if resp != None: return resp[0] 
        else: return resp   

def fancyFixDot(window,bg_color,fg_color='white',size=30):
    """
    Objectively the best fixation dot: https://www.sciencedirect.com/science/article/pii/S0042698912003380
    No costumization implemented
    """
    # define two circles and a cross
    bigCircle = visual.Circle(win=window, size=size,units="pix", pos=[0,0],lineColor=fg_color,fillColor=fg_color)
    rect_horiz = visual.Rect(win=window,units="pix",width=size,height=size/6,fillColor=bg_color,lineColor=bg_color)
    rect_vert = visual.Rect(win=window,units="pix",width=size/6,height=size,fillColor=bg_color,lineColor=bg_color)
    smallCircle = visual.Circle(win=window, size=size/6,units="pix", pos=[0,0],lineColor=fg_color,fillColor=fg_color)
    return [bigCircle,rect_horiz,rect_vert,smallCircle]

def finishExperiment(window,dataLogger,sort='lazy',show_results=False):
    """gracefully finish experiment"""
    window.close()
    dataLogger.write2File(sort=sort)
    if show_results:
        anal.runAnal(dataLogger.outpath)
    core.quit()

def sendTriggers(trigger,mode=None):
    """
    make code easier to read by combining sending triggers with the timeout 
    """
    if mode == 'meg':
        os.system("/usr/local/bin/parashell 0x378 {}".format(trigger))
        core.wait(0.01)
        os.system("/usr/local/bin/parashell 0x378 0")   
        core.wait(0.01)

class Logger(object):
    """
    A class to set up a data logger file, log the data, and store the data as a panda dataframe
    csv file
    """
    def __init__(self,outpath,nameDict):
        self.columns = nameDict.keys()
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

    def write2File(self,sort='regular'):
        # make directories if they don't exist yet
        if not os.path.exists(self.outdir): 
            os.makedirs(self.outdir)

        if sort == 'regular':
            self.data = self.data[sorted(self.data.columns.tolist())]
        elif sort == 'lazy':
            self.data = self.data[sorted(self.data.columns.tolist())]
            first = ['name','expID','sub_id','sess_id','trial_count','block_no','trial_no','context','condition','correct','resp_time','total_correct','total_euro']
            try:
                new_order = first + list(self.data.columns.drop(first))
            except KeyError as e:
                print("Can't do sorting because one of the specified columns does not exist. Save file without sorting")
            else: 
                self.data = self.data.reindex(columns=new_order)
        self.data.to_csv(self.outpath,na_rep=pd.np.nan)        
