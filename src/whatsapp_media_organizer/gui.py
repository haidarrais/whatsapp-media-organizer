"""Desktop GUI for the WhatsApp Media Organizer (built on tkinter)."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext

from .core import organize_whatsapp_media


class WhatsAppMediaOrganizerApp:
    """Tkinter wrapper around :func:`core.organize_whatsapp_media`."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("WhatsApp Media Organizer")
        self.root.geometry("650x500")
        self.root.resizable(False, False)

        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar(
            value=str(Path.home() / "Desktop" / "sorted_media")
        )

        self._build_ui()

    def _build_ui(self) -> None:
        # Source directory
        tk.Label(self.root, text="Source Directory (WhatsApp Download):", anchor="w").pack(
            fill="x", padx=12, pady=(12, 2)
        )
        src_frame = tk.Frame(self.root)
        src_frame.pack(fill="x", padx=12, pady=(0, 8))
        tk.Entry(src_frame, textvariable=self.source_dir).pack(
            side="left", fill="x", expand=True, ipady=2
        )
        tk.Button(src_frame, text="Browse...", command=self._browse_source).pack(
            side="right", padx=(6, 0)
        )

        # Destination directory
        tk.Label(self.root, text="Destination Directory:", anchor="w").pack(
            fill="x", padx=12, pady=(0, 2)
        )
        dest_frame = tk.Frame(self.root)
        dest_frame.pack(fill="x", padx=12, pady=(0, 10))
        tk.Entry(dest_frame, textvariable=self.dest_dir).pack(
            side="left", fill="x", expand=True, ipady=2
        )
        tk.Button(dest_frame, text="Browse...", command=self._browse_dest).pack(
            side="right", padx=(6, 0)
        )

        # Start button
        self.start_btn = tk.Button(
            self.root,
            text="Start Organizing",
            command=self._start,
            bg="#4CAF50",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        self.start_btn.pack(pady=(0, 10))

        # Log output
        tk.Label(self.root, text="Progress:", anchor="w").pack(fill="x", padx=12, pady=(0, 2))
        self.log_area = scrolledtext.ScrolledText(self.root, height=18, font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_area.config(state="disabled")

    def _browse_source(self) -> None:
        directory = filedialog.askdirectory(title="Select WhatsApp Download Folder")
        if directory:
            self.source_dir.set(directory)

    def _browse_dest(self) -> None:
        directory = filedialog.askdirectory(title="Select Destination Folder")
        if directory:
            self.dest_dir.set(directory)

    def _log(self, message: str) -> None:
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")
        self.root.update_idletasks()

    def _start(self) -> None:
        source = self.source_dir.get().strip()
        dest = self.dest_dir.get().strip()

        if not source:
            self._log("ERROR: Please select a source directory.")
            return
        if not os.path.isdir(source):
            self._log(f"ERROR: Source directory does not exist:\n{source}")
            return
        if not dest:
            self._log("ERROR: Please select a destination directory.")
            return

        self.start_btn.config(state="disabled")
        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")

        self._log("Starting organization...")
        thread = threading.Thread(target=self._run, args=(source, dest), daemon=True)
        thread.start()

    def _run(self, source: str, dest: str) -> None:
        try:
            organize_whatsapp_media(source, dest, self._log)
        except Exception as exc:  # pragma: no cover - tkinter error surface
            self._log(f"ERROR: {exc}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state="normal"))


def main() -> None:
    root = tk.Tk()
    app = WhatsAppMediaOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
