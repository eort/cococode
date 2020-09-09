"""
checks whether the timing of the experiments is within reasonable limits. 
"""
import sys,json,os
import pandas as pd
import numpy as np

def run(log,settings):
    # load files
    out = log.replace('.log','.csv').replace('log','timing')
    os.makedirs(os.path.dirname(out), exist_ok=True)

    df = pd.read_csv(log,delimiter='\t',header=None,names = ['timestamp','pp_type','type','idx','message'])
    with open(settings) as jsonfile:    
        param = json.load(jsonfile)

    # read out frame info
    stim_frame=df.loc[df.type.str.contains('stim_frame'),['timestamp','idx','message']].set_index(['idx','message']).rename(columns={'timestamp':'stim_frame'})

    percentiles = [0.01,0.05,0.1,0.3,0.5,0.7,0.9,0.95,0.99]
    
    # summarize frame info during stimulus time
    stim_frame['frame_duration']= stim_frame.groupby('idx').diff(1)
    frame_summary= stim_frame['frame_duration'].describe(percentiles=percentiles)

    # read out log file and measure when things happened
    for cI,c in enumerate(['start_stim','start_fix','start_feed','start_noise','end_trial','resp_time']):
        if cI== 0:
            timing=df.loc[df.type.str.contains(c),['timestamp','idx']].set_index('idx').rename(columns={'timestamp':c})
        else:
            timing=timing.join(df.loc[df.type.str.contains(c),['timestamp','idx']].set_index('idx').rename(columns={'timestamp':c}))

    # compute actual times
    timing['fix_dur'] = timing['start_noise']- timing['start_fix']
    timing['noise_dur'] = timing['start_stim']- timing['start_noise']
    timing['stim_dur'] = timing['resp_time']- timing['start_stim']
    timing['feed_dur'] = timing['end_trial']- timing['start_feed']

    # load planned times
    for m in ['start_noise','resp_time','start_fix','start_feed']:
        timing= timing.join(df.loc[df.type.str.contains(m),['message','idx']].set_index('idx').rename(columns={'message':'planned_{}'.format(m)}))

    # compare planned times to actual measured times
    timing['diff_feed']= timing['planned_start_feed']-timing['feed_dur']
    timing['diff_noise']= timing['planned_start_noise']-timing['noise_dur']
    timing['diff_fix']= timing['planned_start_fix']-timing['fix_dur']
    timing['diff_stim']= timing['planned_resp_time']-(timing['stim_dur']-(1/60))
    
    # summarize findings
    summary = timing[['diff_fix','diff_noise','diff_feed','diff_stim']].describe(percentiles)
    summary['frame_dur'] = frame_summary
    summary.to_csv(out)
    print(summary)

if __name__ == '__main__':
    try:
        log = sys.argv[1]
        settings = sys.argv[2]
    except IndexError as e:
        print("Please provide a log file and a settings file")
        sys.exit(-1)
    else:
        run(log,settings)
