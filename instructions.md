**Installation Of Python Environment**

1) *Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html).* Download the installer and install conda (a package and environment manager for, among others, Python) for your system.*
2) *Download psypy_environment.yml from this repository.* This is a text file that lists packages and dependencies that are needed to run the experiment. There is a fair chance it would also run with other configurations, but it has only be tested with this environment. 
3) *Install the environment.* Run conda `env create -n psychopy -f psychopy-env.yml` to install this conda environment. If you want to call your environment differently, replace `psychopy` with the name you want.  
4) *Activate environment.* Once an environment is installed it can be activated by calling `conda activate psychopy` This has to be done every time you open a new terminal (unless it is set to be the default environment). 

For more info on how to manage environments, please check the [conda documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html#managing-envs)

**Running experiment**
