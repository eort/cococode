"""
checks whether the timing of the experiments is within reasonable limits. 
"""
import sys,json,os,glob
import pickle
import pandas as pd
from IPython import embed as shell
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

def run(dat_file):
    # load files
    
    assert os.path.isdir(dat_file)     
    outpath=dat_file.replace('dot_xy','results')
    os.makedirs(os.path.dirname(outpath), exist_ok=True)

    allFiles = sorted(glob.glob(os.path.join(dat_file,'sub-*_ses-*_task-rdm_*.pkl')))
    n_blocks = 17
    n_trials = 53    
    positions = []
    try:
        for f in allFiles:
            with open(f,'rb') as jsonfile:    
                positions.append(pickle.load(jsonfile))
    except ValueError as e:
        print("ERROR: There are no files in this directory")
        sys.exit(-1)        

    trial_pos=positions[0].loc[1,'positions']

    outpath=dat_file.replace('dot_xy','temp')
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    

    class AnimatedScatter(object):
        """An animated scatter plot using matplotlib.animations.FuncAnimation."""
        def __init__(self, data):
            self.data = data
            self.stream = self.data_stream()
            # Setup the figure and axes...
            self.fig, self.ax = plt.subplots(figsize = [5,5])
            # Then setup FuncAnimation.
            self.ani = animation.FuncAnimation(self.fig, self.update, interval=16,init_func=self.setup_plot, blit=True,repeat=False,save_count=self.data.shape[0]-1)

        def setup_plot(self):
            """Initial drawing of the scatter plot."""
            try:
                x, y = next(self.stream).T
            except StopIteration:
                print('Data empty')
            self.scat = self.ax.scatter(x, y,c='black',s=1)
            self.ax.axis([-400, 400, -400, 400])
            return self.scat,

        def data_stream(self):
            for fr in range(self.data.shape[0]):
                xy = self.data[fr,]
                yield np.c_[xy[:,0], xy[:,1]]

        def update(self,i):
            """Update the scatter plot."""
            data = next(self.stream)
            # Set x and y data...
            self.scat.set_offsets(data[:, :2])
            return self.scat,

    for bl in range(n_blocks):
        for tr in range(1,n_trials+1):
            trial_pos=positions[0].loc[tr,'positions']
            # exclude empty frames
            last_idx = np.where(trial_pos.sum(-1).sum(-1)==0)[0][0] 
            trial_pos = trial_pos[:last_idx+1,]
            print(outpath+'dots_block-{}_trial-{}.mp4'.format(bl+1,tr))
            # run animation
            a = AnimatedScatter(trial_pos)
            a.ani.save(outpath+'dots_block-{}_trial-{}.mp4'.format(bl+1,tr))
            plt.close()        

            # potential processing of trial data

            # compute distance of each dot to the center
        
            #distance = np.sqrt(trial_pos[:,:,0]**2+trial_pos[:,:,1]**2)
            # find indices of dots when new dots changed
            #dot_idx, frame_idx = 1new_dots = np.where(np.absolute(np.diff(distance,axis=0).T)>5)     
            # find angle of each dot relative to either first dot in sequence or (0,0)
            # only implemented for 2 d array, not 3d
            #angles = [np.degrees(np.math.atan2(i-228.2,j+54.9)) for i,j in zip(a[:,0],a[:,1])]


if __name__ == '__main__':
    try:
        f = sys.argv[1]
    except IndexError as e:
        print("Please provide a log file")
        sys.exit(-1)
    else:
        run(f)
