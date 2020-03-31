import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
import os,sys,glob

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
