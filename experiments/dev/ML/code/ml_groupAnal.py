import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os,sys,glob,json
import numpy as np
from IPython import embed as shell

def slidingWindow(series,window=5):
    """
    overly complicated because index of panda series have to be taken care of
    """
    new_s =  pd.Series(pd.np.nan, index=series.index,name='mov_avg')
    win_half = window//2
    for tI in range(win_half,series.size-win_half):
        new_s.iloc[tI] = series[tI-win_half:tI+win_half+1].mean()
    return new_s

def plotResults(dat,acc,outpath = 'fig1.pdf'):
    """
    plot ML specific figure: 
    left top panel: absolute score
    other panels: development over time within each unique block length
    """
    # various correct response measures
    sns.set(font_scale=2,style='white')
    fig = plt.figure(figsize=(30,20))
    grid = plt.GridSpec(3, 6)
    ax0=plt.subplot(grid[0,:2])
    ax0=sns.boxplot(x="measure", y="value", data=acc,width=0.5, dodge=1)
    sns.swarmplot(size=15,edgecolor = 'black', x="measure", y="value", data=acc,dodge=1)
    ax0.set(ylim=(30,100), xlabel='Performance measure',ylabel='Accuracy (%)')
    ax0.set_xticklabels(ax0.get_xticklabels(), rotation=30)    
    for j in np.arange(50,100,10):
        ax0.axhline(j, ls='--',color='black')

    for avg_idx,avg in enumerate(dat.phase_length.unique()):
        if avg in [20,40]:
            ax = plt.subplot(grid[1,avg_idx])
        else:
            ax = plt.subplot(grid[1,avg_idx:])
            
        plotData = dat.loc[dat.phase_length==avg,:].copy()
        sns.lineplot(x='trialInPhase_no',y='value',data=plotData)
        ax.axhline(50, ls='--',color='black')
        ax.set(ylim=(20,100), xlabel='Trial in block - all subs',ylabel='Accuracy (%)',title= 'Block length: {}'.format(avg))
    # sliding window plots
    for avg_idx,avg in enumerate(dat.phase_length.unique()):
        if avg in [20,40]:
            ax = plt.subplot(grid[2,avg_idx])
        else:
            ax = plt.subplot(grid[2,avg_idx:])
            
        plotData = dat.loc[dat.phase_length==avg,:].copy()
        if avg in [20,40]:
            sns.lineplot(x='trialInPhase_no',y='value',hue='phase_type_order',data=plotData,legend=False)
        else:
            sns.lineplot(x='trialInPhase_no',y='value',hue='phase_type_order',data=plotData)
            handles, labels = ax.get_legend_handles_labels()
            fig.legend(handles, labels, loc='upper center')            # Put a legend to the right side
                            
        ax.axhline(50, ls='--',color='black')
        ax.set(ylim=(20,100), xlabel='Trial in block',ylabel='Accuracy (%)',title= 'Block length: {}'.format(avg))

    plt.tight_layout()
    plt.savefig(outpath)

def runAnal(path):
    # some overhead
    assert os.path.isdir(path)  
    
    allFiles = sorted(glob.glob(os.path.join(path,'sub-9*/ses-*/beh/') + 'sub*scr*ml*.csv'))
    pdList = [pd.read_csv(f) for f in allFiles]
    allDat = pd.concat(pdList, axis=0, ignore_index=True,sort=True)
    outpath=os.path.join(path,'results','ml_group_results_no_nb.png')
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    # define the current correct responses
    if allDat.loc[1,'ses_id']=='meg':
        left = 51200;right = 53248
    else:
        left = 'left';right = 'right'

    # RL learner
    alpha = 0.10
    rl_prob = np.ones((allDat.shape[0]))*0.5
    for idx,item in enumerate(rl_prob[:-1]):
        rl_prob[idx+1]=rl_prob[idx] + alpha*(allDat.loc[idx,'outcome1']-rl_prob[idx])
    allDat['rl_prob'] = rl_prob   
    allDat['corr_color'] = 1-allDat.loc[1,'high_prob']
    allDat.loc[allDat['high_prob_color']==allDat.loc[1,'color1'],'corr_color'] = allDat.loc[1,'high_prob']

    # produce correct variables for probs, evs, mags
    allDat['rl_prob_left'] = 1-allDat['rl_prob']
    allDat.loc[allDat['position1'] == 'left','rl_prob_left']=allDat['rl_prob']
    allDat['rl_prob_right'] = 1-allDat['rl_prob']
    allDat.loc[allDat['position1'] == 'right','rl_prob_right']=allDat['rl_prob']
    allDat['rl_prob_correct_resp'] = left
    allDat.loc[allDat['rl_prob_left']<allDat['rl_prob_right'],'rl_prob_correct_resp']= right
    allDat['rl_prob_correct'] = (allDat['rl_prob_correct_resp'] == allDat['resp_key']).astype(int)

    allDat['rl_ev_left'] = allDat['rl_prob_left']*allDat['mag_left']
    allDat['rl_ev_right'] = allDat['rl_prob_right']*allDat['mag_right']
    allDat['rl_correct_resp'] = left
    allDat.loc[allDat['rl_ev_left']<allDat['rl_ev_right'],'rl_correct_resp'] = right
    allDat['rl_correct'] = (allDat['rl_correct_resp'] == allDat['resp_key']).astype(int)
 
    allDat['prob_left'] = 1-allDat['high_prob']
    allDat.loc[allDat['high_prob_side'] == left,'prob_left']=allDat['high_prob']
    allDat['prob_right'] = 1-allDat['high_prob']
    allDat.loc[allDat['high_prob_side'] == right,'prob_right']=allDat['high_prob']
    allDat['prob_correct_resp'] = left
    allDat.loc[allDat['prob_left']<allDat['prob_right'],'prob_correct_resp']= right
    allDat['prob_correct'] = (allDat['prob_correct_resp'] == allDat['resp_key']).astype(int)
    allDat['mag_correct_resp'] = left
    allDat.loc[allDat['mag_left']<allDat['mag_right'],'mag_correct_resp'] = right
    allDat['mag_correct'] = (allDat['mag_correct_resp'] == allDat['resp_key']).astype(int)
    allDat['mags'] = list(zip(allDat.mag_left,allDat.mag_right))
    
    # filter
    cleanDat = allDat.loc[(allDat.loc[:,'nb']==0)&(allDat.loc[:,'timeout']==0)].copy()


    cleanDat.loc[:,'mov_avg']= cleanDat.groupby(['sub_id'])['ev_correct'].apply(slidingWindow)
    cleanDat.loc[:,'prob_mov_avg']= cleanDat.groupby(['sub_id'])['prob_correct'].apply(slidingWindow)
    cleanDat.loc[:,'mag_mov_avg']= cleanDat.groupby(['sub_id'])['mag_correct'].apply(slidingWindow)
    cleanDat.loc[:,'rl_mov_avg']= cleanDat.groupby(['sub_id'])['rl_correct'].apply(slidingWindow)
    cleanDat.loc[:,'rl_prob_mov_avg']= cleanDat.groupby(['sub_id'])['rl_prob_correct'].apply(slidingWindow)
    
    # aggregate and compute average and plot average
    # leave out magnitude measure because it is obviously stupid
    dvs = ['mov_avg','rl_mov_avg','prob_mov_avg','rl_prob_mov_avg']
    

    # compute accuracy over subjects
    firstlvl_acc= pd.melt(cleanDat.groupby(['sub_id'])[['ev_correct','rl_correct','prob_correct','rl_prob_correct','mag_correct']].mean().reset_index(),id_vars=['sub_id'],var_name='measure')
    secondlvl_acc= firstlvl_acc.groupby(['measure']).mean().reset_index()
    firstlvl_acc.value = 100*firstlvl_acc.value
    # compute development within a block for each block type and subject
    grouped= pd.melt(cleanDat.groupby(['sub_id','phase_type_order','phase_length','trialInPhase_no'])['mov_avg'].mean().reset_index(),id_vars=['sub_id','phase_type_order','phase_length','trialInPhase_no'],var_name='measure')
    grouped.value = 100*grouped.value

    plotResults(grouped,firstlvl_acc,outpath)


if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(path)