import multiprocessing
import threading
from pathlib import Path

from connexion import AsyncApp
from sqlalchemy import create_engine
from sqlalchemy.dialects import registry
from sqlalchemy.orm import sessionmaker

import misc
import security
from classes import user
from classes.user import get_user_from_user_id
from config import get_config
from misc import StandaloneApplication, API_VERSIONS

config = get_config()


def add_event_thread():
    while True:
        try:
            request: misc.AddEventRequest = misc.add_event_requests_queue.get()
            user = get_user_from_user_id(request.user_id)
            response = user.add_event(request.chain_name, request.event)
            queue_item_result = misc.AddEventResponse(request.temp_id, response)
            misc.add_event_responses_queue.put(queue_item_result)
        except:
            continue


if __name__ != "__main__":
    app = AsyncApp(__name__)
    for version in API_VERSIONS:
        app.add_api(f'openapis/openapi_{version}.yaml', base_path=f'/api/{version}',
                    resolver=misc.CustomRestyResolver(version))
    app.add_api(f'openapis/openapi_nonversioned.yaml', base_path=f'/api',
                resolver=misc.CustomRestyResolver("nonversioned"))

if __name__ == "__main__":
    misc.generate_versioned_openapis()

    Path(config.data_directory).mkdir(parents=True, exist_ok=True)

    security.generate_ssl_certs_if_needed()

    registry.register("sqlite.mpsqlite", "mpsqlite.main", "MPSQLiteDialect")
    __user_db_engine = create_engine(
        "sqlite+mpsqlite:///" + get_config().data_directory + "/db/users.db")

    user_db_session_maker = sessionmaker(__user_db_engine, expire_on_commit=False)  # TODO: remove expire_on_commit
    user.create_db_and_tables(__user_db_engine)
    with user_db_session_maker() as session:
        user.db = session

        misc.add_event_requests_queue = multiprocessing.Manager().Queue()
        misc.add_event_responses_queue = multiprocessing.Manager().Queue()

        t = threading.Thread(target=add_event_thread)
        t.daemon = True
        t.start()

        options = {
            "bind": [f'0.0.0.0:{config.port}'],
            "workers": (multiprocessing.cpu_count() * 2) + 1,
            "worker_class": "uvicorn.workers.UvicornWorker",
            "certfile": security.SSL_SERVER_CERT_PATH,
            "keyfile": security.SSL_SERVER_KEY_PATH
        }
        StandaloneApplication(f"{Path(__file__).stem}:app", options).run()
