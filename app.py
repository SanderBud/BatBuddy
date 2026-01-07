import tkinter as tk
from tkinter import filedialog, StringVar, Label, Button, ttk
import threading
from multiprocessing import Manager, Event
import os
import sys

from main import main

class App:
    """ Initilising app """
    def __init__(self, root):

        # Inititialise window 
        self.root = root                                    
        self.root.title("BatCallr")
        self.root.geometry("1240x640")

        self.root.grid_rowconfigure(0, weight=1)            
        self.root.grid_columnconfigure(0, weight=1)

        self.frame = tk.Frame(self.root, bg="white")
        self.frame.grid(padx=10, pady=10, sticky="nsew")  

        self.frame.grid_columnconfigure(0, weight=1)

        # Selection of folders 
        self.dir_var = StringVar(value="No folders selected")                                                                  
        self.dirs = []

        self.button_browse_frame = tk.Frame(self.frame, bg="white")
        self.button_browse_frame.grid(row=0, column=0, padx=25, pady=25, sticky="w")

        button_browse = Button(master=self.button_browse_frame, text="Select Folder", command=self.select_folders)       
        button_browse.pack(side="left", padx=(0,10))
        
        button_browse_multi = Button(master=self.button_browse_frame, text="Select Multiple Folders", command=self.select_folders_multi)       
        button_browse_multi.pack(side="left")

        info_browse = tk.Label(master=self.button_browse_frame, text="ℹ", fg="blue", bg="white", cursor="question_arrow")
        info_browse.pack(side="top", padx=10)
        ToolTip(info_browse, "You can select one folder at a time. Opens multiple windows. \nCancel folder browsing to complete folder selection and continue with the analysis")

        lbl1 = Label(master=self.frame, textvariable=self.dir_var, bg="white", fg="#6E6E6E", justify="left")                              
        lbl1.grid(row=1, column=0, padx=25, pady=5, sticky="w")

        # Seperator line 
        sp1 = ttk.Separator(self.frame, orient="horizontal")
        sp1.grid(row=2, column=0, padx=25, pady=5, sticky="ew")

        # Other parameters (recursive, cores)
        ## Recursive analysis of folders
        self.var_recursive = tk.BooleanVar(value=False)
        checkbox_recursive = tk.Checkbutton(self.frame, text="Include subfolders in analysis", variable=self.var_recursive, onvalue=True, offvalue=False, bg="white")
        checkbox_recursive.grid(row=3, column=0, padx=25, pady=5, sticky="w")

        ## Cores
        self.cores_frame = tk.Frame(self.frame, bg="white")
        self.cores_frame.grid(row=4, column=0, padx=15, pady=0, sticky="w")
        self.var_cores = tk.IntVar(value=8)
        lbl_cores = tk.Label(master=self.cores_frame, text="Parallel processes", bg="white")
        lbl_cores.pack(side="left", padx=10, pady=10)

        cores = list(range(1, (os.cpu_count() or 64) + 1))

        spin_cores = ttk.Combobox(
            self.cores_frame,
            textvariable=self.var_cores,
            values=cores,
            width=5,
            state="readonly"
        )
        spin_cores.pack(side="left", padx=10, pady=10)

        info_cores = tk.Label(self.cores_frame, text="ℹ", fg="blue", bg="white", cursor="question_arrow")
        info_cores.pack(side="top", padx=10)
        ToolTip(info_cores, "Select number of logical processors the tool can use to analyse the recordings in parallel. \nUse a lower number of processors when you still need to use the computer for other tasks.")

        # Seperator line 
        sp2 = ttk.Separator(self.frame, orient="horizontal")
        sp2.grid(row=5, column=0, padx=25, pady=5, sticky="ew")


        # Start analysis button 
        self.button_frame = tk.Frame(self.frame, bg="white")
        self.button_frame.grid(row=7, column=0, padx=25, pady=15, sticky="w")

        self.manager = Manager()
        self.start_event = self.manager.Event()
        self.button_start = Button(master=self.button_frame, text="Start Analysis", command=self.start_analysis)
        self.button_start.pack(side="left", padx=(0,10))

        # Cancel analysis
        self.cancel_event = self.manager.Event()
        self.button_cancel = Button(master=self.button_frame, text="Cancel Analysis", command=self.cancel_analysis, state="disabled")
        self.button_cancel.pack(side="left")

        # Logging management
        ## Update label
        self.msg_update_var = tk.StringVar()
        self.msg_update_label = tk.Label(self.frame, textvariable=self.msg_update_var, bg="white")
        self.msg_update_label.grid(row=8, column=0, sticky="w", padx=25, pady=3)
        
        ## Current folder label
        self.msg_current_folder_var = tk.StringVar()
        self.msg_current_folder_label = tk.Label(self.frame, textvariable=self.msg_current_folder_var, bg="white")
        self.msg_current_folder_label.grid(row=9, column=0, sticky="w", padx=25, pady=3)

        ## Progress label
        self.msg_progress_var = tk.StringVar()
        self.msg_progress_label = tk.Label(self.frame, textvariable=self.msg_progress_var, bg="white")
        self.msg_progress_label.grid(row=10, column=0, sticky="w", padx=25, pady=3)

        ## Log text label
        self.msg_log_output = tk.Text(self.frame, height=20, width=100, font=("Calibri", 10))
        self.msg_log_output.grid(row=11, column=0, padx=25, pady=5, sticky="nsew")

        ## Queue for messages from script
        self.msg_queue = self.manager.Queue()
        self.root.after(100, self.poll_queue)


    """ Select single folders to analyse """
    def select_folders(self): 
        self._clear_selected_folders()

        d = filedialog.askdirectory()

        if d not in self.dirs:
            self.dirs.append(d)
            self.dir_var.set("\n".join(self.dirs))


    """ Select multiple folders to analyse """
    def select_folders_multi(self): 
        self._clear_selected_folders()
        
        while True:
            d = filedialog.askdirectory()
            if not d:    # user cancelled -> stop
                break
            if d not in self.dirs:
                self.dirs.append(d)
                self.dir_var.set("\n".join(self.dirs))

    def _clear_selected_folders(self):
        self.dir_var.set("No folders selected")                                                        
        self.dirs = []


    """ Starts analysis using parameters selected in the GUI """
    def start_analysis(self):
        if not self.dirs:
            print("No folders selected.")
            self.msg_update_var.set("No folders selected")
            return

        # Run in background thread
        self.cancel_event.clear()
        self.button_cancel.config(state="normal")   
        self.button_start.config(state="disabled")  
        self.msg_log_output.delete('1.0', tk.END)
        self.msg_update_var.set("Initialising...")

        self.worker = threading.Thread(
            target=main,
            kwargs={"dir_list": self.dirs, "recursive": self.var_recursive.get(), "log_path": False, "msg_queue": self.msg_queue, "cancel_event": self.cancel_event, "app": True},
            daemon=True
        )
        self.worker.start()


    """ Cancel analysis """
    def cancel_analysis(self):
        if not getattr(self, "worker", None) or not self.worker.is_alive():
            self.msg_update_var.set("No analysis to cancel")
            return

        self.cancel_event.set()
        self.msg_update_var.set("Canceling analysis...")
        self.msg_progress_var.set("")
        self.msg_log_output.insert(tk.END, "\nAnalysis canceled by user")
        self.msg_log_output.see(tk.END)


    """ Periodically check status of worker and message queue """
    def poll_queue(self):
        while not self.msg_queue.empty():
            msg = self.msg_queue.get()
            if isinstance(msg, tuple) and msg[0] == "update":
                self.msg_update_var.set(msg[1])
            elif isinstance(msg, tuple) and msg[0] == "current_folder":
                self.msg_current_folder_var.set(msg[1])
            elif isinstance(msg, tuple) and msg[0] == "progress":
                self.msg_progress_var.set(msg[1])
            elif isinstance(msg, tuple) and msg[0] == "log":
                self.msg_log_output.insert(tk.END, msg[1])
                self.msg_log_output.see(tk.END)

        if hasattr(self, "worker") and self.worker is not None:
            if not self.worker.is_alive():
                self._analysis_finished()
                self.worker = None 

        self.root.after(100, self.poll_queue)


    """ Makes start button available and cancel button disabled when the script stops running """
    def _analysis_finished(self):
        self.button_start.config(state="normal")
        self.button_cancel.config(state="disabled")

        self.msg_current_folder_var.set("")
        self.msg_update_var.set("")


class ToolTip:
    def __init__(self, widget, text, delay=500):
        self.widget, self.text, self.delay = widget, text, delay
        self.tip = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)

    def _schedule(self, _):
        self.after_id = self.widget.after(self.delay, self._show)

    def _show(self):
        if self.tip or not self.text:
            return
        x, y = self.widget.winfo_pointerxy()
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x+10}+{y+10}")
        tk.Label(self.tip, text=self.text, justify="left",
                 background="#ffffe0", relief="solid", borderwidth=1,
                 font=("Segoe UI", 9)).pack(padx=5, pady=3)

    def _hide(self, _):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
