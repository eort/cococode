import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
import os,sys
import glob
#import pymc3 as pm
#import numpy as np

def runAnal(dat_file):
    assert os.path.isfile(dat_file)
    allDat = pd.read_csv(dat_file)
    outpath= dat_file.replace('csv','png')

    #####################
    ###    PREPROC   ####
    #####################
    allDat['direction']=[-1 if c else 1 for c in allDat.cur_dir]   
    allDat['cur_coherence'] = allDat['cur_coherence']*100
    allDat['dirCoh']  = allDat['direction'] * allDat['cur_coherence']
    allDat = allDat.dropna(subset=['resp_key'])
    allDat['resp_time'] *= 1000
    allDat.loc[allDat['cur_coherence'] == 0.0,'correct'] = 0.5 
    allDat['prev_response']= allDat.groupby(['sub_id','block_no'])['resp_key'].shift() # time 
    allDat['prev_dir']= allDat.groupby(['sub_id','block_no'])['cur_dir'].shift() # time 
    try:
        allDat['response'] = allDat.resp_key.replace({'right':1,'left':0})
    except:
        allDat['response'] = allDat.resp_key.replace({53248:1,51200:0})

    allDat['prev_dir'] = allDat.prev_dir.replace({0.0:'right',180.0:'left'})
    allDat = allDat.dropna(subset=['prev_dir'])
    
    #####################
    ###   AGGREGATE  ####
    #####################
    # ACC and RT over unsigned coherence
    firstlvl= allDat.groupby(['cur_coherence'])[['correct','resp_time']].mean().reset_index() 
    # ACC and RT over signed coherence
    firstlvl_pf= allDat.groupby(['dirCoh'])['response'].mean().reset_index() 
    # compute mean response time
    firstlvl_rt= allDat.groupby(['dirCoh'])['resp_time'].mean().reset_index() 
    # combine the two data frames
    firstlvl_pf['resp_time'] = firstlvl_rt['resp_time']

    # serial dependency
    serial = allDat.groupby(['prev_response','dirCoh'])['response'].mean().reset_index() 
    serial_dir = allDat.groupby(['prev_dir','dirCoh'])['response'].mean().reset_index() 
 
    #####################
    ###   PLOTTING   ####
    #####################
    max_coh =  allDat.cur_coherence.max()+10
    min_coh =  -max_coh
    firstlvl_pf.response = firstlvl_pf.response*100
    firstlvl.correct = firstlvl.correct*100
    
    fig,axs = plt.subplots(2,2,constrained_layout=1)#,figsize = (12.25,7.5))
    sns.scatterplot(x="dirCoh", y="response", data=firstlvl_pf,ax = axs[0,0])
    sns.lineplot(x="dirCoh", y="response", data=firstlvl_pf,ax = axs[0,0])
    axs[0,0].axhline(50,0, ls='--')
    axs[0,0].set(xlabel='Dot Coherence (%)', ylabel='Response right (%)', xlim=(min_coh,max_coh),ylim = (0,100) )

    axs[0,1].set(xlim=(min_coh,max_coh))
    sns.scatterplot(x="dirCoh", y="resp_time", data=firstlvl_pf,ax = axs[0,1])
    sns.lineplot(x="dirCoh", y="resp_time", data=firstlvl_pf,ax = axs[0,1])
    axs[0,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (ms)')

    sns.scatterplot(x="cur_coherence", y="correct", data=firstlvl,ax = axs[1,0])
    sns.lineplot(x="cur_coherence", y="correct", data=firstlvl,ax = axs[1,0])
    axs[1,0].set(xlabel='Dot Coherence (%)', ylabel='Percentage correct (%)', ylim = (0,100) )
    axs[1,0].axhline(50,0, ls='--')

    axs[1,1].set(xlim=(0,max_coh))
    sns.scatterplot(x="cur_coherence", y="resp_time", data=firstlvl,ax = axs[1,1])
    sns.lineplot(x="cur_coherence", y="resp_time", data=firstlvl,ax = axs[1,1])
    axs[1,1].set(xlabel='Dot Coherence (%)', ylabel='Response Time (ms)')

    """
    ############################
    ### LOGISTIC REGRESSION  ###
    ############################
    def logit(x,trace):
        return 1 / (1 + np.exp(-(trace['Intercept'] + trace['dirCoh']*x)))
    
    with pm.Model() as logistic_model:
        Intercept = pm.Normal('Intercept', 0, sd=10)
        dirCoh = pm.Normal('dirCoh', 0, sd=10)
        y = pm.Bernoulli('y', 1/(1+np.exp(-(Intercept+dirCoh*allDat['dirCoh']))),observed=allDat['response'])
        #a= pm.model_to_graphviz(logistic_model)
        trace = pm.sample(2000,tune=1000,init='adapt_diag')

    # predictive checks
    a = trace['Intercept'].mean()
    b = trace['dirCoh'].mean()
    b_25 = np.percentile(trace['dirCoh'],2.5)
    b_97 = np.percentile(trace['dirCoh'],97.5)

    print(pm.summary(trace,round_to=2))
 
    axs[1,2].set(xlim=(min_coh,max_coh))
    pm.plot_posterior_predictive_glm(trace, samples=100,eval=firstlvl_pf.dirCoh,
                                     lm=logit,label='Posterior predictive y', c='C2')
    plt.plot(firstlvl_pf.dirCoh,0.01*firstlvl_pf.response, '.', label='observed y', c='C0')
    plt.plot(firstlvl_pf.dirCoh, 1 / (1 + np.exp(-(a + b*firstlvl_pf.dirCoh))), label='modeled y', lw=3., c='C3')
    plt.legend(loc=0)
    axs[1,2].set(xlabel='Dot Coherence (%)', ylabel='Response right (%)',title='Bayesian logistic reg. - Slope: {:.02f}, [{:.02f},{:.02f}]'.format(b,b_25,b_97))
    fig.savefig(outpath)
    plt.close() 

    axs[0,2].set(xlim=(min_coh,max_coh))
    sns.scatterplot(x="dirCoh", y="response",hue="prev_dir",legend=False, data=serial_dir,ax = axs[0,2], palette="deep")
    sns.lineplot(x="dirCoh", y="response",hue="prev_dir", data=serial_dir,ax = axs[0,2], palette="deep")
    axs[0,2].set(xlabel='Dot Coherence (%)', ylabel='Response Time (ms)')
    """
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