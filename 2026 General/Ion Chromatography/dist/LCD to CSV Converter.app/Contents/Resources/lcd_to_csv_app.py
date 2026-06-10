#%%
"""
Shimadzu .lcd -> CSV Converter — simple desktop GUI

Pick an input folder (containing .lcd files), pick an output folder,
and click Convert. Uses the conversion logic from lcd_to_csv.py.

Requirements:
    pip install olefile pandas

Run:
    python lcd_to_csv_app.py
"""

import platform
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from lcd_to_csv import convert_lcd


class LcdConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shimadzu LCD → CSV Converter")
        self.geometry("560x420")
        self.resizable(False, False)

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()

        pad = {"padx": 12, "pady": 6}

        # --- Input folder ---
        frame_in = ttk.Frame(self)
        frame_in.pack(fill="x", **pad)
        ttk.Label(frame_in, text="LCD folder:", width=14).pack(side="left")
        ttk.Entry(frame_in, textvariable=self.input_dir).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(frame_in, text="Browse…", command=self.choose_input).pack(side="left")

        # --- Output folder ---
        frame_out = ttk.Frame(self)
        frame_out.pack(fill="x", **pad)
        ttk.Label(frame_out, text="Save CSVs to:", width=14).pack(side="left")
        ttk.Entry(frame_out, textvariable=self.output_dir).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(frame_out, text="Browse…", command=self.choose_output).pack(side="left")

        # --- Convert button + progress ---
        frame_btn = ttk.Frame(self)
        frame_btn.pack(fill="x", **pad)
        self.convert_btn = ttk.Button(frame_btn, text="Convert", command=self.start_conversion)
        self.convert_btn.pack(side="left")
        self.progress = ttk.Progressbar(frame_btn, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self.open_folder_btn = ttk.Button(
            frame_btn, text="Open output folder", command=self.open_output_folder, state="disabled"
        )
        self.open_folder_btn.pack(side="left", padx=(12, 0))

        # --- Log area ---
        frame_log = ttk.Frame(self)
        frame_log.pack(fill="both", expand=True, **pad)
        ttk.Label(frame_log, text="Log:").pack(anchor="w")

        log_container = ttk.Frame(frame_log)
        log_container.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_container, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(log_container, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ── folder pickers ──
    def choose_input(self):
        folder = filedialog.askdirectory(title="Select folder containing .lcd files")
        if folder:
            self.input_dir.set(folder)
            if not self.output_dir.get():
                self.output_dir.set(folder)

    def choose_output(self):
        folder = filedialog.askdirectory(title="Select folder to save CSVs")
        if folder:
            self.output_dir.set(folder)

    def open_output_folder(self):
        folder = self.output_dir.get().strip()
        if not folder or not Path(folder).is_dir():
            return
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", folder])
        elif system == "Windows":
            subprocess.run(["explorer", folder])
        else:
            subprocess.run(["xdg-open", folder])

    # ── logging helper ──
    def log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ── conversion ──
    def start_conversion(self):
        in_dir = self.input_dir.get().strip()
        out_dir = self.output_dir.get().strip()

        if not in_dir or not Path(in_dir).is_dir():
            messagebox.showerror("Error", "Please choose a valid LCD folder.")
            return
        if not out_dir:
            messagebox.showerror("Error", "Please choose an output folder.")
            return

        self.convert_btn.configure(state="disabled")
        self.open_folder_btn.configure(state="disabled")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        thread = threading.Thread(
            target=self._run_conversion, args=(Path(in_dir), Path(out_dir)), daemon=True
        )
        thread.start()

    def _run_conversion(self, in_dir: Path, out_dir: Path):
        lcd_files = sorted(in_dir.rglob("*.lcd"))

        if not lcd_files:
            self.after(0, self.log, "No .lcd files found.")
            self.after(0, self._conversion_done)
            return

        self.after(0, self.log, f"Found {len(lcd_files)} .lcd file(s)\n")
        self.after(0, lambda: self.progress.configure(maximum=len(lcd_files), value=0))

        total_csvs = 0
        for i, lcd in enumerate(lcd_files, start=1):
            rel = lcd.relative_to(in_dir)
            self.after(0, self.log, f"{rel}")
            try:
                written = convert_lcd(lcd, out_dir)
                for w in written:
                    self.after(0, self.log, f"  wrote {w.name}")
                total_csvs += len(written)
            except Exception as e:
                self.after(0, self.log, f"  ERROR: {e}")
            self.after(0, lambda v=i: self.progress.configure(value=v))

        self.after(0, self.log, f"\nDone — {total_csvs} CSV file(s) written to {out_dir}")
        self.after(0, self._conversion_done)

    def _conversion_done(self):
        self.convert_btn.configure(state="normal")
        self.open_folder_btn.configure(state="normal")
        messagebox.showinfo("Done", "Conversion complete.")


if __name__ == "__main__":
    app = LcdConverterApp()
    app.mainloop()
