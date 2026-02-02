import random
import string
from helpers import Settings, get_settings
import os
class BaseController():
    
    def __init__(self):

        self.app_settings:Settings = get_settings()

        # __file__: is a python built in variable give the current file executed full path
        self.src_dir_path = os.path.dirname(os.path.dirname(__file__))
        self.files_dir_path = os.path.join(
            self.src_dir_path,
            "assets",
            "files"
        )

        self.database_dir_path = os.path.join(
            self.src_dir_path,
            "assets",
            "database"
        )

    def get_database_path(self, db_name: str):
        # to prevent classic concurrency bug known as a Race Condition,
        # specifically a "Time-of-Check to Time-of-Use" (TOCTOU) issue.
        os.makedirs(self.database_dir_path, exist_ok=True)

        database_path = os.path.join(
            self.database_dir_path,
            db_name
        )

        os.makedirs(database_path, exist_ok=True)

        return database_path
        
    def generate_random_string(self, length: int=12):
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
