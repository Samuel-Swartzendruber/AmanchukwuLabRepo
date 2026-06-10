#%%
# ─────────────────────────────────────────────────────────────────────────────
# Shimadzu .lcd → CSV  |  Interactive Widget  (VS Code Interactive Window)
#
# Requirements:
#   pip install rainbow-api pandas ipywidgets matplotlib
#
# Run this cell (Shift+Enter) — a GUI panel will appear below.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import io
from pathlib import Path

try:
    import rainbow as rb
except ImportError:
    raise ImportError("Run:  pip install rainbow-api")

import pandas as pd
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display, clear_output

# ── helpers ──────────────────────────────────────────────────────────────────

def find_lcd_files(folder: Path) -> list[Path]:
    return sorted(folder.rglob("*.lcd"))

def convert_lcd(lcd_path: Path, output_dir: Path) -> list[tuple[Path, pd.DataFrame]]:
    """Return list of (csv_path, dataframe) for every channel in the file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    datafile = rb.read(str(lcd_path))
    results = []

    for detector in datafile.detectors:
        for channel in detector.channels:
            times = channel.times
            data  = channel.data
            df = pd.DataFrame({"time_min": times, "intensity": data})

            label    = (channel.name or "channel").replace("/", "-").replace(" ", "_")
            out_path = output_dir / f"{lcd_path.stem}_{label}.csv"
            df.to_csv(out_path, index=False)
            results.append((out_path, df))

    return results

# ── widget layout ─────────────────────────────────────────────────────────────

style   = {"description_width": "130px"}
layout  = widgets.Layout(width="480px")
btn_lay = widgets.Layout(width="160px", height="34px")

# ── input folder ──
w_input = widgets.Text(
    description="📂 LCD folder:",
    placeholder="Paste or type folder path…",
    style=style, layout=layout,
)

# ── output folder ──
w_output = widgets.Text(
    description="💾 Output folder:",
    placeholder="Leave blank → same as input",
    style=style, layout=layout,
)

# ── file list ──
w_filelist = widgets.SelectMultiple(
    description="LCD files:",
    options=[],
    rows=8,
    style=style,
    layout=widgets.Layout(width="480px"),
)

# ── buttons ──
btn_scan    = widgets.Button(description="🔍 Scan folder",  button_style="info",    layout=btn_lay)
btn_convert = widgets.Button(description="⚙ Convert",       button_style="success", layout=btn_lay)
btn_clear   = widgets.Button(description="✖ Clear log",     button_style="warning", layout=btn_lay)

# ── preview toggle ──
w_preview = widgets.Checkbox(value=True, description="Show chromatogram preview", indent=False)

# ── log output ──
out_log  = widgets.Output(layout=widgets.Layout(
    border="1px solid #ccc", min_height="80px", max_height="200px",
    overflow_y="auto", padding="6px", width="480px",
))
# ── plot output ──
out_plot = widgets.Output()

# ── state ──
_lcd_files: list[Path] = []

# ── callbacks ─────────────────────────────────────────────────────────────────

def on_scan(_):
    global _lcd_files
    folder = Path(w_input.value.strip())
    with out_log:
        if not folder.exists():
            print(f"❌  Folder not found: {folder}")
            return
        _lcd_files = find_lcd_files(folder)
        w_filelist.options = [str(p.relative_to(folder)) for p in _lcd_files]
        print(f"✅  Found {len(_lcd_files)} .lcd file(s) in {folder}")

def on_convert(_):
    if not _lcd_files:
        with out_log:
            print("⚠️  Scan a folder first.")
        return

    # Which files to convert — all if nothing selected, else selection
    selected_indices = list(w_filelist.index) or list(range(len(_lcd_files)))
    files_to_run = [_lcd_files[i] for i in selected_indices]

    in_folder  = Path(w_input.value.strip())
    raw_out    = w_output.value.strip()
    out_folder = Path(raw_out) if raw_out else in_folder

    all_results: list[tuple[Path, pd.DataFrame]] = []
    with out_log:
        for lcd in files_to_run:
            try:
                results = convert_lcd(lcd, out_folder)
                for csv_path, _ in results:
                    print(f"  ✅  {csv_path.name}")
                all_results.extend(results)
            except Exception as e:
                print(f"  ❌  {lcd.name}: {e}")
        print(f"\n🏁  Done — {len(all_results)} CSV(s) written to {out_folder}\n")

    if w_preview.value and all_results:
        _plot_previews(all_results)

def on_clear(_):
    out_log.clear_output()
    out_plot.clear_output()

def _plot_previews(results: list[tuple[Path, pd.DataFrame]]):
    with out_plot:
        clear_output(wait=True)
        n = len(results)
        cols = min(n, 3)
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 3 * rows), squeeze=False)
        axes_flat = [ax for row in axes for ax in row]

        for ax, (csv_path, df) in zip(axes_flat, results):
            ax.plot(df["time_min"], df["intensity"], lw=1, color="#2176ae")
            ax.set_title(csv_path.stem, fontsize=9, pad=4)
            ax.set_xlabel("Time (min)", fontsize=8)
            ax.set_ylabel("Intensity", fontsize=8)
            ax.tick_params(labelsize=7)

        # Hide unused axes
        for ax in axes_flat[n:]:
            ax.set_visible(False)

        fig.tight_layout()
        plt.show()

# ── wire up ──
btn_scan.on_click(on_scan)
btn_convert.on_click(on_convert)
btn_clear.on_click(on_clear)

# ── render ────────────────────────────────────────────────────────────────────

panel = widgets.VBox([
    widgets.HTML("<h3 style='margin:0 0 8px'>🧪 Shimadzu LCD → CSV Converter</h3>"),
    w_input,
    w_output,
    widgets.HBox([btn_scan, btn_convert, btn_clear]),
    w_filelist,
    w_preview,
    out_log,
    out_plot,
], layout=widgets.Layout(padding="12px", width="520px"))

display(panel)
