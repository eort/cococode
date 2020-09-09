import pandas as pd
import os,sys,glob,json
import numpy as np


dat_file =sys.argv[1]
allDat = pd.read_csv(dat_file)
for i in range(200):
    allDat['choice']= np.random.permutation(allDat.choice.values)
    allDat['sub_id']= i

    outpath= os.path.join('temp','sub-{:02d}.csv'.format(i))
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    allDat.to_csv(outpath)
