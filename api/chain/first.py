import misc
from classes.user import get_device_from_token_info

spec_paths = {
    "v1.0": {
        "/chain/{chain_name}/first": {
            "get": {
                "summary": "Get first event id of this chain",
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
                "responses": {
                    "200": {
                        "description": "Getting first event id success",
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


def search_v1dot0(token_info: dict, chain_name: str):
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

    first_event_id = device.user.get_first_event_id(chain_name)
    if first_event_id is None:
        return {
            "error": {
                "name": "no_events",
                "description": "This chain doesn't have any events."
            }
        }, 400
    return {
        "response": {
            "first": first_event_id
        }
    }, 200

# no post/put as there will be no force push