import json
from pathlib import Path

import misc
from classes.user import get_device_from_token_info
from config import get_config

spec_paths = {
    "v1.0": {
        "/chain/{chain_name}/event/{event_id}/file/{file_id}": {
            "get": {
                "summary": "Get event's file.",
                "security": [
                    {
                        "jwt": ["secret"]
                    }
                ],
                "parameters": [
                    {
                        "name": "chain_name",
                        "description": "Chain name",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    },
                    {
                        "name": "event_id",
                        "description": "Event name",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    },
                    {
                        "name": "file_id",
                        "description": "File ID",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "File",
                        "content": {
                            "application/octet-stream": {
                                "schema": {
                                    "type": "string",
                                    "format": "binary"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

def get_v1dot0(token_info, chain_name, event_id, file_id):
    if not misc.check_chain_name(chain_name):
        return {
            "error": {
                "name": "malformed_chain_name",
                "description": "As a part of specification, chain name should be lowercase alpha string (only letters) with maximum length of 32."
            }
        }, 400, {"Content-Type": "application/json"}

    if not misc.check_uuid(event_id):
        return {
            "error": {
                "name": "malformed_event_id",
                "description": "As a part of specification, Event ID should be UUID."
            }
        }, 400, {"Content-Type": "application/json"}

    if not misc.check_uuid(file_id):
        return {
            "error": {
                "name": "malformed_file_id",
                "description": "As a part of specification, File ID should be UUID."
            }
        }, 400, {"Content-Type": "application/json"}

    device = get_device_from_token_info(token_info)

    if not device.user.check_chain_exists(chain_name):
        return {
            "error": {
                "name": "chain_not_initialized",
                "description": "Chain with name specified is not initialized. Refer to POST /chain/{chain_name}."
            }
        }, 400, {"Content-Type": "application/json"}

    Path(
        get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/" + event_id).mkdir(
        parents=True, exist_ok=True)
    if not Path(
            get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/" + event_id + "/" + "data.txt").is_file():
        return {
            "error": {
                "name": "not_found",
                "description": "No event with this id was found."
            }
        }, 400, {"Content-Type": "application/json"}

    with open(get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/" + event_id + "/" + "data.txt") as f:
        event = json.loads(f.read())
        if "files" not in event.keys():
            return {
                "error": {
                    "name": "not_found",
                    "description": "No file with this id was found in this event."
                }
            }, 400, {"Content-Type": "application/json"}

        if file_id not in event["files"]:
            return {
                "error": {
                    "name": "not_found",
                    "description": "No file with this id was found in this event."
                }
            }, 400, {"Content-Type": "application/json"}

        return open(get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/" + event_id + "/" + file_id, "rb").read(), 200, {"Content-Type": "application/octet-stream"}
