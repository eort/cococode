import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os,sys,glob,json
import numpy as np
from IPython import embed as shell

def slidingWindow(series,window=7):
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
    fig = plt.figure(figsize=(25,15))
    grid = plt.GridSpec(2, 3)
    ax0 = plt.subplot(grid[0,0])
    ax0=sns.boxplot(x="measure", y="value", data=acc,width=0.5, dodge=1)
    sns.swarmplot(size=15,edgecolor = 'black', x="measure", y="value", data=acc,dodge=1)
    ax0.set(ylim=(0,1))
    ax0.set_xticklabels(ax0.get_xticklabels(), rotation=30)    
    for j in np.arange(0.5,1,0.1):
        ax0.axhline(j, ls='--',color='black')

    # sliding window plots
    for avg_idx,avg in enumerate(dat.block_length.unique(),1):
        if avg in [20,40]:
            ax = plt.subplot(grid[avg_idx])
        else:
            ax = plt.subplot(grid[avg_idx:])
        plotData = dat.loc[dat.block_length==avg,:].copy()
        sns.lineplot(x='trialInBlock_no',y='value',data=plotData)
        ax.axhline(0.5, ls='--',color='black')
        ax.set_xlabel('Trial in block')
    plt.tight_layout()
    plt.savefig(outpath)

def runAnal(path):
    # some overhead
    assert os.path.isdir(path)  
    
    allFiles = sorted(glob.glob(os.path.join(path,'sub-*/ses-*/beh/') + 'sub*scr*ml*.csv'))
    pdList = [pd.read_csv(f) for f in allFiles]
    allDat = pd.concat(pdList, axis=0, ignore_index=True,sort=True)
    outpath=os.path.join('results','ml_group_results.png')
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    # fix to have trialInBlock_no
    allDat['trialInBlock_no'] = 0
    for sub in allDat.sub_id.unique():
        for block_no in allDat.block_no.unique():
            trial_count = len(allDat.loc[(allDat.block_no==block_no)&(allDat.sub_id==sub),'trialInBlock_no'])
            allDat.loc[(allDat.block_no==block_no)&(allDat.sub_id==sub),'trialInBlock_no'] = list(range(1,trial_count+1))
    # define the current correct responses
    if allDat.loc[1,'ses_id']=='meg':
        left = 51200;right = 53248
    else:
        left = 'left';right = 'right'

    # RL learner
    allDat.loc[(allDat.low_prob_color==allDat.option1_color) & (allDat.reward_validity=='valid'),'option1_outcome'] = 0
    allDat.loc[(allDat.low_prob_color==allDat.option1_color) & (allDat.reward_validity=='invalid'),'option1_outcome'] = 1
    alpha = 0.10
    rl_prob = np.ones((allDat.shape[0]))*0.5
    for idx,item in enumerate(rl_prob[:-1]):
        rl_prob[idx+1]=rl_prob[idx] + alpha*(allDat.loc[idx,'option1_outcome']-rl_prob[idx])
    allDat['rl_prob'] = rl_prob   
    allDat['corr_color'] = 1-allDat.loc[1,'high_prob']
    allDat.loc[allDat['high_prob_color']==allDat.loc[1,'option1_color'],'corr_color'] = allDat.loc[1,'high_prob']

    # produce correct variables for probs, evs, mags
    allDat['rl_prob_left'] = 1-allDat['rl_prob']
    allDat.loc[allDat['option1_side'] == 'left','rl_prob_left']=allDat['rl_prob']
    allDat['rl_prob_right'] = 1-allDat['rl_prob']
    allDat.loc[allDat['option1_side'] == 'right','rl_prob_right']=allDat['rl_prob']
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
    cleanDat = allDat.loc[allDat.loc[:,'timeout']==0].copy()
    cleanDat.loc[:,'mov_avg']= cleanDat.groupby(['sub_id'])['correct'].apply(slidingWindow)
    cleanDat.loc[:,'prob_mov_avg']= cleanDat.groupby(['sub_id'])['prob_correct'].apply(slidingWindow)
    cleanDat.loc[:,'mag_mov_avg']= cleanDat.groupby(['sub_id'])['mag_correct'].apply(slidingWindow)
    cleanDat.loc[:,'rl_mov_avg']= cleanDat.groupby(['sub_id'])['rl_correct'].apply(slidingWindow)
    cleanDat.loc[:,'rl_prob_mov_avg']= cleanDat.groupby(['sub_id'])['rl_prob_correct'].apply(slidingWindow)
    
    # aggregate and compute average and plot average
    # ev accuracy
    dvs = ['mov_avg','rl_mov_avg','prob_mov_avg','rl_prob_mov_avg']
    # leave out magnitude measure because it is obviously stupid

    # compute accuracy over subjects
    firstlvl_acc= pd.melt(cleanDat.groupby(['sub_id'])[['correct','rl_correct','prob_correct','rl_prob_correct','mag_correct']].mean().reset_index(),id_vars=['sub_id'],var_name='measure')
    secondlvl_acc= firstlvl_acc.groupby(['measure']).mean().reset_index()

    # compute development within a block for each block type and subject
    grouped= pd.melt(cleanDat.groupby(['sub_id','block_length','trialInBlock_no'])['mov_avg'].mean().reset_index(),id_vars=['sub_id','block_length','trialInBlock_no'],var_name='measure')
    #block_data= grouped.groupby(['block_length','trialInBlock_no','measure']).mean().reset_index()
    plotResults(grouped,firstlvl_acc,outpath)


if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(path)