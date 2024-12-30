from pathlib import Path

import misc
from classes.user import get_device_from_token_info
from config import get_config

spec_paths = {
    "v1.0": {
        "/chain/{chain_name}": {
            "post": {
                "summary": "Initialize new chain",
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
                    "x-body-name": "settings",
                    "description": "Settings of chain initialization",
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
                    "201": {
                        "description": "Created new chain",
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

def post_v1dot0(token_info, chain_name):
    if not misc.check_chain_name(chain_name):
        return {
            "error": {
                "name": "malformed_chain_name",
                "description": "As a part of specification, chain name should be lowercase alpha string (only letters) with maximum length of 32."
            }
        }, 400

    device = get_device_from_token_info(token_info)
    chain_options_folder = Path(get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name)
    chain_options_file = Path(get_config().data_directory + "/userevents/v1/" + device.user.user_id + "/v1/" + chain_name + "/INIT")

    if chain_options_file.exists():
        return {
            "error": {
                "name": "chain_already_initialized",
                "description": "Chain with name specified is already created."
            }
        }, 400

    chain_options_folder.mkdir(parents=True, exist_ok=True)

    with open(chain_options_file, "w") as f:
        f.write("{}")

    return {
        "response": {
            "chain_name": chain_name
        }
    }, 201

