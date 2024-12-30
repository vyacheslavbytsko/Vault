import json
import uuid
from pathlib import Path

import misc
from classes.user import get_device_from_token_info
from config import get_config

spec_paths = {
    "v1.0": {
        "/chain/{chain_name}/event": {
            "post": {
                "summary": "Add new event",
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
                    }
                ],
                "requestBody": {
                    "x-body-name": "event",
                    "description": "Event",
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Added new event",
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
        },
        "/chain/{chain_name}/event/{event_id}": {
            "get": {
                "summary": "Get event data",
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
                        "description": "Event ID",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Event info",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
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


def get_v1dot0(token_info: dict, chain_name: str, event_id: str):
    if not misc.check_chain_name(chain_name):
        return {
            "error": {
                "name": "malformed_chain_name",
                "description": "As a part of specification, chain name should be lowercase alpha string (only letters) with maximum length of 32."
            }
        }, 400

    if not misc.check_uuid(event_id):
        return {
            "error": {
                "name": "malformed_event_id",
                "description": "As a part of specification, Event ID should be UUID."
            }
        }, 400

    device = get_device_from_token_info(token_info)

    if not device.user.check_chain_exists(chain_name):
        return {
            "error": {
                "name": "chain_not_initialized",
                "description": "Chain with name specified is not initialized. Refer to POST /chain/{chain_name}."
            }
        }, 400

    Path(get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/" + event_id).mkdir(
        parents=True, exist_ok=True)
    if not Path(
            get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/" + event_id + "/" + "data.txt").is_file():
        return {
            "error": {
                "name": "not_found",
                "description": "No event with this id was found."
            }
        }, 400
    return {
        "response": {
            "event": json.loads(open(
                get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/" + event_id + "/" + "data.txt",
                "r").read())
        }
    }, 200


def post_v1dot0(token_info: dict, chain_name: str, event: dict):

    # TODO: handle request_id: when user sends event with request_id,
    #  which was already handled in the last 24 hours,
    #  return server-generated event_id and even ignore non-matching last event
    #  and contents of the event.

    if not misc.check_chain_name(chain_name):
        return {
            "error": {
                "name": "malformed_chain_name",
                "description": "As a part of specification, chain name should be lowercase alpha string (only letters) with maximum length of 32."
            }
        }, 400

    if event.get("request_id", None) is None:
        return {
            "error": {
                "name": "no_request_id",
                "description": "As a part of specification, the body of POST request must have 'request_id' parameter."
            }
        }, 400

    if not misc.check_uuid(event["request_id"]):
        return {
            "error": {
                "name": "malformed_request_id",
                "description": "As a part of specification, the 'request_id' parameter must be UUID."
            }
        }, 400

    if event.get("type", None) is None:
        return {
            "error": {
                "name": "no_event_type",
                "description": "As a part of specification, all events have to have a type."
            }
        }, 400

    if event.get("data", None) is None:
        return {
            "error": {
                "name": "no_event_data",
                "description": "As a part of specification, all events have to have 'data' key. It can be empty (no key-value pairs) (it's up to overlying application specification), but it still have to be present."
            }
        }, 400

    if event.get("v", None) is None:
        return {
            "error": {
                "name": "no_event_version",
                "description": "As a part of specification, all event have to have 'v' key, which stands for event version. This version is up to overlying application specification, but it still have to be present."
            }
        }, 400

    if not((type(event["v"]) is str) or (type(event["v"]) is int)):
        return {
            "error": {
                "name": "malformed_event_version",
                "description": "As a part of specification, version of event have to be string or integer."
            }
        }, 400

    device = get_device_from_token_info(token_info)

    if not device.user.check_chain_exists(chain_name):
        return {
            "error": {
                "name": "chain_not_initialized",
                "description": "Chain with name specified is not initialized. Refer to POST /chain/{chain_name}."
            }
        }, 400

    if device.user.get_last_event_id(chain_name) != event.get("parent", None):
        return {
            "error": {
                "name": "parent_mismatch",
                "description": "Event's parent event is not the last event of this chain."
            }
        }, 400

    if "files" in event.keys():
        if type(event["files"]) is not list:
            return {
                "error": {
                    "name": "malformed_files",
                    "description": "\"files\" parameter must be array of strings representing IDs of files."
                }
            }, 400

        if not all(isinstance(elem, str) for elem in event["files"]):
            return {
                "error": {
                    "name": "malformed_files",
                    "description": "\"files\" parameter must be array of strings representing IDs of files."
                }
            }, 400

        if not all(misc.check_uuid(file_id) for file_id in event["files"]):
            return {
                "error": {
                    "name": "malformed_files",
                    "description": "\"files\" parameter must be array of strings representing IDs of files."
                }
            }, 400

        if not all(
                Path(get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/.tempfiles/" + file_id).exists()
                for file_id in event["files"]):
            return {
                "error": {
                    "name": "nonexistent_temp_files",
                    "description": "Some IDs in \"files\" parameter are not present on the server."
                }
            }, 400

    temp_id = str(uuid.uuid4())
    misc.add_event_requests_queue.put(misc.AddEventRequest(temp_id, device.user.user_id, chain_name, event))
    while True:
        try:
            response: misc.AddEventResponse = misc.add_event_responses_queue.get()

            if response.temp_id != temp_id:
                misc.add_event_responses_queue.put(response)
                continue

            return {
                "response": {
                    "event_id": response.event_id
                }
            }, 200
        except:
            return {
                "error": {
                    "name": "server_error",
                    "description": "Server could not add event to the chain. Please retry."
                }
            }, 500
