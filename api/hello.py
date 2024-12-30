from typing import Optional

import misc

spec_paths = {
    "v1.0": {
        "/hello": {
            "get": {
                "summary": "Ping server and get information about it.",
                "parameters": [
                    {
                        "name": "error",
                        "description": "Error should be emitted. 0 for not raising, 1 for raising",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "integer"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Server sent a response containing info about it.",
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
    },
    "nonversioned": {
        "/hello": {
            "get": {
                "summary": "Ping server and get information about it.",
                "parameters": [
                    {
                        "name": "error",
                        "description": "Error should be emitted. 0 for not raising, 1 for raising",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "integer"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Server sent a response containing info about it.",
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



def search_v1dot0(error: Optional[int] = None):
    if error:
        return {
            "error": {
                "name": "bad_request",
                "description": "You sent bad request on purpose."
            }
        }, 400

    return {
        "response": {
            "hello": "Hi!",
            "api_version": misc.API_VERSIONS[0]
        }
    }, 200

def search_nonversioned(error: Optional[int] = None):
    return search_v1dot0(error)