import multiprocessing
import queue
import sqlite3
import threading
import uuid
from multiprocessing import Queue
from sqlite3 import Connection, Cursor

from mpsqlite.accursor import MPSQLiteAlreadyCreatedCursorWrapper, MPSQLiteAlreadyCreatedCursorResponse, \
    MPSQLiteAlreadyCreatedCursorRequest
from mpsqlite.cursor import MPSQLiteCursorRequest, MPSQLiteCursorResponse, MPSQLiteCursorWrapper


class MPSQLiteConnectionRequest:
    def __init__(self, request_id, name, args, kwargs):
        self.request_id = request_id
        self.name = name
        self.args = args
        self.kwargs = kwargs

class MPSQLiteConnectionResponse:
    def __init__(self, request_id, result):
        self.request_id = request_id
        self.result = result

class MPSQLiteConnectionAttributesProxy:
    def __init__(self, name, connection_request_queue, connection_response_queue):
        self.__name = name
        self.__connection_request_queue: Queue = connection_request_queue
        self.__connection_response_queue: Queue = connection_response_queue

    def __call__(self, *args, **kwargs):
        request_id = str(uuid.uuid4())
        self.__connection_request_queue.put(MPSQLiteConnectionRequest(request_id, self.__name, args, kwargs))
        while True:
            try:
                response: MPSQLiteConnectionResponse = self.__connection_response_queue.get()

                if response.request_id != request_id:
                    self.__connection_response_queue.put(response)
                    continue

                if issubclass(type(response.result), Exception):
                    raise response.result

                return response.result
            except:
                return None

class MPSQLiteConnectionWrapper:
    def __init__(self, args, kwargs):
        self.__args = args
        self.__kwargs = kwargs

        self.__connection_request_queue: Queue = multiprocessing.Manager().Queue()
        self.__connection_response_queue: Queue = multiprocessing.Manager().Queue()

        self.__cursor_request_queue: Queue = multiprocessing.Manager().Queue()
        self.__cursor_response_queue: Queue = multiprocessing.Manager().Queue()

        self.__already_created_cursor_request_queue: Queue = multiprocessing.Manager().Queue()
        self.__already_created_cursor_response_queue: Queue = multiprocessing.Manager().Queue()

        t = threading.Thread(target=self.__connection_thread)
        t.daemon = True
        t.start()
        self.__thread = t

    def __connection_thread(self):
        connection: Connection = sqlite3.connect(*self.__args, **self.__kwargs)
        cursor_dict = {}
        while True:
            try:
                connection_request: MPSQLiteConnectionRequest | None = self.__connection_request_queue.get(block=False)
            except queue.Empty:
                connection_request = None

            if connection_request is not None:
                try:
                    connection_result = getattr(connection, connection_request.name)(*connection_request.args, **connection_request.kwargs)
                    self.__connection_response_queue.put(MPSQLiteConnectionResponse(connection_request.request_id, connection_result))
                except Exception as e:
                    self.__connection_response_queue.put(MPSQLiteConnectionResponse(connection_request.request_id, e))

            try:
                cursor_request: MPSQLiteCursorRequest | None = self.__cursor_request_queue.get(block=False)
            except queue.Empty:
                cursor_request = None

            if cursor_request is not None:
                try:
                    if cursor_request.cursor_id not in cursor_dict.keys():
                        cursor_dict[cursor_request.cursor_id] = connection.cursor(*cursor_request.cursor_args, **cursor_request.cursor_kwargs)

                    if cursor_request.type_of_request == "attr_exists":
                        cursor_result = getattr(cursor_dict[cursor_request.cursor_id], cursor_request.name)
                        self.__cursor_response_queue.put(
                            MPSQLiteCursorResponse(cursor_request.request_id, "not_none" if cursor_result is not None else None))
                    elif cursor_request.type_of_request == "attr":
                        cursor_result = getattr(cursor_dict[cursor_request.cursor_id], cursor_request.name)
                        self.__cursor_response_queue.put(
                            MPSQLiteCursorResponse(cursor_request.request_id, cursor_result))
                    elif cursor_request.type_of_request == "call":
                        cursor_result = getattr(cursor_dict[cursor_request.cursor_id], cursor_request.name)(*cursor_request.args, **cursor_request.kwargs)

                        if cursor_request.name == "close":
                            del cursor_dict[cursor_request.cursor_id]

                        if type(cursor_result) is Cursor:
                            # TODO: adding to cursor_dict only when cursor differs from original cursor
                            # now we dont add at all
                            #cursor_dict[id(cursor_request)] = cursor_result
                            self.__cursor_response_queue.put(MPSQLiteCursorResponse(cursor_request.request_id,
                                                                                    MPSQLiteAlreadyCreatedCursorWrapper(
                                                                                        id(cursor_result),
                                                                                        self.__already_created_cursor_request_queue,
                                                                                        self.__already_created_cursor_response_queue)))
                        else:
                            self.__cursor_response_queue.put(
                                MPSQLiteCursorResponse(cursor_request.request_id, cursor_result))
                    elif cursor_request.type_of_request == "iter":
                        cursor_result = getattr(cursor_dict[cursor_request.cursor_id], cursor_request.name).__iter__()
                        self.__cursor_response_queue.put(
                            MPSQLiteCursorResponse(cursor_request.request_id, cursor_result))
                    elif cursor_request.type_of_request == "len":
                        cursor_result = len(getattr(cursor_dict[cursor_request.cursor_id], cursor_request.name))
                        self.__cursor_response_queue.put(
                            MPSQLiteCursorResponse(cursor_request.request_id, cursor_result))
                    elif cursor_request.type_of_request == "item":
                        cursor_result = getattr(cursor_dict[cursor_request.cursor_id], cursor_request.name)[cursor_request.kwargs["item"]]
                        self.__cursor_response_queue.put(
                            MPSQLiteCursorResponse(cursor_request.request_id, cursor_result))
                except Exception as e:
                    self.__cursor_response_queue.put(MPSQLiteCursorResponse(cursor_request.request_id, e))
                # TODO: delete closed cursors there and not while calling "close" in wrappers

            # TODO: i dont believe SQLAlchemy uses cursors which are created after executing command on cursor. so there is not a lot of work I did there.
            # block of code below should be as equal as possible to the MPSQLiteCursorRequest handling above.
            # below, cursors that derived from cursors (= AlreadyCreatedCursors from the face of the dialect) lack type_of_request and adding to cursor_dict
            try:
                already_created_cursor_request: MPSQLiteAlreadyCreatedCursorRequest | None = self.__already_created_cursor_request_queue.get(
                    block=False)
            except queue.Empty:
                already_created_cursor_request = None
            if already_created_cursor_request is not None:
                try:
                    already_created_cursor_result = cursor_dict[already_created_cursor_request.cursor_id](*already_created_cursor_request.args, **already_created_cursor_request.kwargs)

                    if type(already_created_cursor_result) is Cursor:
                        # TODO: adding to cursor_dict only when cursor differs from original cursor
                        # now we dont add at all
                        #cursor_dict[id(already_created_cursor_result)] = already_created_cursor_result
                        self.__already_created_cursor_response_queue.put(MPSQLiteAlreadyCreatedCursorResponse(already_created_cursor_request.request_id, MPSQLiteAlreadyCreatedCursorWrapper(id(already_created_cursor_result), self.__already_created_cursor_request_queue, self.__already_created_cursor_response_queue)))
                    else:
                        self.__already_created_cursor_response_queue.put(MPSQLiteAlreadyCreatedCursorResponse(already_created_cursor_request.request_id, already_created_cursor_result))
                except Exception as e:
                    self.__already_created_cursor_response_queue.put(MPSQLiteAlreadyCreatedCursorResponse(already_created_cursor_request.request_id, e))

    def cursor(self, *args, **kwargs):
        return MPSQLiteCursorWrapper(self.__cursor_request_queue, self.__cursor_response_queue, args, kwargs)

    def __getattr__(self, name):
        resp = MPSQLiteConnectionAttributesProxy(name, self.__connection_request_queue, self.__connection_response_queue)
        return resp