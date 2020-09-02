import pandas as pd                 # handy data table tools
import seaborn as sns               # plotting
import matplotlib.pyplot as plt     # plotting
import os,sys,json,glob             # file management and system libraries

def runAnal(dat_file):
    assert os.path.isfile(dat_file)
    allDat = pd.read_csv(dat_file)
    outpath= dat_file.replace('csv','png').replace('beh','results')
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
    allDat['response'] = allDat.resp_key.replace({allDat.resp_key.unique()[1]:1,allDat.resp_key.unique()[0]:0})
    
    #####################
    ###   AGGREGATE  ####
    #####################
    # ACC and RT over unsigned coherence
    firstlvl= allDat.groupby(['cur_coherence'])[['correct','resp_time']].mean().reset_index() 
    # ACC and RT over signed coherence
    firstlvl_pf= allDat.groupby(['dirCoh'])[['response','resp_time']].mean().reset_index() 
 
    #####################
    ###   PLOTTING   ####
    #####################
    max_coh =  allDat.cur_coherence.max()+10
    min_coh =  -max_coh
    firstlvl_pf.response = firstlvl_pf.response*100
    firstlvl.correct = firstlvl.correct*100
    
    fig,axs = plt.subplots(2,2,constrained_layout=1)
    sns.scatterplot(x="dirCoh", y="response", data=firstlvl_pf,ax = axs[0,0])
    sns.lineplot(x="dirCoh", y="response", data=firstlvl_pf,ax = axs[0,0])
    axs[0,0].axhline(50,0, ls='--')
    axs[0,0].set(xlabel='Dot Coherence towards left (-) or right(+) (%)', ylabel='Response right (%)', xlim=(min_coh,max_coh),ylim = (0,100) )

    axs[0,1].set(xlim=(min_coh,max_coh))
    sns.scatterplot(x="dirCoh", y="resp_time", data=firstlvl_pf,ax = axs[0,1])
    sns.lineplot(x="dirCoh", y="resp_time", data=firstlvl_pf,ax = axs[0,1])
    axs[0,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (ms)')

    sns.scatterplot(x="cur_coherence", y="correct", data=firstlvl,ax = axs[1,0])
    sns.lineplot(x="cur_coherence", y="correct", data=firstlvl,ax = axs[1,0])
    axs[1,0].set(xlabel='Dot Coherence (%)', ylabel='Percentage correct (%)', ylim = (0,100) )
    axs[1,0].axhline(50,0, ls='--')

    axs[1,1].set(xlim=(0,max_coh))
    sns.scatterplot(x="cur_coherence", y="resp_time", data=firstlvl,ax = axs[1,1])
    sns.lineplot(x="cur_coherence", y="resp_time", data=firstlvl,ax = axs[1,1])
    axs[1,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (ms)')

    fig.savefig(outpath)
    plt.close() 

if __name__ == '__main__':
    try:
        inf = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(inf)