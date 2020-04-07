# cococode
Code of the Coconut lab (HHU-Jocham)

**Installation of Python Environment**

1) *Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html).* Download the installer and install conda (a package and environment manager for, among others, Python) for your system. The experiments were written for Python 3.6, so it was very likely that they won't work out of the box for Python 2.7. Therefore, it is adviseable to choose miniconda for Python 3. 
2) *Download psypy_environment.yml from this repository.* Unless you have already cloned or downloaded this repository, download this `.yml` file. This is a text file that lists packages and dependencies that are needed to run the experiment. There is a fair chance it would also run with other configurations, but it has only been tested with this environment. 
3) *Install the environment.* Open a terminal (Anaconda terminal on Windows?) and run conda `env create -n psychopy -f psychopy-env.yml` to install this conda environment. If you want to call your environment differently, replace `psychopy` with the name you want.  
4) *Activate environment.* Once an environment is installed it can be activated by calling `conda activate psychopy`. This has to be done every time you open a new terminal (unless it is set to be the default environment). 

For more info on how to manage environments, please check the [conda documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html#managing-envs)

**Running experiment**

To run an experiment, you need to run python with the experiment and a configuration file from within the root folder of that experiment. For example, to run the value-based decision making task, you first need to navigate to VBM (if you are in the root folder of this repository you can run`cd ./experiments/VBM`) and then run the experiment: `python vbm.py meg_cfg.json`. Note, if you have closed the terminal after you have installed the environment (see above), you need to activate the environment again. 

# Experiments
 Includes code and other files necessary to run the respective experiments

# Analysis
Code for running analyses
