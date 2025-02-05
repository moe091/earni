"""
A very simple logger class to make logging easier and more consistent for my scrapers. Will mostly be used to track errors when scraping
data so I can go back and fix or manually inspect them later. Logs should be easily searchable or parseable via scripts. Will
probably add features onto this as I go, if needed, and I'll probably end up using it for more than just scrapers
"""


class Logger:

    def __init__(self, name):
        self.name = name
        self.cur = "Default"

    def debug(self, message):
        with open(f"./log.{self.name}", "a") as file:
            file.write(f"[DEBUG][{self.cur}] :: {message}\n")

    def log(self, message):
        with open(f"./log.{self.name}", "a") as file:
            file.write(f"[LOG][{self.cur}] :: {message}\n")

    def warn(self, message):
        with open(f"./log.{self.name}", "a") as file:
            file.write(f"[WARN][{self.cur}] :: {message}\n")

    def error(self, message, e = None):
        with open(f"./log.{self.name}", "a") as file:
            file.write(f"[ERROR][{self.cur}] :: {message}\n")
            if e is not None:
                file.write(f"[EXCEPTION][{self.cur}] :: {e}\n")
