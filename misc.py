
import os
import numpy as np
import warnings
from scipy.io import wavfile
from scipy.io.wavfile import WavFileWarning
from scipy.signal import butter, lfilter


""" Reads recording (with high-pass filter and error checks) """
def read_clean_wav(filepath): 
    # Suppress specific warning
    warnings.filterwarnings("ignore", category=WavFileWarning) # Throws warning for many wav files because it doesnt recognise the metadata
    
    # Load file
    try:
        fs, Audiodata = wavfile.read(filepath)

        if Audiodata.size == 0:
            with open(os.path.join(os.path.dirname(filepath), "corrupted_files_log.txt"), "a") as log:
                log.write(os.path.basename(filepath) + "\t" + "File does not contain audio data" + "\n")
            return None, None

    except Exception as e:
        # print(f"file: {filepath}, error: {e}")

        with open(os.path.join(os.path.dirname(filepath), "corrupted_files_log.txt"), "a") as log:
            log.write(os.path.basename(filepath) + "\t" + str(e) + "\n")
        return None, None

    # High-pass filter
    cutoff = 15_000 # 15kHz
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(5, normal_cutoff, btype='high', analog=False)
    Audiodata = lfilter(b, a, Audiodata)
    Audiodata = Audiodata / np.max(np.abs(Audiodata)) # normalise audio data

    return fs, Audiodata

""" Get dirs that contain at least one wav file """
def get_dirs_wav(head_dir_list):
    # Make sure head_dir is a list
    if not isinstance(head_dir_list, list): head_dir_list = [head_dir_list]

    # Get list of paths to dirs containing wav files 
    list_dirs = set()
    for head_dir in head_dir_list:
        for root, _, files in os.walk(head_dir):
            for file in files:
                
                if not file.lower().endswith(".wav"):
                    continue

                list_dirs.add(root)

    return list(list_dirs)