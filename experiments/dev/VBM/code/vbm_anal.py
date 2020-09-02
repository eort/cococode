import pandas as pd                 # handy data table tools
import seaborn as sns               # plotting
import matplotlib.pyplot as plt     # plotting
import os,sys,json,glob             # file management and system libraries

def runAnal(path):
    
    if not os.path.isfile(path):
        inFiles = sorted(glob.glob(os.path.join(path,'sub-*/ses-scr/beh/') + 'sub*scr*vbm*.csv'))
        pdList = [pd.read_csv(f) for f in inFiles]
        allDat = pd.concat(pdList, axis=0, ignore_index=True)
        outpath=os.path.join(path,'results','vbm_group_results.png')
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
    else:
        allDat = pd.read_csv(path)
        outpath= path.replace('csv','png').replace('beh','results')

    #####################
    ###   AGGREGATE  ####
    #####################

    firstlvl_acc= allDat.groupby(['sub_id','ses_id'])[['correct','resp_time']].mean().reset_index()
    secondlvl_acc= allDat.groupby(['sub_id'])[['correct','resp_time']].mean().reset_index()
    secondlvl_acc_long = pd.melt(secondlvl_acc,id_vars=['sub_id'],var_name='measure') 
    correct = secondlvl_acc_long.loc[secondlvl_acc_long['measure']=='correct']
    
    #####################
    ###   PLOTTING   ####
    #####################
    fig = plt.figure(figsize=(5,10),dpi=600)
    ax0=sns.boxplot(x="measure", y="value", data=correct, width=0.5, dodge=1)
    sns.set(font_scale=1,style='white')
    for j in [0.5,0.6,0.7,0.8,0.9]:
        ax0.axhline(j, ls='--',color='darkgray')
    sns.swarmplot(size=6,edgecolor = 'black', x="measure", y="value",color='black', data=correct,dodge=1)
    ax0.set(ylim=(0,1),xlabel=None,xticklabels=[], ylabel='Percentage correct (%)',)
    plt.tight_layout()
    plt.savefig(outpath)

if __name__ == '__main__':
    try:
        inf = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(inf)
