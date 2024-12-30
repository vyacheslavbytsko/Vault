import importlib
import os
import re
import time
from multiprocessing import Queue
from pathlib import Path
from typing import Self, Any

import yaml
from connexion import RestyResolver
from gunicorn.app.wsgiapp import WSGIApplication
from sqlalchemy import TypeDecorator, Integer, JSON
from sqlalchemy.orm import declarative_base, DeclarativeBase


API_VERSIONS = ["v1.0"]

def current_timestamp() -> int:
    return int(time.time())


UUID_PATTERN = re.compile(r'^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$')


def check_uuid(uuid_str: str) -> bool:
    if len(uuid_str) != 36: return False
    return bool(UUID_PATTERN.match(uuid_str.lower()))

def check_chain_name(chain_name: str) -> bool:
    if not chain_name.islower(): return False
    if len(chain_name) > 32: return False
    if not chain_name.isalpha(): return False
    return True


class Base(DeclarativeBase):
    type_annotation_map = {
            dict[str, Any]: JSON
        }


class IntEnum(TypeDecorator):
    """
    Enables passing in a Python enum and storing the enum's *value* in the db.
    The default would have stored the enum's *name* (ie the string).

    https://gist.github.com/hasansezertasan/691a7ef67cc79ea669ff76d168503235
    """

    impl = Integer

    def __init__(self, enumtype, *args, **kwargs):
        super(IntEnum, self).__init__(*args, **kwargs)
        self._enumtype = enumtype

    def process_bind_param(self, value: Self, dialect):
        if isinstance(value, int):
            return value

        return value.value

    def process_result_value(self, value, dialect):
        return self._enumtype(value)

class StandaloneApplication(WSGIApplication):
    def __init__(self, app_uri, options=None):
        self.options = options or {}
        self.app_uri = app_uri
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.app_uri


add_event_requests_queue: Queue
add_event_responses_queue: Queue


class AddEventRequest:
    def __init__(self, temp_id: str, user_id: str, chain_name: str, event: dict):
        self.temp_id = temp_id
        self.user_id = user_id
        self.chain_name = chain_name
        self.event = event

class AddEventResponse:
    def __init__(self, temp_id: str, event_id: str):
        self.temp_id = temp_id
        self.event_id = event_id


ERROR_RESPONSE = {
        "error": {
            "name": "unknown_api_version",
            "description": "Specified API version is unknown to the server. "
                           "Maybe it is too old or very new, so you should "
                           "either update your application or ask "
                           "administrator to update the server."
        }
    }, 400, {"Content-Type": "application/json"}

def generate_versioned_openapis():
    api_versions_with_unversioned = API_VERSIONS.copy()
    api_versions_with_unversioned.append("nonversioned")
    versioned_spec_paths = {k: {} for k in api_versions_with_unversioned}

    for subdir, dirs, files in os.walk("api"):
        for file in files:
            if file.endswith(".py"):
                file_spec_paths = getattr(importlib.import_module(f"{subdir.replace("/", ".")}.{file[:-3]}"),
                                          "spec_paths")

                def get_spec_paths_for_this_version(version):
                    if version == "nonversioned":
                        return file_spec_paths.get("nonversioned", {})
                    for existing_version in API_VERSIONS[API_VERSIONS.index(version):]:
                        try:
                            return file_spec_paths[existing_version]
                        except:
                            pass
                    return {}

                for version in api_versions_with_unversioned:
                    spec_paths_for_this_version = get_spec_paths_for_this_version(version)
                    for k, v in spec_paths_for_this_version.items():
                        versioned_spec_paths[version][f"{k}"] = v

    Path("openapis").mkdir(parents=True, exist_ok=True)

    for version in api_versions_with_unversioned:
        with open(f'openapis/openapi_{version}.yaml', 'w+') as f:
            yaml.dump({
                "openapi": "3.0.0",
                "info": {
                    "title": "Beshence Vault API",
                    "version": version,
                    "description": "API for clients"
                },
                "components": {
                    "securitySchemes": {
                        "jwt": {
                            "type": "http",
                            "scheme": "bearer",
                            "bearerFormat": "JWT",
                            "x-bearerInfoFunc": "classes.user.decode_token"
                        }
                    }
                },
                "paths": versioned_spec_paths[version]
            }, f, allow_unicode=True)

class CustomRestyResolver(RestyResolver):
    def __init__(self, version: str, *, collection_endpoint_name: str = "search"):
        """
        :param collection_endpoint_name: Name of function to resolve collection endpoints to
        """
        super().__init__("api", collection_endpoint_name=collection_endpoint_name)
        self.version = version

    def resolve_operation_id(self, operation):
        """
        Resolves the operationId using REST semantics unless explicitly configured in the spec

        :type operation: connexion.operations.AbstractOperation
        """
        if operation.operation_id:
            return super().resolve_operation_id(operation)

        def get_versioned_function_name(version):
            if version == "nonversioned":
                return self.resolve_operation_id_using_rest_semantics(operation)+"_"+self.version.replace(".", "dot")
            for existing_version in API_VERSIONS[API_VERSIONS.index(version):]:
                modulename = ".".join(self.resolve_operation_id_using_rest_semantics(operation).split(".")[:-1])
                functionname = self.resolve_operation_id_using_rest_semantics(operation).split(".")[-1]

                module = importlib.import_module(modulename)
                if not hasattr(module, functionname+"_"+existing_version.replace(".", "dot")):
                    continue
                return self.resolve_operation_id_using_rest_semantics(operation)+"_"+existing_version.replace(".", "dot")
            return None

        return get_versioned_function_name(self.version)


