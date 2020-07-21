from psychopy import visual,event,core,logging
import pandas as pd
import os
import random

def drawFlip(win, stim):
    """
    combines drawing and window flipping
    """
    drawCompositeStim(stim)
    timestamp = win.flip()
    return timestamp

def prepDirectories():
    """
    make folders that are expected to exist
    """
    dirs = ['log','dat','settings']
    for arg in dirs:
        if not os.path.exists(arg):
              os.makedirs(arg)   

def captureResponseMEG(keys = ['m',None]):
    """
    system call to read out parallel port
    """    
    return os.system("/usr/local/bin/pin 0x379")
    
def captureResponseKB(keys = ['m',None]):
    """
    poll a keyboard response
    """
    resp = event.getKeys()
    if len(resp)>0: return resp[-1]
    return None   

def captureResponseDummy(keys = ['m',None]):
    """
    poll a keyboard response
    """
    return random.choice(keys)

def drawCompositeStim(stim_list):
    """
    Convenience function for readability. Loops over the list and draws all of it. 
    """
    for stim in stim_list:
        stim.draw()

def fancyFixDot(window,bg_color,fg_color='white',size=0.4):
    """
    Objectively the best fixation dot: https://www.sciencedirect.com/science/article/pii/S0042698912003380
    draws in degrees
    """
    # define two circles and a cross
    bigCircle = visual.Circle(win=window, size=size, pos=[0,0],lineColor=fg_color,fillColor=fg_color,autoLog=0)
    rect_horiz = visual.Rect(win=window,width=size,height=size/6,fillColor=bg_color,lineColor=bg_color,autoLog=0)
    rect_vert = visual.Rect(win=window,width=size/6,height=size,fillColor=bg_color,lineColor=bg_color,autoLog=0)
    smallCircle = visual.Circle(win=window, size=size/6, pos=[0,0],lineColor=fg_color,fillColor=fg_color,autoLog=0)
    return [bigCircle,rect_horiz,rect_vert,smallCircle]

def finishExperiment(window,dataLogger,sort='lazy',show_results=False):
    """gracefully finish experiment"""
    window.close()
    dataLogger.write2File(sort=sort)
    if show_results:
        import anal
        anal.runAnal(dataLogger.outpath)
    core.quit()

def sendTriggers(trigger,reset=0.012,prePad=0):
    """
    make code easier to read by combining sending triggers with the timeout 
    """
    core.wait(prePad)
    os.system("/usr/local/bin/parashell 0x378 {}".format(trigger))
    if reset:
        core.wait(reset)
        os.system("/usr/local/bin/parashell 0x378 0")

class Logger(object):
    """
    A class to set up a data logger file, log the data, and store the data as a panda dataframe
    csv file
    """
    def __init__(self,outpath,nameDict,first_columns):
        self.columns = nameDict.keys()
        self.outpath= outpath
        self.outdir= os.path.dirname(outpath)

        if len(self.columns)!=len(set(self.columns)):
            logging.warn("There are duplicate file names in the logfile!")

        self.data = pd.DataFrame(columns=self.columns)
        self.defaultTrial = nameDict
        self.curRowIdx = 0
        self.first_columns = first_columns

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
            first = self.first_columns
            try:
                new_order = first + list(self.data.columns.drop(first))
            except KeyError as e:
                print("Can't do sorting because one of the specified columns does not exist. Save file without sorting")
            else: 
                self.data = self.data.reindex(columns=new_order)
        self.data.to_csv(self.outpath,na_rep=pd.np.nan)        
