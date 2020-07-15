import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os,sys,glob,json
from IPython import embed as shell

def localAverage(series,window=5):
    new_s =  pd.Series(pd.np.nan, index=series.index,name='mov_avg')
    win_half = window//2
    for tI in range(win_half,series.size-win_half):
        new_s.iloc[tI] = series[tI-win_half:tI+win_half+1].mean()
    return new_s

def plotResults(acc,mov_avg,outpath = 'fig1.pdf'):
    fig = plt.figure(figsize=(20,5))
    grid = plt.GridSpec(1, 3)
    ax0 = plt.subplot(grid[0,0])
    sns.set(font_scale=1,style='white')
    ax0=sns.boxplot(x="measure", y="value", data=acc,width=0.5, dodge=1)
    sns.swarmplot(size=6,edgecolor = 'black', x="measure", y="value", data=acc,dodge=1)
    ax0.set(ylim=(0,1))
    ax0.axhline(0.5, ls='--',color='black')
    ax0.axhline(0.6, ls='--',color='black')
    ax0.axhline(0.7, ls='--',color='black')
    ax0.axhline(0.8, ls='--',color='black')
    ax0.axhline(0.9, ls='--',color='black')

    ax1 = plt.subplot(grid[0,1:])
    for i in mov_avg.block_no.unique():
        plotData = mov_avg[mov_avg.block_no==i]
        colors = ['red','magenta','orange','yellow','green','blue','cyan','purple']
        value = str(mov_avg.loc[1,'avg'])
        sns.lineplot(x='trial_no',y='{}'.format(value) ,palette=colors[i-1],data=plotData)

    plt.tight_layout()
    plt.savefig(outpath)

def runAnal(datFolder):
    
    if not os.path.isfile(datFolder):
        inFiles = sorted(glob.glob(datFolder + '/*.csv'))
        pdList = [pd.read_csv(f) for f in inFiles]
        allDat = pd.concat(pdList, axis=0, ignore_index=True)
        outpath=os.path.join(datFolder,'group_results.pdf')
    else:
        allDat = pd.read_csv(datFolder)
        outpath= datFolder.replace('csv','png')

    allDat.correct = allDat.correct.astype(int)
    if 'left' in allDat.resp_key:
        left = 'left'
        right = 'right'
    else:
        left = 51200
        right = 53248
    allDat['prob_left'] = 0.2
    allDat['prob_left'].loc[allDat['high_prob_side'] == left ]= 0.8
    allDat['prob_right'] = 0.2
    allDat['prob_right'].loc[allDat['high_prob_side'] == right ]= 0.8
    allDat['ev_left'] = allDat.mag_left*allDat.prob_left
    allDat['ev_right'] = allDat.mag_right*allDat.prob_right
    allDat['ev_correct_resp'] = left
    allDat['ev_correct_resp'].loc[allDat['ev_left']<allDat['ev_right']] = right
    allDat['mag_correct_resp'] = left
    allDat['mag_correct_resp'].loc[allDat['mag_left']<allDat['mag_right']] = right
    allDat['mag_correct'] = (allDat['mag_correct_resp'] == allDat['resp_key']).astype(int)
    allDat['ev_correct'] = (allDat['ev_correct_resp'] == allDat['resp_key']).astype(int)
    allDat['mags'] = list(zip(allDat.mag_left,allDat.mag_right))

    # filter
    cleanDat = allDat.loc[allDat['timeout']==0]
    cleanDat['mov_avg']= cleanDat.groupby(['sub_id'])['correct'].apply(localAverage)
    cleanDat['avg']= 'mov_avg'
    cleanDat['ev_mov_avg']= cleanDat.groupby(['sub_id'])['ev_correct'].apply(localAverage)
    cleanDat['mag_mov_avg']= cleanDat.groupby(['sub_id'])['mag_correct'].apply(localAverage)

    #pd.crosstab(allDat.mags, allDat.high_prob_side)
    # aggregate data for sub stats
    #shell()
    firstlvl_acc= cleanDat.groupby(['sub_id','sess_id'])['correct','resp_time'].mean().reset_index()
    secondlvl_acc= cleanDat.groupby(['sub_id'])['correct','resp_time'].mean().reset_index()
    # plot
    secondlvl_acc_long = pd.melt(secondlvl_acc,id_vars=['sub_id'],var_name='measure') 
    correct = secondlvl_acc_long.loc[secondlvl_acc_long['measure']=='correct']
    plotResults(correct,cleanDat,outpath)

    cleanDat['avg']= 'ev_mov_avg'
    outpath= outpath.replace('2020','2021')
    # aggregate data for sub stats
    firstlvl_acc= cleanDat.groupby(['sub_id','sess_id'])['ev_correct','resp_time'].mean().reset_index()
    secondlvl_acc= cleanDat.groupby(['sub_id'])['ev_correct','resp_time'].mean().reset_index()
    # plot
    secondlvl_acc_long = pd.melt(secondlvl_acc,id_vars=['sub_id'],var_name='measure') 
    ev_correct = secondlvl_acc_long.loc[secondlvl_acc_long['measure']=='ev_correct']
    plotResults(ev_correct,cleanDat,outpath)

    outpath= outpath.replace('2021','2022')
    cleanDat['avg']= 'mag_mov_avg'
    # aggregate data for sub stats
    firstlvl_acc= cleanDat.groupby(['sub_id','sess_id'])['mag_correct','resp_time'].mean().reset_index()
    secondlvl_acc= cleanDat.groupby(['sub_id'])['mag_correct','resp_time'].mean().reset_index()
    # plot
    secondlvl_acc_long = pd.melt(secondlvl_acc,id_vars=['sub_id'],var_name='measure') 
    mag_correct = secondlvl_acc_long.loc[secondlvl_acc_long['measure']=='mag_correct']
    plotResults(mag_correct,cleanDat,outpath)

if __name__ == '__main__':
    try:
        inf = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(inf)