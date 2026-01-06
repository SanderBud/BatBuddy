
import matplotlib
import ntpath
import numpy as np
from PIL import Image
import os
from pathlib import Path
from scipy.signal import istft, spectrogram, stft
from source.misc import read_clean_wav


""" Removes background noise form spectogram data """
def spectral_subtraction(signal,    
                         noise_estimation,
                         fs,
                         magn_weight=0.00,
                         nperseg=512):

    # Compute the Short-Time Fourier Transform (STFT)
    f, t, Sxx = stft(signal, fs=fs, nperseg=min(nperseg, len(signal)))  # Ensure nperseg is not larger than signal length

    # Compute the magnitude and phase of the STFT
    magnitude = np.abs(Sxx)
    phase = np.angle(Sxx)

    # Ensure noise_estimation array has the same shape as the magnitude (in terms of frequency bins)
    if len(noise_estimation) != magnitude.shape[0]:
        noise_estimation = np.interp(f, np.linspace(0, fs / 2, len(noise_estimation)), noise_estimation)

    # Subtract the estimated noise from the magnitude
    magnitude_denoised = np.maximum(magnitude - (magn_weight * noise_estimation[:, np.newaxis]), 0)

    # Reconstruct the complex STFT with denoised magnitude and original phase
    Sxx_denoised = magnitude_denoised * np.exp(1j * phase)

    # Use the same nperseg for inverse STFT as was used for STFT
    _, denoised_signal = istft(Sxx_denoised, fs=fs, nperseg=min(nperseg, len(signal)))

    return denoised_signal

""" Converts (segment) audio data to spectogram data """
def create_spectrogram_data(segment_data,
                       fs,
                       magn_weight,
                       segment_duration):
        # Spectrogram configuration
    N = 512  # FFT size
    nperseg = N  # Number of samples per segment
    overlap = 0.5  # Overlap ratio (0.0 to 1.0)
    noverlap = int(nperseg * overlap)

    if magn_weight > 0:
        # Estimate noise from the first 0.5 seconds (or adjust as needed)
        noise_estimation = np.mean(np.abs(segment_data[:int(0.5 * fs)]))  # Mean of the first half-second
        noise_estimation_array = np.full((nperseg // 2 + 1,), noise_estimation)  # Create an array for noise estimation

        # Apply spectral subtraction
        denoised_segment_data = spectral_subtraction(segment_data, noise_estimation_array, fs, magn_weight, nperseg)


        frequencies, times, Sxx = spectrogram(denoised_segment_data, fs=fs, window='hann',
                                            nperseg=nperseg, noverlap=noverlap)

    else:
        frequencies, times, Sxx = spectrogram(segment_data, fs=fs, window='hann',
                                    nperseg=nperseg, noverlap=noverlap)


    # Filter frequencies up to the desired limit
    max_freq = 120000  # Maximum frequency to display (120 kHz)
    nyquist_freq = fs / 2

    if nyquist_freq < max_freq:
        # Padding required since fs is insufficient to reach desired frequency
        additional_freqs = np.linspace(nyquist_freq, max_freq,
                                       int((max_freq - nyquist_freq) / (frequencies[1] - frequencies[0])))
        frequencies = np.concatenate([frequencies, additional_freqs])
        Sxx = np.pad(Sxx, ((0, len(additional_freqs)), (0, 0)), mode='constant', constant_values=0)
    else:
        # Filter frequencies up to the desired limit
        freq_limit = frequencies <= max_freq
        frequencies = frequencies[freq_limit]
        Sxx = Sxx[freq_limit, :]

    # Calculate padding if necessary
    total_time = times[-1]
    required_time = segment_duration

    if total_time < required_time:
        time_step = times[1] - times[0]   # actual delta t from spectrogram
        pad_width = int(np.round((required_time - total_time) / time_step))

        new_times = np.arange(start = total_time + time_step,
            stop  = required_time + 1e-9,  # tiny epsilon so we don’t miss the endpoint
            step  = time_step)

        # Pad Sxx with the same number of extra columns
        Sxx = np.pad(Sxx, ((0, 0), (0, len(new_times))), mode='constant', constant_values=0)
        times = np.concatenate([times, new_times])

    return frequencies, times, Sxx

""" Converts spectogram data to spectrogram with the right resolution and axis """
def viz_audio_segment(segment_data,
                        fs,
                        folder_struc,
                        filename_original,
                        segment_duration,
                        segment_number,
                        time_img,
                        colour_scale,
                        write_plot,
                        magn_weight,
                        draw_freq_lines):

    # Generate the spectrogram data
    frequencies, times, Sxx = create_spectrogram_data(segment_data=segment_data,
                                                 fs=fs,
                                                 magn_weight=magn_weight,
                                                 segment_duration=segment_duration)

    # Apply a logarithmic scale to the spectrogram
    Sxx_log = 10 * np.log10(Sxx + 1e-10)  # Avoid log of zero

    # Normalize to 0-1 for color mapping
    Sxx_norm = (Sxx_log - np.min(Sxx_log)) / (np.max(Sxx_log) - np.min(Sxx_log))

    # Apply the colormap
    cmap = matplotlib.colormaps.get_cmap(colour_scale)  # E.g., 'jet' or 'gray'
    image_array_rgba = cmap(Sxx_norm)  # Map to RGBA (4 channels)

    # Convert colormap to grayscale or RGB
    if colour_scale == "gray":
        image_array = (image_array_rgba[..., 0] * 255).astype(np.uint8)  # Grayscale (mode L)
    else:
        image_array = (image_array_rgba[..., :3] * 255).astype(np.uint8)  # RGB (mode RGB)

    # Correct orientation
    image_array = np.flipud(image_array)  # Flip vertically if necessary

    # Resize to 1200x400 pixels first
    image_pil = Image.fromarray(image_array)
    image_resized = image_pil.resize((1280, 400), Image.Resampling.LANCZOS)
    image_array_resized = np.array(image_resized)

    # Now draw the white lines for frequency intervals
    if draw_freq_lines:
        frequency_intervals = np.arange(0, 120_000, 20_000) 
        for idx in frequency_intervals:
            # Convert the frequency index to pixel index (scaled to resized image height)
            y_pos = int(idx / 120_000 * image_resized.height)
            
            # Ensure that y_pos is within bounds (between 0 and image height)
            y_pos = min(max(y_pos, 0), image_resized.height - 1)
                
            if colour_scale == "gray":
                # For grayscale, modify only the single channel
                image_array_resized[y_pos, :] = 255  # Set the entire row to white
            else:
                # For RGB, modify all three channels
                image_array_resized[y_pos, :, 0] = 255  # Set Red channel
                image_array_resized[y_pos, :, 1] = 255  # Set Green channel
                image_array_resized[y_pos, :, 2] = 255  # Set Blue channel


    if write_plot:
        # Save as an image
        os.makedirs(os.path.join(folder_struc, "img"), exist_ok=True)
        new_filename = f"IMG_{filename_original}_{segment_number:05d}_{time_img[0]}_{time_img[1]}.png"
        new_filepath = os.path.join(folder_struc, "img", new_filename)

        # Save image with correct mode
        if colour_scale == "gray":
            Image.fromarray(image_array_resized, mode="L").save(new_filepath)
        else:
            Image.fromarray(image_array_resized).save(new_filepath)

    # Return the image array and filename
    new_filename = f"IMG_{filename_original}_{segment_number:05d}_{time_img[0]}_{time_img[1]}.png"

    image_array_resized_bgr = image_array_resized[..., ::-1]

    return image_array_resized_bgr, new_filename

""" Full function to convert recording (of any duration) to seperate spectrograms """
def recording_to_visual(wav_file, output_size=1, overlap=0, colour_scale="jet", magn_weight=0, write_plot=False, draw_freq_lines=True):
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
        
        end = min(start + segment_samples, total_samples)
        segment_data = Audiodata[start:end]
        segment_start_time = start / fs
        start_time_file = int(segment_start_time * 1000)
        end_time_file = min(int((segment_start_time + output_size) * 1000), total_length) # calc end time without overshooting max file length
        time_img_list = [start_time_file, end_time_file] # Start and end time of segment in miliseconds

        # print(f"time_img_list: {time_img_list}")

        viz_audio_segment(segment_data=segment_data, 
                    fs=fs, 
                    folder_struc=folder_struc, 
                    filename_original=filename_original, 
                    segment_duration=output_size,
                    segment_number=segment_number, 
                    time_img=time_img_list,
                    colour_scale=colour_scale,
                    magn_weight=magn_weight,
                    write_plot=True,
                    draw_freq_lines=draw_freq_lines)

        segment_number += 1

        start += segment_samples - overlap_samples # advancing start position




if __name__ == "__main__":
    ## To change parameters in multiprocessing 
    # def process_file(filepath):
    #     # Call the spectrogram visualization function (for multiprocessing)
    #     recording_to_visual(filepath, 
    #                     output_size=1, 
    #                     overlap=0.5,
    #                     colour_scale="jet",
    #                     magn_weight=0,
    #                     write_plot=True,
    #                     draw_freq_lines=True)

    #     return filepath

    # path = R"data\comparison_accuracies_models"
    # files = []

    # # Collect all .wav files in the directory
    # for root, _, filenames in os.walk(path):
    #     for filename in filenames:

    #         if not filename.lower().endswith(".wav"):
    #             continue

    #         full_path = os.path.join(root, filename)
    #         files.append(full_path)

    # start_time = datetime.now()


    # # Use ProcessPoolExecutor for multiprocessing
    # with ProcessPoolExecutor() as executor:
    #     # Submit all file paths to the executor
    #     results = executor.map(process_file, files)

    #     # Track progress
    #     counter = 0
    #     for _ in results:
    #         counter += 1
    #         if counter % 100 == 0:
    #             print(f"{counter} sound files processed")

    #     print(f"Finished in {len(files)} soundfiles in {datetime.now() - start_time}")

    recording_to_visual(r"c:\Users\sanderb\OneDrive - NIOO\_Projects\Chapter6_ImageRecognition_Buzzes\data\script_tests\E2_DH009b_B012_M034_080_20230920_230900.wav", magn_weight=0.05)



