import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
import os,sys,glob
from IPython import embed as shell
from scipy.stats import norm
import numpy as np

def localAverage(series,window=21):
    new_s =  pd.Series(pd.np.nan, index=series.index,name='mov_avg')
    win_half = window//2
    for tI in range(win_half,series.size-win_half):
        new_s.iloc[tI] = series[tI-win_half:tI+win_half+1].mean()
    return new_s

def localDPrime(df,window=21):
    """
    Series can have multiple columns, but the first is always the responses
    """
    correct = df.correct
    condition = df.condition
    new_s =  pd.Series(pd.np.nan, index=correct.index,name='dprime')
    win_half = window//2
    for tI in range(win_half,correct.size-win_half):
        subset_cor = correct[tI-win_half:tI+win_half+1]
        subset_con = condition[tI-win_half:tI+win_half+1]
        half_hit = 0.5 / sum(subset_con=='go')
        half_fa = 0.5 / sum(subset_con=='nogo')
        hit = sum(subset_cor[subset_con=='go'])/sum(subset_con=='go')
        fa = (sum(subset_con=='nogo')-sum(subset_cor[subset_con=='nogo']))/sum(subset_con=='nogo')
        if hit == 1: hit = 1-half_hit
        elif hit == 0: hit = half_hit
        if fa == 1: fa = 1-half_fa
        elif fa == 0: fa = half_fa            
        new_s.iloc[tI] = norm.ppf(hit) - norm.ppf(fa)
    return pd.DataFrame(new_s)

def doSDT(df):

    out = pd.DataFrame(columns = ['hits','fa','miss','cr','md','mbeta'],index=df.index)
    n_trials = df['correct'].size
    out['hits'] = sum(df.correct[df['condition']=='go'])/(n_trials/2)
    out['fa'] = ((n_trials/2)-sum(df.correct[df['condition']=='nogo']))/(n_trials/2)
    out['miss'] = ((n_trials/2)-sum(df.correct[df['condition']=='go']))/(n_trials/2)
    out['cr'] = sum(df.correct[df['condition']=='nogo'])/(n_trials/2)
    out['md'] = norm.ppf(out['hits'])-norm.ppf(out['fa'])
    out['mbeta']= np.exp((norm.ppf(out['fa'])**2 - norm.ppf(out['hits'])**2) / 2)
    return out

def plotResults(acc,outpath = 'fig1.pdf'):
    fig = plt.figure(figsize=(5,10))
    sns.set(font_scale=1,style='white')
    ax0=sns.boxplot(x="measure", y="value", data=acc,width=0.5, dodge=1)
    sns.swarmplot(size=6,edgecolor = 'black', x="measure", y="value", data=acc,dodge=1)
    ax0.set(ylim=(0,1))
    ax0.axhline(0.5, ls='--',color='black')
    ax0.axhline(0.6, ls='--',color='black')
    ax0.axhline(0.7, ls='--',color='black')
    ax0.axhline(0.8, ls='--',color='black')
    ax0.axhline(0.9, ls='--',color='black')
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

    # aggregate data for sub stats
    firstlvl_acc= allDat.groupby(['sub_id','sess_id'])['correct','resp_time'].mean().reset_index()
    secondlvl_acc= allDat.groupby(['sub_id'])['correct','resp_time'].mean().reset_index()

    # plot
    secondlvl_acc_long = pd.melt(secondlvl_acc,id_vars=['sub_id'],var_name='measure') 
    correct = secondlvl_acc_long.loc[secondlvl_acc_long['measure']=='correct']

    plotResults(correct,outpath)

if __name__ == '__main__':
    try:
        inf = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(inf)
