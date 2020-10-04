import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os,sys,glob,json
import numpy as np

def slidingWindow(series,window=7):
    """
    overly complicated because index of panda series have to be taken care of
    """
    new_s =  pd.Series(np.nan, index=series.index,name='mov_avg')
    win_half = window//2
    for tI in range(win_half,series.size-win_half):
        new_s.iloc[tI] = series[tI-win_half:tI+win_half+1].mean()
    return new_s

def plotResults(dat,acc,dv,outpath = 'fig1.pdf'):
    """
    plot ML specific figure: 
    left panel: absolute score
    right panel: development over time
    """
    # various correct response measures
    sns.set(font_scale=2,style='white')
    fig = plt.figure(figsize=(25,15))
    grid = plt.GridSpec(5, 3)
    ax0 = plt.subplot(grid[:2,0])
    ax0=sns.boxplot(x="measure", y="value", data=acc,width=0.5, dodge=1)
    sns.swarmplot(size=15,edgecolor = 'black', x="measure", y="value", data=acc,dodge=1,hue="measure")
    ax0.set(xticklabels=[],xlabel=None,ylim=(0,1),ylabel = 'Performance (%)')    
    for j in np.arange(0.5,1,0.1):
        ax0.axhline(j, ls='--',color='black')
    ax0.legend(loc='lower center', ncol=2,frameon=False)

    # obj/subj. probabilities
    ax1= plt.subplot(grid[2:4:,0])
    sns.lineplot(x='trial_no',y='true_corr_resp' ,palette='green',data=dat)
    sns.lineplot(x='trial_no',y='rl_prob' ,palette='red',data=dat)
    ax1.set(ylim=(0,1))      

    # legend
    ax2= plt.subplot(grid[4,0])
    plt.annotate('correct/mov_avg: obj. EV\nrl_correct/rl_mov_avg: subj. EV\nprob_correct/prob_mov_avg: obj. Probability\nrl_prob_correct/rl_prob_mov_avg: subj. Probability\nmag_correct/mag_mov_avg: obj. Magnitude',xy=(0,0.1),fontsize=22)
    plt.axis('off')

    # performance over time
    for avg_idx,avg in enumerate(dv):
        ax = plt.subplot(grid[avg_idx,1:])
        for i in dat.phase_no.unique():
            plotData = dat.loc[dat.phase_no==i,:].copy()
            colors = ['red','magenta','orange','yellow','green','blue','cyan','purple']
            sns.lineplot(x='trial_no',y='{}'.format(avg) ,palette=colors[int(i-1)],data=plotData)
        if avg_idx!=len(dv)-1: 
            ax.set(xticklabels=[],xlabel=None)
        else:
            ax.set(xlabel='Performance measure')
        ax.axhline(0.5, ls='--',color='black')
    plt.tight_layout()
    plt.subplots_adjust(hspace = 0.2)
    plt.savefig(outpath)

def runAnal(dat_file):
    # some overhead
    assert os.path.isfile(dat_file)
    allDat = pd.read_csv(dat_file)
    outpath= dat_file.replace('csv','png').replace('beh','results')
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    # define the current correct responses
    if allDat.loc[1,'ses_id'] in [1,2,3]:
        left = 51200;right = 53248
    else:
        left = 'left';right = 'right'

    # RL learner
    alpha = 0.10
    rl_prob = np.ones((allDat.shape[0]))*0.5
    for idx,item in enumerate(rl_prob[:-1]):
        rl_prob[idx+1]=rl_prob[idx] + alpha*(allDat.loc[idx,'outcome1']-rl_prob[idx])
    allDat['rl_prob'] = rl_prob   
    allDat['true_corr_resp'] = 1-allDat.loc[1,'high_prob']
    allDat.loc[allDat['high_prob_color']==allDat.loc[1,'color1'],'true_corr_resp'] = allDat.loc[1,'high_prob']

    # produce correct variables for probs, evs, mags
    allDat['rl_prob_left'] = 1-allDat['rl_prob']
    allDat.loc[allDat['position1'] == 'left','rl_prob_left']=allDat['rl_prob']
    allDat['rl_prob_right'] = 1-allDat['rl_prob']
    allDat.loc[allDat['position1'] == 'right','rl_prob_right']=allDat['rl_prob']
    allDat['rl_prob_corr_resp'] = left
    allDat.loc[allDat['rl_prob_left']<allDat['rl_prob_right'],'rl_prob_corr_resp']= right
    allDat['rl_prob_correct'] = (allDat['rl_prob_corr_resp'] == allDat['resp_key']).astype(int)

    allDat['rl_ev_left'] = allDat['rl_prob_left']*allDat['mag_left']
    allDat['rl_ev_right'] = allDat['rl_prob_right']*allDat['mag_right']
    allDat['rl_corr_resp'] = left
    allDat.loc[allDat['rl_ev_left']<allDat['rl_ev_right'],'rl_corr_resp'] = right
    allDat['rl_correct'] = (allDat['rl_corr_resp'] == allDat['resp_key']).astype(int)
     
    # filter
    cleanDat = allDat.loc[allDat.loc[:,'timeout']==0].copy()
    cleanDat.loc[:,'mov_avg']= cleanDat.groupby(['sub_id'])['ev_correct'].apply(slidingWindow)
    cleanDat.loc[:,'prob_mov_avg']= cleanDat.groupby(['sub_id'])['prob_correct'].apply(slidingWindow)
    cleanDat.loc[:,'mag_mov_avg']= cleanDat.groupby(['sub_id'])['mag_correct'].apply(slidingWindow)
    cleanDat.loc[:,'rl_mov_avg']= cleanDat.groupby(['sub_id'])['rl_correct'].apply(slidingWindow)
    cleanDat.loc[:,'rl_prob_mov_avg']= cleanDat.groupby(['sub_id'])['rl_prob_correct'].apply(slidingWindow)

    # aggregate and compute average and plot average
    # ev accuracy
    dvs = ['mov_avg','rl_mov_avg','prob_mov_avg','rl_prob_mov_avg','mag_mov_avg']
    firstlvl_acc= pd.melt(cleanDat.groupby(['ses_id'])['ev_correct','rl_correct','prob_correct','rl_prob_correct','mag_correct'].mean().reset_index(),id_vars=['ses_id'],var_name='measure')
    print(firstlvl_acc)
    plotResults(cleanDat,firstlvl_acc,dvs,outpath)


if __name__ == '__main__':
    try:
        inf = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(inf)