import json
import uuid
from pathlib import Path
from typing import Self, Set, Any

import jwt
import sqlalchemy
from sqlalchemy import select, Engine, ForeignKey, JSON
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship

import misc
from config import get_config
from security import get_jwt_settings

config = get_config()
jwt_settings = get_jwt_settings()
db: sqlalchemy.orm.session.Session

class UserStatus(misc.IntEnum):
    DELETED_UNSPECIFIED = -1
    ACTIVE = 0

class User(misc.Base):
    __tablename__ = "UsersV1"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[UserStatus] = mapped_column(misc.IntEnum(UserStatus))
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    devices: Mapped[Set["Device"]] = relationship(back_populates="user")

    def get_last_event_id(self, chain_name):
        folder_path = get_config().data_directory + "/userevents/v1/" + self.user_id + "/v1/" + chain_name
        last_event_path = folder_path+"/LAST"
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        if not Path(last_event_path).is_file():
            return None
        with open(last_event_path, "r") as f:  # TODO: synchronously read this file
            return f.read()

    def unsafe_set_last_event_id(self, chain_name, event_id):
        folder_path = get_config().data_directory + "/userevents/v1/" + self.user_id + "/v1/" + chain_name
        last_event_path = folder_path + "/LAST"
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        f = open(last_event_path, "w")
        f.write(event_id)
        f.flush()
        f.close()

    def add_event(self, chain_name: str, event: dict) -> str:
        event_id = self.unsafe_add_event(chain_name, event)
        self.unsafe_set_last_event_id(chain_name, event_id)
        return event_id

    def unsafe_add_event(self, chain_name: str, event: dict) -> str:
        chain_folder_path = get_config().data_directory + "/userevents/v1/" + self.user_id + "/v1/" + chain_name
        Path(chain_folder_path).mkdir(parents=True, exist_ok=True)

        event_id = str(uuid.uuid4())
        event_folder_path = chain_folder_path + "/" + event_id
        event_path = event_folder_path + "/" + "data.txt"
        while Path(
                event_path).is_file():
            event_id = str(uuid.uuid4())
            event_path = event_folder_path + "/" + "data.txt"

        Path(event_folder_path).mkdir(parents=True, exist_ok=True)

        if "files" in event.keys():
            for file_id in event["files"]:
                (Path(chain_folder_path + "/.tempfiles/" + file_id)
                 .rename(event_folder_path + "/" + file_id))

        open(event_path, "w").write(json.dumps(event))

        return event_id

    def check_chain_exists(self, chain_name):
        if not misc.check_chain_name(chain_name):
            return False

        chain_options_folder = Path(
            get_config().data_directory + "/userevents/v1/" + self.user_id + "/v1/" + chain_name)
        if not chain_options_folder.exists():
            return False

        chain_options_file = Path(
            get_config().data_directory + "/userevents/v1/" + self.user_id + "/v1/" + chain_name + "/INIT")
        if not chain_options_file.exists():
            return False

        return True

    def save(self, new: bool = False):
        try:
            if new:
                db.add(self)
            else:
                db.merge(self)
        except:
            db.rollback()
            raise
        else:
            db.commit()

    def __repr__(self) -> str:
        return f"User(user_id={self.user_id})"

    def __eq__(self, other: Self):
        return self.user_id == other.user_id

class DeviceStatus(misc.IntEnum):
    LOGGED_OUT_UNSPECIFIED = -1
    LOGGED_IN = 0

class Device(misc.Base):
    __tablename__ = "DevicesV1"

    device_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('UsersV1.user_id'))
    user: Mapped["User"] = relationship(back_populates="devices")
    status: Mapped[DeviceStatus] = mapped_column(misc.IntEnum(DeviceStatus))
    created_at: Mapped[int]
    updated_at: Mapped[int]
    data: Mapped[dict[str, Any]]

    def generate_token_and_update(self):
        timestamp = misc.current_timestamp()
        payload = {
            "iss": jwt_settings.jwt_issuer,
            "iat": timestamp,
            "exp": timestamp + jwt_settings.jwt_lifetime_seconds,
            "sub": self.user.user_id + "." + "access" + "." + self.device_id,
        }
        self.updated_at = timestamp
        self.save()
        return jwt.encode(payload, jwt_settings.jwt_secret, algorithm=jwt_settings.jwt_algorithm)

    def save(self, new: bool = False):
        try:
            if new:
                db.add(self)
            else:
                db.merge(self)
        except:
            db.rollback()
            raise
        else:
            db.commit()


def decode_token(token) -> dict:
    try:
        return jwt.decode(token,
                          jwt_settings.jwt_secret,
                          options={
                              "require_sub": True,
                              "require_iss": True,
                              "require_iat": True,
                              "require_exp": True
                          },
                          algorithms=[jwt_settings.jwt_algorithm],
                          issuer=jwt_settings.jwt_issuer)
    except:
        return {}

def get_device_from_token(token: str, accepted_statuses: list[UserStatus] = []) -> Device:
    return get_device_from_token_info(decode_token(token), accepted_statuses)

def get_device_from_token_info(token_info: dict, accepted_statuses: list[UserStatus] = []) -> Device:
    try:
        user_id, token_type, device_id = token_info["sub"].split(".")
        result = db.execute(select(Device).where(Device.device_id == device_id))
        device = result.scalars().one()
        if device.user.user_id != user_id:
            raise
        if device.updated_at != token_info["iat"]:
            raise
        return device
    except:
        raise

def get_user_from_user_id(user_id: str, accepted_statuses: list[UserStatus] = [], raise_error: bool = True) -> User | None:
    try:
        result = db.execute(select(User).where(User.user_id == user_id))
        return result.scalars().one()
    except NoResultFound:
        if raise_error:
            raise
        else:
            return None

def get_user_from_username(username: str, accepted_statuses: list[UserStatus] = [], raise_error: bool = True) -> User | None:
    try:
        result = db.execute(select(User).where(User.username == username))
        return result.scalars().one()
    except NoResultFound:
        if raise_error:
            raise
        else:
            return None

def create_db_and_tables(engine: Engine):
    misc.Base.metadata.create_all(engine)