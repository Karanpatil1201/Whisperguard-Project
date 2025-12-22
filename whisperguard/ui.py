"""Minimal UI scaffold using tkinter for status and simple controls."""

import tkinter as tk
from tkinter import ttk


class SimpleDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WhisperGuard - Status")
        self.status_var = tk.StringVar(value="SAFE")
        ttk.Label(self.root, text="Status:").grid(row=0, column=0, sticky="w")
        ttk.Label(self.root, textvariable=self.status_var).grid(row=0, column=1, sticky="w")

    def set_status(self, s):
        self.status_var.set(s)

    def run(self):
        self.root.mainloop()
