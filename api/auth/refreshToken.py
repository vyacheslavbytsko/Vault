from classes.user import get_device_from_token_info

spec_paths = {
    "v1.0": {
        "/auth/refreshToken": {
            "get": {
                "summary": "Get new JWT token for this device",
                "security": [
                    {
                        "jwt": ["secret"]
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Refreshing token success",
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


def search_v1dot0(token_info):
    device = get_device_from_token_info(token_info)
    return {
        "response": {
            "token": device.generate_token_and_update()
        }
    }, 200