
from datetime import datetime, timedelta
import glob
import os
from misc import get_dirs_wav
import log
import csv
import sys
import math
import pandas as pd
from ultralytics import YOLO
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from misc import read_clean_wav
from predict import recording_to_predict

""" Main function to process all wav files """
def main(
    dir_list, # Single path or list of paths
    log_path, # False or name of dir where to store/find log file
    msg_queue=None, 
    cancel_event=None,
    model_path=r"data\models\0016_best.pt", # Location of YOLOv8 model
    files_per_batch=10_000, # Number of recordings checked before writing to output file
    output_name=False, # False or name of output name. Output name will be supplemented with the recording file index of which the output is stored in that specific file
    recursive=True, # True (if all folders should be checked recursively for wav files) or False (if only wav files in the folder paths as assigned in 'dir_list' should be analysed)
    proc=8, # Number of processors to use to speed up analysis
    overlap=0.3, # 0 when not using sliding window approach. 0.1-0.9 when using sliding window, where 0.1 if the proportion overlap between subsequent spectrograms analysed.
    app=False):

    """ Preliminaries (find directories with recordings, set parameters, etc) """
    model = YOLO(model_path)

    if recursive: dir_list = get_dirs_wav(head_dir_list=dir_list)
    dir_list.sort()

    dir_list_check = log.logging(path=log_path, dirs=dir_list) # Handles all logging functionality when path is not False

    if len(dir_list_check) == 0:
        print("No folders with wav-files found") 
        if app: msg_queue.put(("update", f"No folders with wav-files found"))
        return

    print(f"Starting analysis. Total dirs: {len(dir_list_check)}")
    if app: msg_queue.put(("update", f"Starting analysis of {len(dir_list_check)} folders"))


    """ Analyse recordings per directory """
    recording_to_predict_with_model = partial(recording_to_predict, model=model, output_size=1, overlap=overlap, colour_scale="jet", write_plot=False, cancel_event=cancel_event)

    count_dir = 1
    for dir in dir_list_check:
        start_time_dir = datetime.now()
        
        if app: 
            msg_queue.put(("update", f"Analysing... Working on folder {count_dir} of {len(dir_list_check)}"))
            msg_queue.put(("current_folder", f"Current folder: {dir}"))
            msg_queue.put(("progress", ""))

            count_dir += 1

        file_paths = glob.glob(os.path.join(dir, "*.[Ww][Aa][Vv]"))

        # file_paths = [
        #     f for f in glob.glob(os.path.join(dir, "*.[Ww][Aa][Vv]"))
        #     if "Chan08" in os.path.basename(f)
        # ]

        total_files = len(file_paths)

        if len(file_paths) == 0: 
            print("No wav-files found") 
            if app: msg_queue.put(("progress", f"No wav-files found"))
            time.sleep(5)
            continue
        
        
        print("---------")

        print(f"Analysing {total_files} wav-files in {dir}.")

        """ Analyse in multiple batches when too many wav-files in dir """
        rounds = math.ceil(total_files / files_per_batch)
        start_idx = 0

        for i in range(0, rounds):
            csv_data_total = []
            
            stop_idx = min((start_idx + files_per_batch), total_files)
            index_file_paths = file_paths[start_idx:stop_idx]
            index_file_paths_len = len(index_file_paths)

            print_batch_message = f"\tAnalysing files {start_idx+1} - {stop_idx}... "
            sys.stdout.write(print_batch_message)
            sys.stdout.flush()
            if app: msg_queue.put(("progress", f"Analysing files {start_idx+1} - {stop_idx}... "))

            """ Using multiprocessing to process files in parallel """
            with ProcessPoolExecutor(max_workers=proc) as executor:
                results = executor.map(recording_to_predict_with_model, index_file_paths)

                # Track progress
                start_time = datetime.now()
                for counter, result in enumerate(results, start=1):

                    if cancel_event and cancel_event.is_set(): return

                    if result: csv_data_total.extend(result)

                    if counter % 10 == 0 or counter == index_file_paths_len or counter == 0:
                        elapsed_time = (datetime.now() - start_time).total_seconds()
                        time_per_file = elapsed_time / counter
                        remaining_files = index_file_paths_len - counter
                        estimated_time_left = time_per_file * remaining_files

                        if app: 
                            msg_queue.put(("progress", f"{f"Analysing files {start_idx+1} - {stop_idx}... "}: Processed {counter}/{index_file_paths_len} files... ETA: {str(timedelta(seconds=int(estimated_time_left)))}"))
                        else:
                            sys.stdout.write(f"\r{print_batch_message} Processed {counter}/{index_file_paths_len} files... Estimated time left: {str(timedelta(seconds=int(estimated_time_left)))} ")
                            sys.stdout.flush()

            """ Predictions to csv file """
            if not output_name: 
                output_name_new = f"output_{start_idx+1}-{stop_idx}.csv"
            else:
                output_name_new = output_name + f"_{start_idx+1}-{stop_idx}.csv"

            output_name_path = os.path.join(dir, output_name_new)
            
            with open(output_name_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=["filename", "filepath", "category", "confidence", "start_time_ms", "end_time_ms", "freq_min", "freq_max"])
                writer.writeheader()
                writer.writerows(csv_data_total)

            time_batch = datetime.now() - start_time
            formatted_time = str(timedelta(seconds=int(time_batch.total_seconds())))
            sys.stdout.write(f"\r{print_batch_message} Finished in {formatted_time}. Output stored in {output_name_new}\n")
            sys.stdout.flush()

            if app: msg_queue.put(("progress", f"{print_batch_message} Finished in {formatted_time}. Output stored in {output_name_new}"))

            start_idx += files_per_batch


        """ Log results and print to console/app """
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        dir_duration = str(timedelta(seconds=int((datetime.now() - start_time).total_seconds())))
        if app: msg_queue.put(("log", f"{timestamp} Finished in {dir_duration}. Output stored in {os.path.join(dir, output_name_new)}\n"))

        # Update log file
        if log_path is not False:
            log_path_csv = os.path.join(log_path, "log.csv")
            log_file = pd.read_csv(log_path_csv)
            log_file.loc[log_file["dir"] == dir, "done"] = "yes"
            log_file.to_csv(log_path_csv, index=False)

    if app: 
        msg_end = "\nAll folders are analysed. See you next time!"
        msg_queue.put(("update", "Done!"))
        msg_queue.put(("current_folder", ""))
        msg_queue.put(("progress", ""))
        
        msg_queue.put(("log", msg_end))


if __name__ == "__main__":

    head_dir = r"e:\buzz"

    main(
        dir_list=head_dir,
        model_path=r"data\models\0016_best.pt",
        log_path=head_dir,
        recursive=True,
        proc=8
        )