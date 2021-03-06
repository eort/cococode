import pandas as pd                 # handy data table tools
import seaborn as sns               # plotting
import matplotlib.pyplot as plt     # plotting
import os,sys,json,glob             # file management and system libraries

def runAnal(path):
    # some overhead
    assert os.path.isdir(path) 
    allFiles = sorted(glob.glob(os.path.join(path,'sub-*/ses-scr/beh/') + 'sub-*_ses-scr_task-rdm_*.csv'))
    pdList = [pd.read_csv(f) for f in allFiles]
    try:
        allDat = pd.concat(pdList, axis=0, ignore_index=True,sort=True)
    except ValueError as e:
        print("ERROR: There are no files in this directory")
        sys.exit(-1)        
    outpath=os.path.join(path,'results','rdm_group_behav.png')
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    #####################
    ###    PREPROC   ####
    #####################
    allDat = allDat.dropna(subset=['resp_key'])
    allDat['direction']=[-1 if c else 1 for c in allDat.cur_dir]   
    allDat['cur_coherence'] = allDat['cur_coherence']*100
    allDat['dirCoh']  = allDat['direction'] * allDat['cur_coherence']
    allDat['resp_time'] *= 1000
    allDat.loc[allDat['cur_coherence'] == 0.0,'correct'] = 0.5 
    if 'left' in allDat.resp_key.unique():
        allDat['response'] = allDat.resp_key.replace({'left':0,'right':1})
    else:
        allDat['response'] = allDat.resp_key.replace({51200:0,53248:1})        
    
    #####################
    ###   AGGREGATE  ####
    #####################
    # ACC and RT over unsigned coherence
    firstlvl= allDat.groupby(['sub_id','ses_id','cur_coherence'])[['correct','resp_time']].mean().reset_index() # time between successive switches
    secondlvl= firstlvl.groupby(['sub_id','cur_coherence'])[['correct','resp_time']].mean().reset_index() # time between successive switches
    thirdlvl= secondlvl.groupby(['cur_coherence'])[['correct','resp_time']].mean().reset_index() 

    # ACC and RT over signed coherence
    firstlvl_pf=allDat.groupby(['sub_id','ses_id','dirCoh'])[['response','resp_time']].mean().reset_index()
    secondlvl_pf= firstlvl_pf.groupby(['sub_id','dirCoh'])[['response','resp_time']].mean().reset_index() 
    thirdlvl_pf= secondlvl_pf.groupby(['dirCoh'])[['response','resp_time']].mean().reset_index()

    #####################
    ###   PLOTTING   ####
    #####################
    max_coh =  allDat.cur_coherence.max()+10
    min_coh =  -max_coh
    thirdlvl_pf.response = thirdlvl_pf.response*100
    thirdlvl.correct =  thirdlvl.correct*100

    fig,axs = plt.subplots(2,2,constrained_layout=1)
    sns.scatterplot(x="dirCoh", y="response", data=thirdlvl_pf,ax = axs[0,0])
    sns.lineplot(x="dirCoh", y="response", data=thirdlvl_pf,ax = axs[0,0])
    axs[0,0].axhline(50,0, ls='--')
    axs[0,0].set(xlabel='Dot Coherence (%)', ylabel='Response right (%)', xlim=(min_coh,max_coh),ylim = (0,100) )

    axs[0,1].set(xlim=(min_coh,max_coh))
    sns.scatterplot(x="dirCoh", y="resp_time", data=thirdlvl_pf,ax = axs[0,1])
    sns.lineplot(x="dirCoh", y="resp_time", data=thirdlvl_pf,ax = axs[0,1])
    axs[0,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (%)')

    axs[1,0].set(xlim=(0,max_coh))
    sns.scatterplot(x="cur_coherence", y="correct", data=thirdlvl,ax = axs[1,0])
    sns.lineplot(x="cur_coherence", y="correct", data=thirdlvl,ax = axs[1,0])
    axs[1,0].set(xlabel='Dot Coherence (%)', ylabel='Percentage Correct (%)',ylim = (0,100) )
    axs[1,0].axhline(50,0, ls='--')

    axs[1,1].set(xlim=(0,max_coh))
    sns.scatterplot(x="cur_coherence", y="resp_time", data=thirdlvl,ax = axs[1,1])
    sns.lineplot(x="cur_coherence", y="resp_time", data=thirdlvl,ax = axs[1,1])
    axs[1,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (%)')

    fig.savefig(outpath)
    plt.close() 

if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except IndexError as e:
        print("ERROR: Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(path)