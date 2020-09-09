import os,sys,json
import pandas as pd

def run(log,settings):
    # prep files
    out = log.replace('.log','.csv').replace('log','timing')
    if not os.path.exists(os.path.dirname(out)):
          os.makedirs(os.path.dirname(out))  
    # load files
    with open(settings) as jsonfile:    
        param = json.load(jsonfile)
    df = pd.read_csv(log,delimiter='\t',header=None,names = ['timestamp','pp_type','type','idx','message'])
    # read out log file
    
    for cI,c in enumerate(['start_stim','start_fix','start_feed','start_select','start_timeout','end_trial']):
        if cI== 0:
            timing=df.loc[df.type.str.contains(c),['timestamp','idx']].set_index('idx').rename(columns={'timestamp':c})
        else:
            timing=timing.join(df.loc[df.type.str.contains(c),['timestamp','idx']].set_index('idx').rename(columns={'timestamp':c}))
            
    # compute phase durations
    timing['fix_dur'] = timing['start_stim']- timing['start_fix']
    timing['stim_dur'] = timing['start_select']- timing['start_stim']
    timing.loc[pd.isna(timing['start_select']),'stim_dur'] = timing.loc[pd.isna(timing['start_select']),'start_timeout']- timing['start_stim']
    timing['feed_dur'] = timing.loc[pd.notna(timing['start_feed']),'end_trial']- timing['start_feed']
    timing['trial_dur'] = timing['end_trial']- timing['start_fix']
    timing['select_dur'] = timing['start_feed']- timing['start_select']
    timing['resp_dur'] = timing['start_timeout']- timing['start_stim']
    timing= timing.join(df.loc[df.type.str.contains('start_fix'),['message','idx']].set_index('idx').rename(columns={'message':'planned_fix_dur'}))
    timing= timing.join(df.loc[df.type.str.contains('start_select'),['message','idx']].set_index('idx').rename(columns={'message':'planned_select_dur'}))
    timing['planned_feed_dur'] = param['timing_info']['feed_dur']+0.008
    timing['planned_resp_dur'] = param['timing_info']['resp_dur']+0.008
    
    # compute timing accuracy
    timing['diff_feed']= timing['planned_feed_dur']-timing['feed_dur']
    timing['diff_select']= timing['planned_select_dur']-timing['select_dur']
    timing['diff_fix']= timing['planned_fix_dur']-timing['fix_dur']
    timing['diff_resp']= timing['planned_resp_dur']-timing['resp_dur']

    # summarize findings
    summary = timing[['diff_fix','diff_select','diff_feed','diff_resp']].describe()
    summary.to_csv(out)
    print(summary)
    return summary

if __name__ == '__main__':
    try:
        log = sys.argv[1]
        settings = sys.argv[2]
    except IndexError as e:
        print("Please provide a log and a settings file")
        sys.exit(-1)
    else:
        run(log,settings)