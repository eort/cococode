from __future__ import division
import numpy as np
import pandas as pd
import mne
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype'] = 'none'
from IPython import embed as shell
import scipy.stats as ss
import scipy.signal as sig

def hammingSincLP(sig,cutoffFreq, trans_band_fac=0.25):
    """implements a finite sinc hamming window lowpass filter"""

    fc = cutoffFreq/512  # Cutoff frequency as a fraction of the sampling rate (in (0, 0.5)).
    b = trans_band_fac*fc  # Transition band, as a fraction of cutofffreq
    N = int(np.ceil((3.1 / b)))
    if not N % 2: N += 1  # Make sure that N is odd.
    n = np.arange(N)
     
    # Compute sinc filter.
    h = np.sinc(2 * fc * (n - (N - 1) / 2))
    # Compute Blackman window.
    w = np.hamming(N)
    # Multiply sinc filter with window.
    h = h * w
    # Normalize to get unity gain.
    h = h / np.sum(h)

    new_sig = np.convolve(sig,h)
    # cut edges
    offset = new_sig.shape[0]-sig.shape[0]
    return new_sig[int(offset/2):-int(offset/2)]

def leaveOneOut(tc):
    output = np.zeros((tc.shape[0]+1,tc.shape[1],tc.shape[2]))
    for sub in range(tc.shape[0]):
        # exclude subject
        subs = np.concatenate([np.arange(0,sub),np.arange(sub+1,tc.shape[0])])
        # average over the rest
        output[sub,:] = (tc[subs,:,:]).mean(axis = 0)
    # add the GA in the last column
    output[sub+1,:] = tc.mean(axis = 0)
    return output


def findOnset(tc,tp,peak_frac = 0.5,baseline=0.5,polarity=-1,tmin=None,tmax=None,margins=5,
                search='forward'):
    """
    Jackknife-based estimation of onsets
    tc       :  2D numpy array (subs,time)
    peak_frac:  for fractional onset latency measure, what is cutoff %
    baseline :  What is the baseline
    polarity :  Takes care that negative peaks dont mess up code
    tmin,tmax:  time indices between which peak is searched for

    returns jackknifed estimates of area or onset
    """
    tc = tc*polarity
    onsets = np.zeros(tc.shape[:2])
    #
    # determine the peak amplitude
    if tmin != None or tmax != None:
        peakIdx =tmin + tc[:,:,tmin:tmax].argmax(axis = 2)
    else:
        peakIdx = tc[:,:,:].max(axis = 2)  

    peakIdx_low = peakIdx-margins
    peakIdx_high = peakIdx+margins
    for sub in range(tc.shape[0]):
        # where is peak reached
        
        new_tc = np.zeros((tc.shape[1],tc.shape[2]))
        peak_avg= np.zeros(tc.shape[1])
        for condI in range(tc.shape[1]):
            sub_tc = tc[sub,condI,:]
            peak_avg[condI] = tc[sub,condI,peakIdx_low[sub,condI]:peakIdx_high[sub,condI]+1].mean()
            for i in range(sub_tc[tmin:tmax].shape[0]):
                new_tc[condI,tmin+i] = sub_tc[tmin+i-margins:tmin+i+margins+1].mean()
        # critical value that defines the onset (scaled to baseline)
        
        onsetCutoff = baseline+peak_frac*(peak_avg-baseline)      
        if search == 'backward':    
            onsets[sub,:] = np.array(
               [peakIdx[sub,condI]-np.where(new_tc[condI,peakIdx[sub,condI]:tmin:-1] <= 
                    onsetCutoff[condI])[0][0]\
                    for condI in range(new_tc.shape[0])])
        else:
            onsets[sub,:] = np.array(
                [tmin+np.where(new_tc[condI,tmin:tmax] >= onsetCutoff[condI])[0][0]
                    for condI in range(new_tc.shape[0])])
    # make it in ms
    return tp[onsets.astype(int)]

def findOnsetArea(tc,tp,peak_frac = 0.3,baseline=0.5,polarity=-1,tmin=None,tmax=None):
    """
    Jackknife-based estimation of onsets
    tc       :  2D numpy array (subs,time)
    peak_frac:  for fractional onset latency measure, what is cutoff %
    baseline :  What is the baseline
    polarity :  Takes care that negative peaks dont mess up code
    tmin,tmax:  time indices between which peak is searched for

    returns jackknifed estimates of area or onset
    """
    #shell()
    tc = tc*polarity
    onsets = np.zeros(tc.shape[:2])
    area = np.zeros(tc.shape[:2])
    #
    # sign the timeseries
    tc2 = tc-baseline
    tc2[tc2<0] = 0
    #shell()
    # find peak
    if tmin != None or tmax != None:
        peakIdx =tmin + tc2[-1,:,tmin:tmax].argmax(axis = -1)
    else:
        peakIdx = tc2[-1,:,:].max(axis = 2) 

    #compute the total area
    if tmin != None:
        for nCond in range(tc2.shape[1]):
            area[:,nCond] = tc2[:,nCond,tmin:peakIdx[nCond]].sum(axis = -1)
    else:
        area = tc2[:,:,:].sum(axis = 2)  


    area_cutoff = peak_frac* area
    #shell()
    cum_area = np.zeros(tc.shape[:2])
    for sub in range(tc.shape[0]):
        # where is peak reached
        for nCond in range(tc.shape[1]):
            for t in range(tmin,tmax):
                cum_area[sub,nCond] += tc2[sub,nCond,t]
                if cum_area[sub,nCond] > area_cutoff[sub,nCond]:
                    onsets[sub,nCond]= t
                    break
 
    # make it in ms
    return tp[onsets.astype(int)]

def jackknife(onsets,comparisons):
    #shell()
    
    GA = onsets[-1,:]
    N = onsets.shape[0]-1
    M_loo = onsets[:N,:].mean(axis=0)

    t_stats = dict()
    for comp,idx in comparisons.items():
        cond_diff = M_loo[idx[1]]- M_loo[idx[0]]
        ga_diff = GA[idx[1]]- GA[idx[0]]
        onset_diff = onsets[:N,idx[1]]-onsets[:N,idx[0]]
        sd = np.sqrt(((N-1)/N)*((onset_diff[:N]-cond_diff)**2).sum())
        t_val = ga_diff/sd
        p_val = 2*(ss.t.cdf(-np.absolute(t_val),N-1))
        t_stats[comp] = dict(M = ga_diff,T = t_val,p = p_val,sd=sd)
    return t_stats

def getSwitch(series):
    """
    series: a panda series
    returns binary series where two consectuive values were the same or different
    """
 
    switch =  pd.Series(None, index=series.index,name='switch')
    if switch.shape[0] == 1:
       return switch
    switch.iloc[1:]=(series!=series.shift(1))*1
    # exclude NaNs
    miss = series[pd.isnull(series)].index
    if len(miss)>0:
        miss2 = miss + 1
        miss2 = miss2[miss2<max(series.index)]
        switch.loc[miss] = None
        switch.loc[miss2] = None
    return switch

def plotTimecourse(data,timepoints,cond_labels,cfg):
    # set plot overhead  
    cm = plt.get_cmap('Paired')
    if len(cfg['colorIdx'])>0:
         colors = [cm.colors[i] for i in cfg['colorIdx']]
    else:
        colors = [cm.colors[i] for i in range(len(cond_labels))]


    if not cfg['ax']:     
        fig, ax = plt.subplots(1,figsize=cfg['figsize'],dpi=cfg['dpi'])
    else:
        ax = cfg['ax']
    ax.axhline(cfg['x_baseline'],color='black',linestyle='dashed',linewidth = 1.2)
    ax.axvline(0,color='black',linestyle='dashed',linewidth = 1.2)
    for axis in ['bottom','left','right']:
        ax.spines[axis].set_linewidth(1.7)
    ax.set_xlabel(cfg['xlabel'],fontsize = 10)
    ax.set_ylabel(cfg['ylabel'],fontsize = 10)
    ax.set_ylim(cfg['ylimits'])
    ax.set_xlim(cfg['xlimits']) 
    ax.set_yticks(np.arange(cfg['ylimits'][0],cfg['ylimits'][1],cfg['ytick']))    
    ax.tick_params(axis='both', which='major', width = 1, length=4,labelsize=8)

    if len(cfg['plotDiff'])>0:
        no_diffs = cfg['plotDiff'].shape[1]
        for i in range(no_diffs):
            colors.append((0,0,0))
        data = np.concatenate((data,cfg['plotDiff']),axis=1)

    # loop over every condition, run 1sample permutation test (cluster correct)
    #shell()
    for condI in range(len(cond_labels)):
        print("Cluster correct for cond_label: {}".format(cond_labels[condI]))
        if cfg['plotIndiv']==False:
            timeseries = data[:,condI,:]
        else:
            timeseries = data[condI,:]

        cfg['times'] = timepoints
        cfg['condition'] = cond_labels[condI]
        cfg['color'] = colors[condI]
        cfg['plotIdx'] = condI
        if '-' in cond_labels[condI]:
            #shell()
            ax2 = ax.twinx()
            ax2.set_ylabel('AUC Difference',fontsize = 10)
            #ax2.set_ylim((-0.04,0.10))
            #ax2.set_yticks(np.arange(-0.04,0.10,0.02))
            ax2.set_ylim((-0.04,0.08))
            ax2.set_yticks(np.arange(-0.04,0.12,0.02))
            ax2.tick_params(axis='both', which='major',width=1, length=4, labelsize=8)
            clusterCorrect(timeseries,0,cfg,ax = ax2)
        else:
            clusterCorrect(timeseries,cfg['x_baseline'],cfg,ax = ax)
       
        if len(cfg['plot_onsets']):
            ax.axvline(cfg['plot_onsets'][condI],color=colors[condI],
                linewidth = 2.0,linestyle=':')

    if cfg['legend']:
        ax.legend(loc='upper left')
    if not cfg['ax']:  
        plt.savefig(cfg['outfilepath'], dpi=fig.dpi)
        plt.close()


def clusterCorrect(data,chance,cfg,ax):

    if cfg['plotIndiv']==False:
        GA = data.mean(axis=0)
        # compute standard error
        sem = data.std(axis=0)/(data.shape[0]**0.5)
    else:
        GA = data
    # lowpass filtering for illustration purposes
    if cfg['smooth']: 
        GA = hammingSincLP(GA,cfg['smooth'])
        #GA = sig.cspline1d(GA,cfg['smooth']/2)
        if cfg['plotIndiv']==False:
            sem = hammingSincLP(sem,cfg['smooth']) 
            #sem = sig.cspline1d(sem,cfg['smooth']/2)    

    if cfg['plotIndiv']==False:
        t_clust, clust_times, p_values, H0 = \
            mne.stats.permutation_cluster_1samp_test(data-chance,
                n_permutations=cfg['iterations'])

    if cfg['plotShades']:
        ax.fill_between(cfg['times'],GA-sem,GA+sem,alpha = 0.196,color=cfg['color'],linewidth=0) 

    if cfg['plotGA']:
        ax.plot(cfg['times'],GA,label = cfg['condition'],color=cfg['color'],linewidth = 0.85)
    if cfg['plotSigBars']:
        if cfg['ytick'] < 0:
            disp = np.linspace(ax.get_ybound()[1],chance,15)
        else:
            disp = np.linspace(ax.get_ybound()[0],chance,15)    
        # color significant lines thicker and sig line underneith
        for it, (times, p_val) in enumerate(zip(clust_times, p_values)):
            if p_val < cfg['sigLevel']:
                s = np.arange(cfg['times'].shape[0])[times]
                ax.plot([cfg['times'][s[0]], cfg['times'][s[-1]]],
                    [disp[cfg['plotIdx']+1],disp[cfg['plotIdx']+1]],linewidth = 1.7,color =cfg['color'])
                ax.plot(cfg['times'][s[0]:s[-1]],GA[s[0]:s[-1]], linewidth = 1.7, 
                    color =cfg['color'])
                print("Cluster p-value %1.5f between timepoints %1.5f and %1.5f, in color"
                        %(p_val, cfg['times'][s[0]], cfg['times'][s[-1]]))
