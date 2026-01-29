from helpers import Settings, get_settings
class BaseController():
    
    def __init__(self):

        self.app_settings:Settings = get_settings()