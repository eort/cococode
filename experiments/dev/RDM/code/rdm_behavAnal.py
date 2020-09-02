import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os,sys,glob,json
import numpy as np
import pymc3 as pm
from IPython import embed as shell

def runAnal(path):
    # some overhead
    assert os.path.isdir(path)  
    
    allFiles = sorted(glob.glob(os.path.join(path,'sub-*/ses-*/beh/') + 'sub*scr*rdm*.csv'))
    pdList = [pd.read_csv(f) for f in allFiles]
    allDat = pd.concat(pdList, axis=0, ignore_index=True,sort=True)
    outpath=os.path.join('results','rdm_group_results.png')
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    #####################
    ###    PREPROC   ####
    #####################
    allDat['direction']=[-1 if c else 1 for c in allDat.cur_dir]   
    allDat['cur_coherence'] = allDat['cur_coherence']*100
    allDat['dirCoh']  = allDat['direction'] * allDat['cur_coherence']
    allDat = allDat.dropna(subset=['resp_key'])
    allDat['resp_time'] *= 1000
    allDat.loc[allDat['cur_coherence'] == 0.0,'correct'] = 0.5 
    allDat['response'] = allDat.resp_key.replace({'right':1,'left':0})
    
    #####################
    ###   AGGREGATE  ####
    #####################
    # ACC and RT over unsigned coherence
    firstlvl= allDat.groupby(['sub_id','ses_id','cur_coherence'])[['correct','resp_time']].mean().reset_index() # time between successive switches
    secondlvl= firstlvl.groupby(['sub_id','cur_coherence'])[['correct','resp_time']].mean().reset_index() # time between successive switches
    thirdlvl= secondlvl.groupby(['cur_coherence'])[['correct','resp_time']].mean().reset_index() 

    # ACC and RT over signed coherence
    firstlvl_pf=allDat.groupby(['sub_id','ses_id','dirCoh'])['response'].mean().reset_index()
    # compute mean response time
    firstlvl_rt=allDat.groupby(['sub_id','ses_id','dirCoh'])['resp_time'].mean().reset_index() 
    # combine the two data frames
    firstlvl_pf['resp_time'] = firstlvl_rt['resp_time']
    secondlvl_pf= firstlvl_pf.groupby(['sub_id','dirCoh'])[['response','resp_time']].mean().reset_index() 
    thirdlvl_pf= secondlvl_pf.groupby(['dirCoh'])[['response','resp_time']].mean().reset_index()

    #####################
    ###   PLOTTING   ####
    #####################
    max_coh =  allDat.cur_coherence.max()+10
    min_coh =  -max_coh
    thirdlvl_pf.response = thirdlvl_pf.response*100
    thirdlvl.correct =  thirdlvl.correct*100

    fig,axs = plt.subplots(2,2,constrained_layout=1)
    sns.scatterplot(x="dirCoh", y="response", data=thirdlvl_pf,ax = axs[0,0])
    sns.lineplot(x="dirCoh", y="response", data=thirdlvl_pf,ax = axs[0,0])
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

    """
    N = len(allDat.sub_id.unique())
    sub_index = allDat.sub_id-1
    # hierarchical model
    with pm.Model() as hm:

        I_mu = pm.Normal('I_mu', 0, sd=10)
        I_sd = pm.HalfNormal('I_sd', 5)
        s_mu = pm.Normal('s_mu', 0, sd=10)
        s_sd = pm.HalfNormal('s_sd', 5)

        Intercept = pm.Normal('Intercept', I_mu, sd=I_sd, shape=N)
        signal = pm.Normal('signal', s_mu, sd=s_sd, shape=N)
        y_est = 1/(1+np.exp(-(Intercept[sub_index]+signal[sub_index]*allDat['dirCoh'])))

        y = pm.Bernoulli('y',y_est ,observed=allDat['response'])

        a = pm.model_to_graphviz(hm)
        hm_trace = pm.sample(5000,tune=4000,init='adapt_diag')

    print(pm.summary(hm_trace))

    def logit2(x,trace):
        return 1 / (1 + np.exp(-(trace['I_mu'] + trace['s_mu']*x)))

    a = hm_trace['I_mu'].mean()
    b = hm_trace['s_mu'].mean()
    axs[1,2].set(xlim=(min_coh,max_coh))
    pm.plot_posterior_predictive_glm(hm_trace, samples=100,eval=thirdlvl_pf.dirCoh,
                                     lm=logit2,label='Posterior predictive y', c='C2')
    plt.plot(thirdlvl_pf.dirCoh,thirdlvl_pf.response, '.', label='observed y', c='C0')
    plt.plot(thirdlvl_pf.dirCoh, 1 / (1 + np.exp(-(a + b*thirdlvl_pf.dirCoh))), label='modeled y', lw=3., c='C3')
    plt.legend(loc=0)
    axs[1,2].set(xlabel='Dot Coherence (%)', ylabel='Response right (%)',title='Bayesian logistic reg. - Slope: {:.02f}, [{:.02f},{:.02f}]'.format(b,b_25,b_97))
    fig.savefig(outpath)
    plt.close() 

    """

    fig.savefig(outpath)
    plt.close() 



if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except IndexError as e:
        print("Please provide an input file.")
        sys.exit(-1)
    else:
        runAnal(path)