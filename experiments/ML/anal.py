import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os,sys,glob,json

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
        sns.lineplot(x='trial_no',y='mov_avg' ,palette=colors[i-1],data=plotData)

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
    # filter
    cleanDat = allDat.loc[allDat['timeout']==0]
    cleanDat['mov_avg']= cleanDat.groupby(['sub_id'])['correct'].apply(localAverage)

    # aggregate data for sub stats
    firstlvl_acc= cleanDat.groupby(['sub_id','sess_id'])['correct','resp_time'].mean().reset_index()
    secondlvl_acc= cleanDat.groupby(['sub_id'])['correct','resp_time'].mean().reset_index()

    # plot
    secondlvl_acc_long = pd.melt(secondlvl_acc,id_vars=['sub_id'],var_name='measure') 
    correct = secondlvl_acc_long.loc[secondlvl_acc_long['measure']=='correct']
    plotResults(correct,cleanDat,outpath)

if __name__ == '__main__':
    try:
        inf = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(inf)
