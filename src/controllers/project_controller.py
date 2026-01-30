
import os
from .base_controller import BaseController
from fastapi import UploadFile
from enums import ResponseSignal

class ProjectController(BaseController):
    def __init__(self):
        super().__init__()


    def get_project_path(self, project_id:str):
        project_dir_path = os.path.join(
            self.files_dir_path,
            project_id
        )

        if not os.path.exists(self.files_dir_path):
            os.makedirs(self.files_dir_path)

        if not os.path.exists(project_dir_path):
            os.makedirs(project_dir_path)

        return project_dir_path


