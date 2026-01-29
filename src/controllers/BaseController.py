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


