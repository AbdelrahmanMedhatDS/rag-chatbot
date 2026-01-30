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

    def generate_random_string(self, length: int=12):
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
