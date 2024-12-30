import uuid
from pathlib import Path

import starlette.datastructures

import misc
from classes.user import get_device_from_token_info
from config import get_config

spec_paths = {
    "v1.0": {
        "/chain/{chain_name}/file": {
            "post": {
                "summary": "Add new file. This file will be stored temporarily (usually 24 hours, but this is dependent on server settings). To store this file permanently, you must send event which contains this file id in \"files\" key.",
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
                    #"x-body-name": "file",
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "file": {
                                        "type": "string",
                                        "format": "binary"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Added new file",
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
        #    "/chain/{chain_name}/file/{file_id}": {
        #        "get": {
        #            "summary": "Get temporarily stored file. To get the file of event, use /chain/{chain_name}/event/{event_id}/file/{file_id}.",
        #            "security": [
        #                {
        #                    "jwt": ["secret"]
        #                }
        #            ],
        #            "parameters": [
        #                {
        #                    "name": "chain_name",
        #                    "description": "Chain name",
        #                    "in": "path",
        #                    "required": True,
        #                    "schema": {
        #                        "type": "string"
        #                    }
        #                },
        #                {
        #                    "name": "file_id",
        #                    "description": "File ID",
        #                    "in": "path",
        #                    "required": True,
        #                    "schema": {
        #                        "type": "string"
        #                    }
        #                }
        #            ],
        #            "responses": {
        #                "200": {
        #                    "description": "File",
        #                    "content": {
        #                        "application/octet-stream": {
        #                            "schema": {
        #                                "type": "string",
        #                                "format": "binary"
        #                            }
        #                        }
        #                    }
        #                },
        #                "400": {
        #                    "description": "Bad request",
        #                    "content": {
        #                        "application/json": {
        #                            "schema": {
        #                                "type": "object"
        #                            }
        #                        }
        #                    }
        #                }
        #            }
        #        }
        #    }
    }
}


async def post_v1dot0(token_info, chain_name, file: starlette.datastructures.UploadFile):
    if not misc.check_chain_name(chain_name):
        return {
            "error": {
                "name": "malformed_chain_name",
                "description": "As a part of specification, chain name should be lowercase alpha string (only letters) with maximum length of 32."
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

    if not isinstance(file, starlette.datastructures.UploadFile):
        return {
            "error": {
                "name": "not_a_file",
                "description": "You're not sending a file."
            }
        }, 400

    file_id = str(uuid.uuid4())

    Path(
        get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/.tempfiles").mkdir(
        parents=True, exist_ok=True)
    with open(
            get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/.tempfiles/" + file_id,
            "wb") as buffer:
        while content := await file.read(1024):
            buffer.write(content)

    return {
        "response": {
            "file_id": file_id
        }
    }, 200
