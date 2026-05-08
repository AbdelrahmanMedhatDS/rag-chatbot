from enum import Enum

class AssetTypeEnum(Enum):

    FILE = "file" # the asset till now manily store the file_id in asset_name
    DATASET = "dataset" # dataset assets stored by path or dataset name
    