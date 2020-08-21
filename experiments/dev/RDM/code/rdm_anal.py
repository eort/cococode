import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
import os,sys
import glob

def runAnal(datFolder):
    if not os.path.isfile(datFolder):
        allFiles = sorted(glob.glob('../sub-*/ses-*/beh/' + datFolder + '.csv'))
        inFiles=[]
        for f in allFiles:
            if os.stat(f).st_size>100000: inFiles.append(f) 
        pdList = [pd.read_csv(f) for f in inFiles]
        allDat = pd.concat(pdList, axis=0, ignore_index=True)
        outpath=os.path.join('group_results.png')
    else:
        allDat = pd.read_csv(datFolder)
        outpath= datFolder.replace('csv','png')

    #####################
    ###    PREPROC   ####
    #####################
    allDat['direction']=[-1 if c else 1 for c in allDat.cur_dir]   
    allDat['cur_coherence'] = allDat['cur_coherence']*100
    allDat['dirCoh']  = allDat['direction'] * allDat['cur_coherence']
    allDat = allDat.dropna(subset=['resp_key'])
    allDat['resp_time'] = allDat['resp_time'] *1000
    allDat['correct'].loc[allDat['cur_coherence'] == 0.0] = 0.5 

    #####################
    ###   AGGREGATE  ####
    #####################
    # ACC and RT over unsigned coherence
    firstlvl= allDat.groupby(['sub_id','ses_id','cur_coherence'])['correct','resp_time'].mean().reset_index() # time between successive switches
    secondlvl= firstlvl.groupby(['sub_id','cur_coherence'])['correct','resp_time'].mean().reset_index() # time between successive switches
    thirdlvl= secondlvl.groupby(['cur_coherence'])['correct','resp_time'].mean().reset_index() 

    # ACC and RT over signed coherence
    f  = lambda x: x[x.str.contains('right')].count() / x.count()
    firstlvl_pf= allDat.groupby(['sub_id','ses_id','dirCoh'])['resp_key'].apply(f).reset_index() 
    # compute mean response time
    firstlvl_rt= allDat.groupby(['sub_id','ses_id','dirCoh'])['resp_time'].mean().reset_index() 
    # combine the two data frames
    firstlvl_pf['resp_time'] = firstlvl_rt['resp_time']
    secondlvl_pf= firstlvl_pf.groupby(['sub_id','dirCoh'])['resp_key','resp_time'].mean().reset_index() 
    thirdlvl_pf= secondlvl_pf.groupby(['dirCoh'])['resp_key','resp_time'].mean().reset_index()

    #####################
    ###   PLOT       ####
    #####################
    max_coh =  allDat.cur_coherence.max()+10
    min_coh =  - max_coh

    if not os.path.isfile(datFolder):
        thirdlvl_pf.resp_key = thirdlvl_pf.resp_key*100
        thirdlvl.correct = thirdlvl.correct*100

        fig,axs = plt.subplots(2,2,constrained_layout=1)
        #axs[0,0].set()
        sns.scatterplot(x="dirCoh", y="resp_key", data=thirdlvl_pf,ax = axs[0,0])
        sns.lineplot(x="dirCoh", y="resp_key", data=thirdlvl_pf,ax = axs[0,0])
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

    else:
        for idx,sub_id in enumerate(secondlvl.sub_id.unique()):
            thirdlvl_pf = secondlvl_pf[secondlvl_pf.sub_id == sub_id]
            thirdlvl = secondlvl[secondlvl.sub_id == sub_id]
            thirdlvl_pf.resp_key = thirdlvl_pf.resp_key*100
            thirdlvl.correct = thirdlvl.correct*100
            
            fig,axs = plt.subplots(2,2,constrained_layout=1)
            sns.scatterplot(x="dirCoh", y="resp_key", data=thirdlvl_pf,ax = axs[0,0])
            sns.lineplot(x="dirCoh", y="resp_key", data=thirdlvl_pf,ax = axs[0,0])
            axs[0,0].axhline(50,0, ls='--')
            axs[0,0].set(xlabel='Dot Coherence (%)', ylabel='Response right (%)', xlim=(min_coh,max_coh),ylim = (0,100) )

            axs[0,1].set(xlim=(min_coh,max_coh))
            sns.scatterplot(x="dirCoh", y="resp_time", data=thirdlvl_pf,ax = axs[0,1])
            sns.lineplot(x="dirCoh", y="resp_time", data=thirdlvl_pf,ax = axs[0,1])
            axs[0,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (%)')

            sns.scatterplot(x="cur_coherence", y="correct", data=thirdlvl,ax = axs[1,0])
            sns.lineplot(x="cur_coherence", y="correct", data=thirdlvl,ax = axs[1,0])
            axs[1,0].set(xlabel='Dot Coherence (%)', ylabel='Percentage correct (%)', ylim = (0,100) )
            axs[1,0].axhline(50,0, ls='--')

            axs[1,1].set(xlim=(0,max_coh))
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