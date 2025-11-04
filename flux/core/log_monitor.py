import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import re

class LogMonitor(FileSystemEventHandler):
    def __init__(self, log_path, error_callback):
        self.log_path = log_path
        self.error_callback = error_callback
        self.observer = Observer()

    def on_modified(self, event):
        if event.src_path == self.log_path:
            self.process_log_file()

    def process_log_file(self):
        with open(self.log_path, 'r') as log_file:
            for line in log_file:
                if 'Traceback' in line or 'Error' in line:
                    error_details = self.extract_error_details(line)
                    if error_details:
                        self.error_callback(error_details)

    def extract_error_details(self, log_line):
        # Example regex to extract file, line, and error type
        error_regex = re.compile(r'File "(.*?)", line (\d+), in (.*?)\n(\w+): (.*)')
        match = error_regex.search(log_line)
        if match:
            return {
                'file': match.group(1),
                'line': int(match.group(2)),
                'function': match.group(3),
                'error_type': match.group(4),
                'error_message': match.group(5)
            }
        return None

    async def start(self):
        self.observer.schedule(self, self.log_path, recursive=False)
        self.observer.start()
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
