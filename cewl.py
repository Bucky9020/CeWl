#!/usr/bin/env python3
# CeWL By Bucky - Tkinter Dark Edition
# Behavior change: after crawling finishes the program prompts "Save As"
# with a default filename based on the target hostname and timestamp.
# All UI text is English.

import os
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
from urllib.parse import urljoin, urlparse
from datetime import datetime

# Basic crawler (recursing links up to max_depth)
def crawl_website(start_url, max_depth, min_word_length, stop_flag=None):
    visited = set()
    words = set()

    def crawl(url, depth):
        if stop_flag and stop_flag.is_set():
            return
        if depth < 0 or url in visited:
            return
        visited.add(url)
        try:
            resp = requests.get(url, timeout=6)
            # process only text/html responses
            ctype = resp.headers.get("Content-Type", "").lower()
            if resp.status_code != 200 or not ("text" in ctype or "html" in ctype):
                return
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=" ")
            for token in text.split():
                cleaned = "".join(ch for ch in token if ch.isalnum())
                if len(cleaned) >= min_word_length:
                    words.add(cleaned.lower())
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith("http://") or href.startswith("https://"):
                    crawl(href, depth - 1)
                else:
                    # try to join relative links
                    try:
                        next_url = urljoin(url, href)
                        if next_url.startswith("http://") or next_url.startswith("https://"):
                            crawl(next_url, depth - 1)
                    except:
                        pass
        except Exception:
            pass

    crawl(start_url, max_depth)
    return sorted(words)

def find_txt_files_under_home(max_files=500, max_depth=5):
    found = []
    home = os.path.expanduser("~")
    base_len = len(home)
    for root, dirs, files in os.walk(home):
        depth = root[base_len:].count(os.sep)
        if depth > max_depth:
            dirs[:] = []
            continue
        for f in files:
            if f.lower().endswith(".txt"):
                path = os.path.join(root, f)
                try:
                    size = os.path.getsize(path)
                except Exception:
                    size = 0
                # heuristic: ignore tiny files
                if size < 200:
                    continue
                found.append(path)
                if len(found) >= max_files:
                    return found
    return found

# GUI
class CeWLApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CeWL By Bucky")
        self.geometry("720x540")
        self.configure(bg="#121212")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.crawl_thread = None
        self.stop_flag = threading.Event()

        # Title label
        self.title_label = tk.Label(self, text="CeWL By Bucky", font=("Helvetica", 20, "bold"),
                                    fg="#e6e6e6", bg="#121212")
        self.title_label.pack(pady=(12, 6))

        # Input frame
        frm = tk.Frame(self, bg="#121212")
        frm.pack(fill="x", padx=12, pady=6)

        lbl_url = tk.Label(frm, text="Target URL:", fg="#e6e6e6", bg="#121212")
        lbl_url.grid(row=0, column=0, sticky="e", padx=(0,6))
        self.url_entry = tk.Entry(frm, width=52, bg="#1E1E1E", fg="#ffffff", insertbackground="#ffffff")
        self.url_entry.insert(0, "https://")
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="w", pady=4)

        lbl_depth = tk.Label(frm, text="Depth:", fg="#e6e6e6", bg="#121212")
        lbl_depth.grid(row=1, column=0, sticky="e", padx=(0,6))
        self.depth_entry = tk.Entry(frm, width=10, bg="#1E1E1E", fg="#ffffff", insertbackground="#ffffff")
        self.depth_entry.insert(0, "1")
        self.depth_entry.grid(row=1, column=1, sticky="w", pady=4)

        lbl_min = tk.Label(frm, text="Min word length:", fg="#e6e6e6", bg="#121212")
        lbl_min.grid(row=2, column=0, sticky="e", padx=(0,6))
        self.min_entry = tk.Entry(frm, width=10, bg="#1E1E1E", fg="#ffffff", insertbackground="#ffffff")
        self.min_entry.insert(0, "3")
        self.min_entry.grid(row=2, column=1, sticky="w", pady=4)

        lbl_output = tk.Label(frm, text="Output file (optional):", fg="#e6e6e6", bg="#121212")
        lbl_output.grid(row=3, column=0, sticky="e", padx=(0,6))
        self.output_var = tk.StringVar()
        self.output_entry = tk.Entry(frm, textvariable=self.output_var, width=52, bg="#1E1E1E", fg="#ffffff", insertbackground="#ffffff")
        self.output_entry.grid(row=3, column=1, columnspan=1, sticky="w", pady=4)
        btn_browse = tk.Button(frm, text="Browse", command=self.choose_output_file, bg="#2b2b2b", fg="#ffffff", relief="flat")
        btn_browse.grid(row=3, column=2, padx=(8,0))

        # Buttons
        btn_frame = tk.Frame(self, bg="#121212")
        btn_frame.pack(fill="x", padx=12, pady=(6,0))
        self.start_btn = tk.Button(btn_frame, text="Start Crawl", command=self.start_crawl, bg="#2b8b57", fg="#ffffff", relief="flat", padx=8, pady=6)
        self.start_btn.pack(side="left")
        self.stop_btn = tk.Button(btn_frame, text="Stop", command=self.stop_crawl, state="disabled", bg="#7a2b2b", fg="#ffffff", relief="flat", padx=8, pady=6)
        self.stop_btn.pack(side="left", padx=(8,0))

        # Log area
        self.log_box = scrolledtext.ScrolledText(self, width=90, height=18, bg="#0e0e0e", fg="#dcdcdc", insertbackground="#dcdcdc")
        self.log_box.pack(fill="both", expand=True, padx=12, pady=10)

        # Footer info
        footer = tk.Label(self, text="If output file is empty, the program will search your home directory for .txt files and list them.",
                          fg="#bdbdbd", bg="#121212", font=("Helvetica", 9))
        footer.pack(side="bottom", pady=(0,10))

    def choose_output_file(self):
        p = filedialog.asksaveasfilename(title="Choose output file", defaultextension=".txt",
                                         filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if p:
            self.output_var.set(p)

    def log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {text}\n")
        self.log_box.see("end")

    def start_crawl(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a target URL first.")
            return
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, url)

        try:
            depth = int(self.depth_entry.get().strip())
            min_len = int(self.min_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Depth and Min word length must be integers.")
            return

        outpath_prefilled = self.output_var.get().strip()
        preexisting = []
        if not outpath_prefilled:
            self.log("No output file chosen. Scanning home for .txt files...")
            found = find_txt_files_under_home()
            self.log(f"Found {len(found)} candidate .txt files under home.")
            for p in found[:20]:
                self.log(p)
            if found:
                preexisting = found
                self.log("Pre-existing wordlists will be merged into the final output if present.")
            else:
                self.log("No .txt files found under home.")
                # Not fatal — still allow crawl and then prompt save.
        else:
            # if user prefilled an output path, we'll use it automatically (no prompt)
            self.log(f"Output file preselected: {outpath_prefilled}")

        # start worker thread
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.stop_flag.clear()
        self.log(f"Starting crawl: {url} (depth={depth}, min_word_length={min_len})")

        def worker():
            try:
                words = crawl_website(url, depth, min_len, stop_flag=self.stop_flag)
                self.log(f"Crawl finished. Extracted {len(words)} unique words.")
                # merge preexisting lists if any
                if preexisting:
                    self.log("Merging words from existing .txt files...")
                    for p in preexisting:
                        try:
                            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                                for ln in fh:
                                    w = ln.strip()
                                    if w:
                                        words.append(w) if isinstance(words, list) else words.add(w)
                        except Exception as e:
                            self.log(f"Failed to read {p}: {e}")

                # ensure unique sorted list
                if isinstance(words, set):
                    out_list = sorted(words)
                else:
                    out_list = sorted(set(words))

                # If user already provided an output path, write directly.
                if outpath_prefilled:
                    try:
                        with open(outpath_prefilled, "w", encoding="utf-8") as outf:
                            for w in out_list:
                                outf.write(w + "\n")
                        self.log(f"Output written to: {outpath_prefilled} (total words: {len(out_list)})")
                    except Exception as e:
                        self.log(f"Failed to write output file: {e}")
                else:
                    # Prompt Save As on the main thread, with suggested filename based on hostname
                    # build suggested filename
                    try:
                        parsed = urlparse(url)
                        host = parsed.hostname or "site"
                        host_safe = host.replace(":", "_")
                    except Exception:
                        host_safe = "site"
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    suggested_name = f"wordlist_{host_safe}_{ts}.txt"
                    # call prompt in main thread
                    self.after(0, lambda: self.prompt_save_and_write(out_list, suggested_name))
            except Exception as e:
                self.log(f"Error during crawl: {e}")
            finally:
                self.after(0, self.on_crawl_finish)

        self.crawl_thread = threading.Thread(target=worker, daemon=True)
        self.crawl_thread.start()

    def prompt_save_and_write(self, out_list, suggested_name):
        # Ask user where to save final wordlist (default name based on tested host)
        p = filedialog.asksaveasfilename(title="Save wordlist as", defaultextension=".txt",
                                         initialfile=suggested_name,
                                         filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not p:
            self.log("Save cancelled. The wordlist was not saved.")
            return
        try:
            with open(p, "w", encoding="utf-8") as outf:
                for w in out_list:
                    outf.write(w + "\n")
            self.log(f"Output written to: {p} (total words: {len(out_list)})")
        except Exception as e:
            self.log(f"Failed to write output file: {e}")

    def stop_crawl(self):
        if messagebox.askyesno("Stop", "Stop the current crawl?"):
            self.stop_flag.set()
            self.log("Stop requested. The crawl will stop shortly if possible.")
            # Note: crawler checks stop_flag at page recursion entry; full immediate stop requires additional checks.

    def on_crawl_finish(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log("Crawler stopped or finished.")

    def on_close(self):
        if self.crawl_thread and self.crawl_thread.is_alive():
            if not messagebox.askyesno("Exit", "A crawl is still running. Exit anyway?"):
                return
        self.destroy()

if __name__ == "__main__":
    app = CeWLApp()
    app.mainloop()
