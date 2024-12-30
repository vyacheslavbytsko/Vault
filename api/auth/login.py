import uuid

import misc
from classes.user import get_user_from_username, Device, DeviceStatus

spec_paths = {
    "v1.0": {
        "/auth/login": {
            "get": {
                "summary": "Return JWT token",
                "parameters": [
                    {
                        "name": "username",
                        "description": "Username",
                        "in": "query",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    },
                    {
                        "name": "password",
                        "description": "User password",
                        "in": "query",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "JWT token",
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


def search_v1dot0(username: str, password: str):
    user = get_user_from_username(username, raise_error=False)
    if user is None:
        return {
            "error": {
                "name": "wrong_username_or_password",
                "description": "Could not find this user-password pair."
            }
        }, 400
    if user.password != password:
        return {
            "error": {
                "name": "wrong_username_or_password",
                "description": "Could not find this user-password pair."
            }
        }, 400

    device = Device()
    device.device_id = str(uuid.uuid4())
    device.status = DeviceStatus.LOGGED_IN
    device.data = {}
    device.created_at = misc.current_timestamp()
    device.updated_at = misc.current_timestamp()
    device.user = user
    device.save(new=True)

    return {
        "response": {
            "token": device.generate_token_and_update()
        }
    }, 200
