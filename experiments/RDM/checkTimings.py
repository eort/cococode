"""
checks whether the timing of the experiments is within reasonable limits. 
"""
import sys,json
import pandas as pd

def run(f):
    # load files
    df = pd.read_csv(f,delimiter='\t',header=None,names = ['timestamp','pp_type','type','idx','message'])
    s = 'settings' + f[3:] 
    s = s[:-3] + 'json'
    with open(s) as jsonfile:    
        param = json.load(jsonfile)

    # read out frame info
    stim_frame=df[['timestamp','idx','message']].loc[df.type.str.contains('cloud_frame')].set_index(['idx','message']).rename(columns={'timestamp':'cloud_frame'})
    nostim_frame=df[['timestamp','idx','message']].loc[df.type.str.contains('nostim_frame')].set_index(['idx','message']).rename(columns={'timestamp':'nostim_frame'})

    # summarize frame info
    cloud_frame_summary=stim_frame['frame']= stim_frame.groupby('idx').diff(1).describe()
    nostim_frame_summary=nostim_frame['frame']= nostim_frame.groupby('idx').diff(1).describe()  
    print(cloud_frame_summary,nostim_frame_summary)

    # last frame of each phase
    end_cloud_time = stim_frame.reset_index().groupby('idx').max()
    end_stim_time = nostim_frame.reset_index().groupby('idx').max()

    # read out log file
    for cI,c in enumerate(['start_stim','start_fix','start_feed','start_noise','end_trial','resp_time']):
        if cI== 0:
            timing=df[['timestamp','idx']].loc[df.type.str.contains(c)].set_index('idx').rename(columns={'timestamp':c})
        else:
            timing=timing.join(df[['timestamp','idx']].loc[df.type.str.contains(c)].set_index('idx').rename(columns={'timestamp':c}))

    # compute phase durations
    timing['fix_dur'] = timing['start_noise']- timing['start_fix']
    timing['noise_dur'] = timing['start_stim']- timing['start_noise']
    timing['feed_dur'] = timing['end_trial']- timing['start_feed']
    timing['trial_dur'] = timing['end_trial']- timing['start_fix']

    timing= timing.join(df[['message','idx']].loc[df.type.str.contains('start_noise')].set_index('idx').rename(columns={'message':'planned_noise_dur'}))
    timing['planned_feed_dur'] = param['timing_info']['feed_dur']+0.008
    timing['planned_fix_dur'] = param['timing_info']['fix_dur']+0.008
    
    # compute timing accuracy
    timing['diff_feed']= timing['planned_feed_dur']-timing['feed_dur']
    timing['diff_noise']= timing['planned_noise_dur']-timing['noise_dur']
    timing['diff_fix']= timing['planned_fix_dur']-timing['fix_dur']
    
    # summarize findings
    summary = timing[['diff_fix','diff_noise','diff_feed']].describe()
    print(summary)
    return summary
if __name__ == '__main__':
    try:
        f = sys.argv[1]
    except IndexError as e:
        print("Please provide a log file")
        sys.exit(-1)
    else:
        run(f)
