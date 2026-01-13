# Installation
(I'm aiming to eventually package the project into a simple .exe file to increase accessibility)

1. Clone git repository
2. In cmd, navigate to the repository. Change the path in the example command below.
```
cd d:\coding_projects\BatBuddy
```
3. Install environment using conda/[miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main)
```
conda env create -n batbuddy --file environment.yml
```
4. Activate the conda environment
```
conda activate batbuddy
```
# Using the tool
## Analysing using UI
Simply open the tool in the command line:
```
python app.py
```
Parameter configuration is scarce in the UI, on purpose. If you're looking to change settings (like the overlap--as discussed in the paper, storing spectrograms, logging the analysis process in a csv file, or change the batch size), check out the next option:

## Analysing using python interface
1. Edit the parameters at the end of the script (underneath `if __name__ == "__main__":`)
    - `dir_list`: Single path or list of paths.
    - `log_path`: `False` or a path where to store/find log file if you want to log the analysis (so the tool can continue later on where it left of).
    - `files_per_batch`: Number of recordings checked before writing to output file. The risk of setting this too high is an out of memory crash. If you only have a couple of GBs of RAM, set this at 1000. If you have more to spare, the default value of 5000 should be fine.
    - `overlap`: 0 when not using sliding window approach. 0.1-0.9 when using sliding window, where 0.1 if the proportion overlap between subsequent spectrograms analysed.
    - `recursive`: `True` if all dirs inside the specified dir(s) should be analysed. `False` if only recordings in the specified dir in `dir_list`should be analysed.
    - `proc`: Number of logical processors to use to analyse recordings in parallel. This has been tested up until 12 processors, where runtime started leveling off around 8 processors. Results may vary on different machines. 
    
2. Run the program in the command line:
```
python main.py
```