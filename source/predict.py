
import ntpath
import os
from pathlib import Path
import source.visualise as vis
import torch
import warnings
from source.misc import read_clean_wav

warnings.filterwarnings("ignore", "You are using `torch.load` with `weights_only=False`*.")

""" Predicts based on nparray (data of spectogram) and outputs tabular data """
def predict_sono(model,
                 img_array,
                 filenames,
                 wav_path,
                 save_directory=R"kaas",
                 save=False):

    if save and save_directory == R"kaas":
        raise ValueError("Define save dir before continuing")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    subfolder_name = "img_predict"
    if save: os.makedirs(os.path.join(save_directory, subfolder_name), exist_ok=True)

    # Use these values in the model.predict() call
    results = model.predict(source=img_array, 
                            save=save, 
                            verbose=False,
                            device=device,
                            # project=os.path.join(save_directory, subfolder_name), 
                            # name="", 
                            conf=0.1, iou=0.4)

    # Data to tabular format
    csv_data = []
    for idx, result in enumerate(results):

        for box in result.boxes:
            # Extract bounding box information
            x_min, y_min, x_max, y_max = box.xyxy[0].tolist()

            # Timing and frequency
            height, width = result.orig_shape[:2]
            y_min_corrected = height - y_max  # Reverse y_min if spectrogram has reversed y-axis
            y_max_corrected = height - y_min  # Reverse y_max if spectrogram has reversed y-axis

            filename_stem = os.path.splitext(filenames[idx])[0]

            start_file = (int(filename_stem.split("_")[-2]))
            start_time = f"{(x_min / width) * 1000 + start_file :.0f}"  # Start time in ms
            end_time = f"{(x_max / width) * 1000 + start_file :.0f}"    # End time in ms

            # Frequency range calculations
            freq_min = f"{y_min_corrected * (120 / height) :.0f}"  # Min frequency in kHz
            freq_max = f"{y_max_corrected * (120 / height) :.0f}"  # Max frequency in kHz

            # Other metadata
            category = result.names[int(box.cls[0])]  # Get category name
            confidence = float(box.conf[0])  # Get confidence score

            # Prepare row for CSV
            csv_data.append({
                "filename": os.path.basename(wav_path),
                "filepath": wav_path,
                "category": category,
                "confidence": confidence,
                "start_time_ms": start_time,
                "end_time_ms": end_time,
                "freq_min": freq_min,
                "freq_max": freq_max
            })

    return csv_data 

""" Function to process a single wav file with overlapping segments """
def recording_to_predict(wav_file, model, output_size=1, overlap=0, colour_scale="jet", write_plot=False, cancel_event=None):
    fs, Audiodata = read_clean_wav(wav_file)

    if fs is None or Audiodata is None:
        return []

    filename_original = Path(ntpath.basename(wav_file)).stem
    folder_struc = ntpath.dirname(wav_file)
    segment_samples = int(round((output_size) * fs, 0)) # Calculate samples with frames per second * output in seconds
    overlap_samples = int(round(overlap * fs, 0))  

    list_img_array = []
    filename_list = []
    segment_number = 1
    total_samples = len(Audiodata)
    total_length = int((len(Audiodata) / fs) * 1000) # file length in ms

    start = 0
    end = 0

    # Process each overlapping segment of the audio file
    while end < total_samples:

        if cancel_event and cancel_event.is_set():  # Check for cancellation
            return []

        end = min(start + segment_samples, total_samples)
        segment_data = Audiodata[start:end]
        segment_start_time = start / fs
        start_time_file = int(segment_start_time * 1000)
        end_time_file = min(int((segment_start_time + output_size) * 1000), total_length) # calc end time without overshooting max file length
        time_img_list = [start_time_file, end_time_file] # Start and end time of segment in miliseconds

        img_array, filename = vis.viz_audio_segment(segment_data=segment_data, 
                                            fs=fs, 
                                            folder_struc=folder_struc, 
                                            filename_original=filename_original, 
                                            segment_duration=output_size,
                                            segment_number=segment_number, 
                                            time_img=time_img_list,
                                            colour_scale=colour_scale,
                                            write_plot=False,
                                            magn_weight=0,
                                            draw_freq_lines=True)

        list_img_array.append(img_array)
        filename_list.append(filename)
        segment_number += 1

        start += segment_samples - overlap_samples # advancing start position
    
    if not list_img_array:
        print(filename_original)
        
    # Predict and return the result
    csv_data = predict_sono(model=model,
                            img_array=list_img_array,
                            filenames=filename_list,
                            wav_path=wav_file,
                            save=False)

    return csv_data


