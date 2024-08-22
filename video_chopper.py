import os
import math
from shutil import copyfile
from tkinter import Tk, Label, Button, Scale, filedialog, HORIZONTAL, Text, END, IntVar, StringVar, DoubleVar
from tkinter import ttk
from moviepy.editor import VideoFileClip, vfx
import threading

class VideoChopper:
    def __init__(self, master):
        self.master = master
        master.title("Enhanced Video Chopper")

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", padding=10, font=("Arial", 12))
        self.style.configure("TButton", padding=10, font=("Arial", 12))
        self.style.configure("TScale", padding=10)
        
        main_frame = ttk.Frame(master, padding="20")
        main_frame.pack(fill="both", expand=True)

        self.segment_length = IntVar(value=15)
        self.speed_multiplier = DoubleVar(value=1.0)

        ttk.Label(main_frame, text="Select segment length (seconds):").grid(column=0, row=0, sticky="w")
        self.slider = ttk.Scale(main_frame, from_=1, to=30, orient=HORIZONTAL, variable=self.segment_length, length=300, command=self.update_slider_value)
        self.slider.grid(column=0, row=1, sticky="ew")
        self.slider_value_label = ttk.Label(main_frame, text="15")
        self.slider_value_label.grid(column=1, row=1)

        ttk.Label(main_frame, text="Select speed multiplier:").grid(column=0, row=2, sticky="w")
        self.speed_slider = ttk.Scale(main_frame, from_=0.5, to=3, orient=HORIZONTAL, variable=self.speed_multiplier, length=300, command=self.update_speed_slider_value)
        self.speed_slider.grid(column=0, row=3, sticky="ew")
        self.speed_slider_value_label = ttk.Label(main_frame, text="1.0")
        self.speed_slider_value_label.grid(column=1, row=3)

        self.choose_files_button = ttk.Button(main_frame, text="Choose Video Files", command=self.choose_files)
        self.choose_files_button.grid(column=0, row=4, sticky="ew", pady=5)

        self.remove_file_button = ttk.Button(main_frame, text="Remove Selected Video", command=self.remove_file)
        self.remove_file_button.grid(column=0, row=5, sticky="ew", pady=5)

        self.choose_output_folder_button = ttk.Button(main_frame, text="Choose Output Folder", command=self.choose_output_folder)
        self.choose_output_folder_button.grid(column=0, row=6, sticky="ew", pady=5)

        self.chop_button = ttk.Button(main_frame, text="Chop Videos", command=self.start_chopping, state='disabled')
        self.chop_button.grid(column=0, row=7, sticky="ew", pady=5)

        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(column=0, row=8, sticky="ew", pady=5)

        self.log_text = Text(main_frame, height=20, width=80, wrap="word", font=("Arial", 10))
        self.log_text.grid(column=0, row=9, sticky="nsew", pady=10)

        self.total_duration_var = StringVar(value="Total Duration: 0 seconds")
        self.total_duration_label = ttk.Label(main_frame, textvariable=self.total_duration_var)
        self.total_duration_label.grid(column=0, row=10, sticky="w", pady=5)

        self.total_clips_var = StringVar(value="Estimated Total Clips: 0")
        self.total_clips_label = ttk.Label(main_frame, textvariable=self.total_clips_var)
        self.total_clips_label.grid(column=0, row=11, sticky="w", pady=5)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(9, weight=1)

        self.video_paths = []
        self.video_durations = {}
        self.output_folder = ""
        self.log = ""
        self.processed_videos = 0
        self.total_videos = 0
        self.current_video = 0
        self.total_duration = 0
        self.total_clips = 0

    def update_slider_value(self, value):
        self.slider_value_label.config(text=str(int(float(value))))
        self.update_total_clips()

    def update_speed_slider_value(self, value):
        self.speed_slider_value_label.config(text=f"{self.speed_multiplier.get():.1f}")
        self.update_total_duration()
        self.update_total_clips()

    def choose_files(self):
        new_video_paths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
        if new_video_paths:
            for path in new_video_paths:
                if path not in self.video_paths:
                    self.video_paths.append(path)
                    self.get_video_duration(path)
            if self.output_folder:
                self.chop_button.config(state='normal')
            self.log_message(f"Selected {len(new_video_paths)} new video(s). Total selected: {len(self.video_paths)} video(s)")
            self.update_total_duration()
            self.update_total_clips()

    def get_video_duration(self, video_path):
        try:
            with VideoFileClip(video_path) as video:
                duration = video.duration
                self.video_durations[video_path] = duration
                self.log_message(f"Video: {os.path.basename(video_path)}, Duration: {duration:.2f} seconds")
        except Exception as e:
            self.log_message(f"Error getting duration for {os.path.basename(video_path)}: {e}")

    def update_total_duration(self):
        speed_multiplier = self.speed_multiplier.get()
        self.total_duration = sum(duration / speed_multiplier for duration in self.video_durations.values())
        hours, remainder = divmod(self.total_duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.total_duration_var.set(f"Total Duration: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        self.log_message(f"Estimated total video length (after speed adjustment): {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")

    def update_total_clips(self):
        segment_length = self.segment_length.get()
        speed_multiplier = self.speed_multiplier.get()
        self.total_clips = sum(math.ceil((duration / speed_multiplier) / segment_length) for duration in self.video_durations.values())
        self.total_clips_var.set(f"Estimated Total Clips: {self.total_clips}")
        self.log_message(f"Estimated total clips: {self.total_clips}")

    def remove_file(self):
        selected_indices = self.log_text.tag_ranges("sel")
        if selected_indices:
            selected_text = self.log_text.get(selected_indices[0], selected_indices[1])
            for path in self.video_paths:
                if os.path.basename(path) in selected_text:
                    self.video_paths.remove(path)
                    duration = self.video_durations.pop(path, 0)
                    self.log_message(f"Removed video: {os.path.basename(path)}")
                    self.update_total_duration()
                    self.update_total_clips()
                    break
        else:
            self.log_message("No video selected for removal")

    def choose_output_folder(self):
        self.output_folder = filedialog.askdirectory()
        if self.video_paths and self.output_folder:
            self.chop_button.config(state='normal')
        self.log_message(f"Output folder: {self.output_folder}")

    def log_message(self, message):
        self.log += message + "\n"
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)

    def start_chopping(self):
        self.chop_button.config(state='disabled')
        self.processed_videos = 0
        self.total_videos = len(self.video_paths)
        self.progress_bar['value'] = 0
        self.log_message(f"Starting to process {self.total_videos} video(s)")

        threading.Thread(target=self.process_videos, daemon=True).start()

    def process_videos(self):
        for i, video_path in enumerate(self.video_paths, 1):
            self.current_video = i
            self.process_video(video_path)
            self.processed_videos += 1
            progress = (self.processed_videos / self.total_videos) * 100
            self.master.after(100, self.update_progress, progress)

        self.master.after(100, self.finalize_progress)

    def process_video(self, video_path):
        segment_length = self.segment_length.get()
        speed_multiplier = self.speed_multiplier.get()

        try:
            with VideoFileClip(video_path) as video:
                original_duration = video.duration
                video = video.fx(vfx.speedx, speed_multiplier)
                adjusted_duration = video.duration
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                expected_segments = math.ceil(adjusted_duration / segment_length)

                self.log_message(f"Processing video: {base_name}")
                self.log_message(f"Original duration: {original_duration:.2f} seconds")
                self.log_message(f"Adjusted duration: {adjusted_duration:.2f} seconds")

                if adjusted_duration <= segment_length:
                    output_path = os.path.join(self.output_folder, f"{base_name}_speedx{speed_multiplier:.1f}{os.path.splitext(video_path)[1]}")
                    video.write_videofile(output_path, codec="libx264")
                    self.log_message(f"Created single sped-up video for {self.current_video}/{self.total_videos}")
                else:
                    for part_number in range(1, expected_segments + 1):
                        start = (part_number - 1) * segment_length
                        end = min(start + segment_length, adjusted_duration)
                        segment = video.subclip(start, end)
                        output_path = os.path.join(self.output_folder, f"{base_name}_speedx{speed_multiplier:.1f}_part{part_number}{os.path.splitext(video_path)[1]}")
                        segment.write_videofile(output_path, codec="libx264")
                        self.log_message(f"Created segment {part_number}/{expected_segments} for video {self.current_video}/{self.total_videos}")

        except Exception as e:
            self.log_message(f"Error processing video {self.current_video}/{self.total_videos}: {e}")

    def update_progress(self, progress):
        self.progress_bar['value'] = progress

    def finalize_progress(self):
        self.progress_bar['value'] = 100
        self.log_message("Video chopping process completed.")
        self.chop_button.config(state='normal')

if __name__ == "__main__":
    root = Tk()
    video_chopper = VideoChopper(root)
    root.mainloop()