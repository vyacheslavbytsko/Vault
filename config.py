from argparse import ArgumentParser
from enum import Enum

import yaml


class RequiredEntryNotConfiguredException(Exception):
    def __init__(self, item_path):
        self.item_path = item_path

class _YamlConfig:
    """Just a helper class to make it easier to handle non-configured entries."""
    def __init__(self, yaml, prefix=""):
        self.yaml = yaml
        self.prefix = prefix

    def __getitem__(self, item):
        try:
            if type(self.yaml[item]) is dict:
                return _YamlConfig(self.yaml[item], self.prefix+"."+item)
            else:
                return self.yaml[item]
        except:
            raise RequiredEntryNotConfiguredException((self.prefix+"."+item)[1:])


class Config:
    class Authentication:
        class Types(Enum):
            builtin = "builtin"

        auth_type: Types

    data_directory: str
    port: int
    authentication: Authentication


__config_in_memory: Config = None


def get_config() -> Config:
    global __config_in_memory
    if __config_in_memory is not None:
        return __config_in_memory

    __parser = ArgumentParser()
    __parser.add_argument("-c", "--config", dest="config", metavar="FILE")
    __args = __parser.parse_args()

    __actual_version = __update_config()
    __av = __actual_version
    __yaml_config = _YamlConfig(yaml.safe_load(open(__args.config)))

    __temp_config = Config()
    __temp_config.data_directory = __yaml_config[__av]["dataDirectory"]
    try:
        __temp_config.port = __yaml_config[__av]["port"]
    except RequiredEntryNotConfiguredException:
        __temp_config.port = 8000
    #__temp_config.authentication = Config.Authentication()
    #__temp_config.authentication.auth_type = Config.Authentication.Types(__yaml_config[__av]["authentication"]["type"])

    __config_in_memory = __temp_config
    return __config_in_memory

def __update_config() -> str:
    # every time config parameters are updated and need to be rewritten, new version appears
    return "v1"
