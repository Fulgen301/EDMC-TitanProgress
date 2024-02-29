# MIT License

# Copyright (c) 2024 George Tokmaji

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import tkinter as tk
from typing import Tuple
from config import config
from theme import theme
import threading
import requests
import json
import os.path

from EDMCLogging import get_main_logger

frame: tk.Frame = None
session: requests.Session = None
worker_thread: threading.Thread = None
worker_event: threading.Event = None

titan_data = {}
titan_widgets = {}

plugin_name = os.path.basename(os.path.dirname(__file__))
logger = get_main_logger()


def titan_data_changed(event: tk.Event) -> None:
    """
    Handle the <<TitanDataChanged>> event
    """

    try:

        if not titan_widgets:
            logger.trace("Creating widgets for Titan data")
            for i, titan in enumerate(titan_data):
                label = tk.Label(frame, text=titan["name"]).grid(
                    row=i+1, column=0, sticky=tk.W)
                heart_progress_var = tk.StringVar(frame)
                heart_progress = tk.Label(frame, textvariable=heart_progress_var).grid(
                    row=i+1, column=1, sticky=tk.E)

                total_progress_var = tk.StringVar(frame)
                total_progress = tk.Label(frame, textvariable=total_progress_var).grid(
                    row=i+1, column=2, sticky=tk.E)

                titan_widgets[titan["name"]] = (
                    heart_progress_var, total_progress_var)

        for titan in titan_data:
            heart_progress_var, total_progress_var = titan_widgets[titan["name"]]
            heart_progress_var.set(
                f"{titan['heartProgress']:.4%} (+{titan['heartsRemaining'] - 1})")
            total_progress_var.set(
                f"{titan['totalProgress']:.2%}")

    except Exception as e:
        logger.exception("Failed to update Titan data")

    theme.update(frame)


def titan_worker_thread(quit_event: threading.Event):
    while True:
        if config.shutting_down:
            break

        logger.trace("Checking for Titan data")

        try:
            r = session.get(
                "https://dcoh.watch/api/v1/Overwatch/Titans")

            if r:
                global titan_data
                titan_data = r.json()["maelstroms"]
                titan_data.sort(key=lambda x: x["ingameNumber"])
                frame.event_generate("<<TitanDataChanged>>",
                                     when="tail")

        except Exception as e:
            logger.exception(f"Failed to get Titan data")

        if quit_event.wait(150):
            break


def plugin_app(parent: tk.Frame) -> Tuple[tk.Label, tk.Label]:
    """
    Create a pair of TK widgets for the EDMarketConnector main window
    """
    global session
    session = requests.Session()

    global frame
    frame = tk.Frame(parent)
    frame.grid()
    tk.Label(frame, text="Titan").grid(
        row=0, column=0)
    tk.Label(frame, text="\u2661").grid(
        row=0, column=1)
    tk.Label(frame, text="Total Progress").grid(
        row=0, column=2)
    theme.update(frame)
    frame.bind("<<TitanDataChanged>>", titan_data_changed)

    global worker_thread, worker_event
    worker_event = threading.Event()
    worker_thread = threading.Thread(target=titan_worker_thread, args=[
                                     worker_event], daemon=True)
    worker_thread.start()
    return frame


def plugin_start3(plugin_dir: str) -> str:
    """
    Load this plugin into EDMarketConnector
    """
    return plugin_name


def plugin_stop() -> None:
    """
    Unload this plugin from EDMarketConnector
    """
    if worker_event:
        worker_event.set()
        worker_thread.join()
