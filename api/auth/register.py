import uuid

import misc
from classes.user import User, UserStatus, get_user_from_username, Device, DeviceStatus

spec_paths = {
    "v1.0": {
        "/auth/register": {
            "post": {
                "summary": "Register user and return JWT token",
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


def post_v1dot0(username: str, password: str):
    user = get_user_from_username(username, raise_error=False)
    if user is not None:
        return {
            "error": {
                "name": "user_already_exists",
                "description": "User with specified username is already present in our database. Can't register with this username."
            }
        }, 400

    user = User()
    user.user_id = str(uuid.uuid4())
    user.status = UserStatus.ACTIVE
    user.username = username
    user.password = password
    user.save(new=True)

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