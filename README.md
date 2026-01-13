# Installation
(I'm aiming to package the project into a simple .exe file to increase accessibility)

1. Clone git repository
2. In cmd, navigate to the repository 
```
cd d:\coding_projects\BatBuddy # example, change the path to your location
```
3. Install environment using conda/[miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main)
```
conda env create -n batbuddy --file environment.yml
```
4. Activate the conda environment
```
conda activate batbuddy
```
## Analysing using UI
```
python app.py
```
## Analysing using python interface
1. Edit the parameters at the end of the 