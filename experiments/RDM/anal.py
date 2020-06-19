import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
import os,sys
import glob
from IPython import embed as shell


def runAnal(datFolder):
    if not os.path.isfile(datFolder):
        inFiles = sorted(glob.glob(datFolder + '/*.csv'))
        pdList = [pd.read_csv(f) for f in inFiles]
        allDat = pd.concat(pdList, axis=0, ignore_index=True)
        outpath=os.path.join(datFolder,'group_results.pdf')
    else:
        allDat = pd.read_csv(datFolder)
        outpath= datFolder.replace('csv','png')

    #preprocess
    direction  = [-1 if c else 1 for c in allDat.cur_dir]          
    allDat['direction']  =direction
    allDat['cur_coherence'] = allDat['cur_coherence']*100
    allDat['dirCoh']  = allDat['direction'] * allDat['cur_coherence']
    allDat = allDat.dropna(subset=['resp_key'])
    allDat['resp_time'] = allDat['resp_time'] *1000

    #aggregate
    shell()
    # plot correct and response time
    firstlvl= allDat.groupby(['sub_id','sess_id','cur_coherence'])['correct','resp_time'].mean().reset_index() # time between successive switches
    secondlvl= firstlvl.groupby(['sub_id','cur_coherence'])['correct','resp_time'].mean().reset_index() # time between successive switches
    thirdlvl= secondlvl.groupby(['cur_coherence'])['correct','resp_time'].mean().reset_index() # time between successive switches

    # plot psychometric function
    f  = lambda x: x[x.str.contains('right')].count() / x.count()
    firstlvl_pf= allDat.groupby(['sub_id','sess_id','dirCoh'])['resp_key'].apply(f).reset_index() # time between successive switches
    firstlvl_rt= allDat.groupby(['sub_id','sess_id','dirCoh'])['resp_time'].mean().reset_index() # time between successive switches
    firstlvl_pf['resp_time'] = firstlvl_rt['resp_time']

    secondlvl_pf= firstlvl_pf.groupby(['sub_id','dirCoh'])['resp_key','resp_time'].mean().reset_index() # time between successive switches
    thirdlvl_pf= secondlvl_pf.groupby(['dirCoh'])['resp_key','resp_time'].mean().reset_index() # time between successive switches

    # plot
    thirdlvl_pf.resp_key = thirdlvl_pf.resp_key*100
    thirdlvl.correct = thirdlvl.correct*100

    fig,axs = plt.subplots(2,2,constrained_layout=1)
    #axs[0,0].set()
    sns.scatterplot(x="dirCoh", y="resp_key", data=thirdlvl_pf,ax = axs[0,0])
    sns.lineplot(x="dirCoh", y="resp_key", data=thirdlvl_pf,ax = axs[0,0])
    axs[0,0].axhline(50,0, ls='--')
    axs[0,0].set(xlabel='Dot Coherence (%)', ylabel='Response right (%)', xlim=(-60,60),ylim = (0,100) )

    axs[0,1].set(xlim=(-60,60))
    sns.scatterplot(x="dirCoh", y="resp_time", data=thirdlvl_pf,ax = axs[0,1])
    sns.lineplot(x="dirCoh", y="resp_time", data=thirdlvl_pf,ax = axs[0,1])
    axs[0,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (%)')

    axs[1,0].set(xlim=(0,60))
    sns.scatterplot(x="cur_coherence", y="correct", data=thirdlvl,ax = axs[1,0])
    sns.lineplot(x="cur_coherence", y="correct", data=thirdlvl,ax = axs[1,0])
    axs[1,0].set(xlabel='Dot Coherence (%)', ylabel='Percentage Correct (%)')
    axs[1,0].axhline(50,0, ls='--')

    axs[1,1].set(xlim=(0,60))
    sns.scatterplot(x="cur_coherence", y="resp_time", data=thirdlvl,ax = axs[1,1])
    sns.lineplot(x="cur_coherence", y="resp_time", data=thirdlvl,ax = axs[1,1])
    axs[1,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (%)')
    if not os.path.isfile(datFolder):
        fig.savefig(outpath)
        plt.close() 

    for idx,sub_id in enumerate(secondlvl.sub_id.unique()):
        thirdlvl_pf = secondlvl_pf[secondlvl_pf.sub_id == sub_id]
        thirdlvl = secondlvl[secondlvl.sub_id == sub_id]
        thirdlvl_pf.resp_key = thirdlvl_pf.resp_key*100
        thirdlvl.correct = thirdlvl.correct*100
        
        fig,axs = plt.subplots(2,2,constrained_layout=1)
        sns.scatterplot(x="dirCoh", y="resp_key", data=thirdlvl_pf,ax = axs[0,0])
        sns.lineplot(x="dirCoh", y="resp_key", data=thirdlvl_pf,ax = axs[0,0])
        axs[0,0].axhline(50,0, ls='--')
        axs[0,0].set(xlabel='Dot Coherence (%)', ylabel='Response right (%)', xlim=(-60,60),ylim = (0,100) )

        axs[0,1].set(xlim=(-60,60))
        sns.scatterplot(x="dirCoh", y="resp_time", data=thirdlvl_pf,ax = axs[0,1])
        sns.lineplot(x="dirCoh", y="resp_time", data=thirdlvl_pf,ax = axs[0,1])
        axs[0,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (%)')

        sns.scatterplot(x="cur_coherence", y="correct", data=thirdlvl,ax = axs[1,0])
        sns.lineplot(x="cur_coherence", y="correct", data=thirdlvl,ax = axs[1,0])
        axs[1,0].set(xlabel='Dot Coherence (%)', ylabel='Percentage correct (%)', xlim=(-60,60),ylim = (0,100) )
        axs[1,0].axhline(50,0, ls='--')

        axs[1,1].set(xlim=(0,60))
        sns.scatterplot(x="cur_coherence", y="resp_time", data=thirdlvl,ax = axs[1,1])
        sns.lineplot(x="cur_coherence", y="resp_time", data=thirdlvl,ax = axs[1,1])
        axs[1,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (%)')

        fig.savefig(outpath)
        plt.close() 


if __name__ == '__main__':
    try:
        datFolder = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(datFolder)