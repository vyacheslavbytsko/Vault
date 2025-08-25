from starlette import status
from starlette.exceptions import HTTPException

HTTPUserAlreadyCreatedException = lambda: HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="User with this username already exists")

HTTPCredentialsException = lambda: HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"})