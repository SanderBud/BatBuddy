
import pandas as pd
import os

""" Try to read log file with error management """
def read_log_file(log_path):
    try:
        df = pd.read_csv(log_path)  
        return df  # Return the DataFrame if successful

    except pd.errors.EmptyDataError:
        print(f"Error: The file '{log_path}' is empty.")
        return None  

    except pd.errors.ParserError:
        print(f"Error: The file '{log_path}' could not be parsed. Please check the file format.")
        return None  

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None  


""" Check if log file contains expected columns, column names, and values """
def log_file_correctness_check(df):

    if df is None or df.empty: raise ValueError("The log file could not be read or is empty.")  # Raises an error if the DataFrame is invalid

    shape = df.shape

    if shape[1] != 2: raise SystemExit("\nLog file Error: The log file does not contain the expected number of columns.") # Raises an error when more than 2 columns exist
    if not list(df.columns) == ["dir", "done"]: raise SystemExit("\nLog file Error: The columns of the log file are not named as expected.") # Raises an error when columns are not names correctly
    if not set(pd.unique(df["done"])).issubset({"yes", "no"}):  raise SystemExit("\nLog file Error: The 'done' column contains unexpected values. Can only contain 'yes' or 'no'.") # raises error when column contains values that are not 'yes' or 'no'

    return

""" Check if logging is requested. If so, if log file already exists and continue where left of. If not exists, create new log file """
def logging(path, dirs):
    
    if path is False:  
        print("No log requested. Starting analysis without logging progress.")
        return(dirs)
    else:
        log_path = os.path.join(path, "log.csv")  

        log_file = pd.DataFrame({"dir": dirs}) # To compare to existing log file or save when no log file exists
        log_file["done"] = "no"

        if os.path.isfile(log_path): # Checks if there is an existing log file
            print(f"Log file exists. ", end="")

            df = read_log_file(log_path)

            log_file_correctness_check(df) 

            log_file_read = df.sort_values("dir")

            if list(log_file["dir"]) == list(log_file_read["dir"]): # Will continue analysis if list of dirs to analyse match the list of dirs in the log file
                print(f"Continue analysis where we left off. ", end="")
                len_dirs = len(dirs)
                dir_list = log_file_read.loc[log_file_read["done"] == "no", "dir"].tolist()
                skipped_dirs = len_dirs - len(dir_list)
                print(f"Already analysed dirs: {skipped_dirs}")

                if not len(dir_list): # Exit if all dirs have been analysed
                    print(f"All dirs are already analysed! See you next time.")
                    exit()

            else: # Exits if there is an existing log file but doenst match current list of dirs that need to be analysed
                print(f"The analysed folders, as indicated in your log file, do not match the folders that you want to analyse. Archive or rename the existing logfile to continue.")
                exit()

        else:
            print(f"No log file exists. Initialising log file for analysis. ", end="")
            log_file.to_csv(log_path, index=False)

            print(f"Log file stored in {log_path}")
            return(dirs)
    
    return(dir_list)