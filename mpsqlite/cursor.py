import queue
import uuid
from multiprocessing import Queue


class MPSQLiteCursorRequest:
    def __init__(self, request_id, cursor_id, cursor_args, cursor_kwargs, type_of_request, name, args, kwargs):
        self.request_id = request_id
        self.cursor_id = cursor_id
        self.cursor_args = cursor_args
        self.cursor_kwargs = cursor_kwargs
        self.type_of_request = type_of_request
        self.name = name
        self.args = args
        self.kwargs = kwargs


class MPSQLiteCursorResponse:
    def __init__(self, request_id, result):
        self.request_id = request_id
        self.result = result


class MPSQLiteCursorAttributesProxy:
    def __init__(self, cursor_id, cursor_args, cursor_kwargs, name, cursor_request_queue, cursor_response_queue):
        self.__cursor_id = cursor_id
        self.__cursor_args = cursor_args
        self.__cursor_kwargs = cursor_kwargs
        self.__name = name
        self.__cursor_request_queue: Queue = cursor_request_queue
        self.__cursor_response_queue: Queue = cursor_response_queue

    def check_if_attr_exists(self):
        request_id = str(uuid.uuid4())
        self.__cursor_request_queue.put(
            MPSQLiteCursorRequest(request_id, self.__cursor_id, self.__cursor_args, self.__cursor_kwargs, "attr_exists",
                                  self.__name, None, None))
        while True:
            try:
                response: MPSQLiteCursorResponse = self.__cursor_response_queue.get()

                if response.request_id != request_id:
                    self.__cursor_response_queue.put(response)
                    continue
                if issubclass(type(response.result), Exception):
                    raise response.result

                return response.result
            except:
                return None

    def get_actual_attr(self):
        request_id = str(uuid.uuid4())
        self.__cursor_request_queue.put(
            MPSQLiteCursorRequest(request_id, self.__cursor_id, self.__cursor_args, self.__cursor_kwargs, "attr",
                                  self.__name, None, None))
        while True:
            try:
                response: MPSQLiteCursorResponse = self.__cursor_response_queue.get()

                if response.request_id != request_id:
                    self.__cursor_response_queue.put(response)
                    continue
                if issubclass(type(response.result), Exception):
                    raise response.result

                return response.result
            except:
                return None

    def __call__(self, *args, **kwargs):
        request_id = str(uuid.uuid4())
        self.__cursor_request_queue.put(
            MPSQLiteCursorRequest(request_id, self.__cursor_id, self.__cursor_args, self.__cursor_kwargs, "call",
                                  self.__name, args, kwargs))
        while True:
            try:
                response: MPSQLiteCursorResponse = self.__cursor_response_queue.get()

                if response.request_id != request_id:
                    self.__cursor_response_queue.put(response)
                    continue

                if issubclass(type(response.result), Exception):
                    raise response.result

                return response.result
            except:
                return None

    def __iter__(self):
        request_id = str(uuid.uuid4())
        self.__cursor_request_queue.put(
            MPSQLiteCursorRequest(request_id, self.__cursor_id, self.__cursor_args, self.__cursor_kwargs, "iter",
                                  self.__name, (), {}))
        while True:
            try:
                response: MPSQLiteCursorResponse = self.__cursor_response_queue.get()

                if response.request_id != request_id:
                    self.__cursor_response_queue.put(response)
                    continue

                if issubclass(type(response.result), Exception):
                    raise response.result

                return response.result
            except queue.Empty:
                return None

    def __len__(self):
        request_id = str(uuid.uuid4())
        self.__cursor_request_queue.put(
            MPSQLiteCursorRequest(request_id, self.__cursor_id, self.__cursor_args, self.__cursor_kwargs, "len",
                                  self.__name, (), {}))
        while True:
            try:
                response: MPSQLiteCursorResponse = self.__cursor_response_queue.get()

                if response.request_id != request_id:
                    self.__cursor_response_queue.put(response)
                    continue

                if issubclass(type(response.result), Exception):
                    raise response.result

                return response.result
            except queue.Empty:
                return None

    def __getitem__(self, item):
        request_id = str(uuid.uuid4())
        self.__cursor_request_queue.put(
            MPSQLiteCursorRequest(request_id, self.__cursor_id, self.__cursor_args, self.__cursor_kwargs, "item",
                                  self.__name, (), {"item": item}))
        while True:
            try:
                response: MPSQLiteCursorResponse = self.__cursor_response_queue.get()

                if response.request_id != request_id:
                    self.__cursor_response_queue.put(response)
                    continue

                if issubclass(type(response.result), Exception):
                    raise response.result

                return response.result
            except queue.Empty:
                return None


class MPSQLiteCursorWrapper:
    def __init__(self, cursor_request_queue, cursor_response_queue, args, kwargs):
        self.__args = args
        self.__kwargs = kwargs
        self.__cursor_request_queue = cursor_request_queue
        self.__cursor_response_queue = cursor_response_queue

    def close(self):
        return self.__getattr__("close")()

    def __getattr__(self, name):
        if name == "rowcount":
            return MPSQLiteCursorAttributesProxy(id(self), self.__args, self.__kwargs, name,
                                                 self.__cursor_request_queue,
                                                 self.__cursor_response_queue).get_actual_attr()

        proxy = MPSQLiteCursorAttributesProxy(id(self), self.__args, self.__kwargs, name, self.__cursor_request_queue,
                                              self.__cursor_response_queue)
        if proxy.check_if_attr_exists() is None:
            return None
        return proxy
