"""
Batch converter: Shimadzu .lcd -> CSV (retention time vs intensity)

LCD files are Microsoft OLE compound documents. The chromatogram traces
live in streams named "LSS Raw Data" / "Chromatogram Ch<N>", encoded with
a delta-compression scheme. This script reads those streams directly with
`olefile` (no proprietary software required).

Usage:
    python lcd_to_csv.py <input_dir> [output_dir]

    input_dir:  folder containing .lcd files (searched recursively)
    output_dir: where to write CSVs (default: same folder as each .lcd file)

Requirements:
    pip install olefile pandas
"""

import sys
import struct
import argparse
from pathlib import Path

try:
    import olefile
except ImportError:
    sys.exit("Missing dependency. Run:  pip install olefile")

import numpy as np
import pandas as pd


def _decode_value(raw_bytes: bytes) -> int:
    """Decode a Shimadzu delta-encoded value. The leading nibble is a sign
    digit: even = positive, odd = two's-complement negative."""
    total_bits = 8 * len(raw_bytes)
    x = 0
    for b in raw_bytes:
        x = (x << 8) | b

    value_bits = total_bits - 4
    sign = (x >> value_bits) & 0xF
    value_mask = (1 << value_bits) - 1
    value = x & value_mask

    if sign % 2 == 1:
        return -((1 << value_bits) - value)
    return value


def _decode_chromatogram_stream(buf: bytes) -> tuple[np.ndarray, float]:
    """Decode a 'Chromatogram Ch<N>' stream into (intensities, interval_ms)."""
    pos = 24  # 24-byte header (see module docstring)
    n_lambda = struct.unpack_from("<H", buf, 8)[0]      # number of points
    interval_ms = struct.unpack_from("<i", buf, 4)[0]   # sampling interval (ms)

    signal = np.zeros(n_lambda)
    count = 0
    acc = 0

    while count < n_lambda - 1 and pos + 2 <= len(buf):
        n_bytes = struct.unpack_from("<H", buf, pos)[0]
        pos += 2
        end_pos = pos + n_bytes

        while pos < end_pos:
            cb = buf[pos]
            if cb == 0x82:
                pos += 1
                continue
            elif cb == 0x00:
                delta = 0
                pos += 1
            else:
                hex1 = cb >> 4
                if hex1 == 0:
                    delta = cb
                    pos += 1
                elif hex1 == 1:
                    delta = _decode_value(buf[pos:pos + 1])
                    pos += 1
                else:
                    extra = hex1 // 2
                    delta = _decode_value(buf[pos:pos + 1 + extra])
                    pos += 1 + extra

            acc += delta
            signal[count] = acc
            count += 1
            if count >= n_lambda - 1:
                break

        pos = end_pos
        pos += 2  # end-of-segment marker
        acc = 0

    return signal, interval_ms


def convert_lcd(lcd_path: Path, output_dir: Path | None) -> list[Path]:
    """Convert one .lcd file to one CSV per chromatogram channel."""
    out_dir = output_dir or lcd_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    with olefile.OleFileIO(str(lcd_path)) as ole:
        streams = ole.listdir()
        chrom_streams = sorted(
            s for s in streams
            if len(s) == 2 and s[0] == "LSS Raw Data" and s[1].startswith("Chromatogram Ch")
        )

        for stream in chrom_streams:
            buf = ole.openstream(stream).read()
            if len(buf) < 24:
                continue  # empty/unused channel

            signal, interval_ms = _decode_chromatogram_stream(buf)

            times = np.arange(len(signal)) * interval_ms / 60000.0  # ms -> min
            df = pd.DataFrame({"time_min": times, "intensity": signal})

            label = stream[1].replace(" ", "_")  # e.g. Chromatogram_Ch1
            out_path = out_dir / f"{lcd_path.stem}_{label}.csv"
            df.to_csv(out_path, index=False)
            written.append(out_path)

    return written


def main():
    
    
    parser = argparse.ArgumentParser(description="Batch Shimadzu .lcd -> CSV converter")
    parser.add_argument("input_dir", type=Path, help="Folder with .lcd files (recursive)")
    parser.add_argument("output_dir", type=Path, nargs="?", default=None,
                        help="Output folder for CSVs (default: alongside each .lcd)")
    args = parser.parse_args()

    lcd_files = sorted(args.input_dir.rglob("*.lcd"))
    if not lcd_files:
        sys.exit(f"No .lcd files found under {args.input_dir}")

    print(f"Found {len(lcd_files)} .lcd file(s)\n")
    total = 0
    for lcd in lcd_files:
        print(f"{lcd.relative_to(args.input_dir)}")
        try:
            written = convert_lcd(lcd, args.output_dir)
            for w in written:
                print(f"  wrote {w.name}")
            total += len(written)
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone — {total} CSV file(s) written.")


if __name__ == "__main__":
    main()
