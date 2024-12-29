#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import datetime
import hashlib
import json
import logging
import re
import uuid
from argparse import ArgumentParser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

# from scoring import get_score, get_interests
import scoring
from scoring.scoring import get_interests, get_score

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
ADMIN_SCORE = 42
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class SkipField(Exception):
    pass


class NullValueNotAllowed(Exception):
    pass


class Field(abc.ABC):

    def __init__(self, required=True, nullable=False):
        self.required = required
        self.nullable = nullable

    def __set_name__(self, owner, name):
        self.private_name = "_" + name

    def __get__(self, obj, objtype=None):
        return (
            getattr(obj, self.private_name, None)
            if self.nullable
            else getattr(obj, self.private_name)
        )

    def __set__(self, obj, value):
        self.validate(value)
        setattr(obj, self.private_name, value)

    @abc.abstractmethod
    def validate(self, value):
        pass


class CharField(Field):
    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError(f"Expected {value!r} to be an str")


class ArgumentsField(Field):
    def validate(self, value):
        if not isinstance(value, dict):
            raise TypeError(f"Expected {value!r} to be an dict")


class EmailField(CharField):
    def validate(self, value):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise ValueError("invalid email")


class PhoneField(Field):
    def validate(self, value):
        if isinstance(value, str):
            if len(value) != 11 or not re.match(r"^7\d{10}", value):
                raise ValueError(
                    f"Expected {value!r} to be a 11-digit string starting with 7"
                )
        elif isinstance(value, int):
            if value > 79_999_999_999 or value < 70_000_000_000:
                raise ValueError(f"Expected {value!r} 11-digit number starting with 7")


class DateField(Field):
    def __set__(self, obj, value):
        self.validate(value)
        value = datetime.datetime.strptime(value, "%d.%m.%Y")
        setattr(obj, self.private_name, value)

    def validate(self, value):
        # TODO: add valid date check
        if not re.match(r"(\d){2}\.(\d){2}\.(\d){4}", value):
            raise ValueError(f"Expected {value!r} to be in format dd.mm.yyyy")


class BirthDayField(DateField):
    max_birthday = datetime.datetime(year=1900, month=1, day=1)

    def validate(self, value):
        super().validate(value)

        value_date = datetime.datetime.strptime(value, "%d.%m.%Y")
        if (value_date - self.max_birthday).days < 0:
            raise ValueError(f"Expected {value!r} to be not more than 01.01.1900")


class GenderField(Field):
    def validate(self, value):
        if value not in GENDERS.keys():
            raise ValueError(f"Expected one of {GENDERS.values()}")


class ClientIDsField(Field):
    def validate(self, value):
        if not (isinstance(value, list) or isinstance(value, tuple)):
            raise TypeError(f"Expected {value} to be a list or tuple")
        if len(value) < 1:
            raise ValueError(f"Expected client_ids {value} to be not empty")
        for item in value:
            if not isinstance(item, int):
                raise TypeError(f"Expected client id {value} to be a integer")


class BaseRequest(abc.ABC):
    @classmethod
    def from_json(cls, data):
        instance = cls()

        for field_name, field in cls.__dict__.items():
            if isinstance(field, Field):
                value = data.get(field_name)

                if field.required and value is None and not field.nullable:
                    raise ValueError(f"Missing required field: {field_name}")

                if value is None and field.nullable:
                    continue

                setattr(instance, field_name, value)

        return instance

    def validate(self):
        for attr_name, attr_value in self.__class__.__dict__.items():
            if isinstance(attr_value, Field):
                if attr_value.required and getattr(self, attr_name, None) is None:
                    raise ValueError(f"{type}: {attr_name} is required")
                if not attr_value.nullable and getattr(self, attr_name) is None:
                    raise ValueError(f"{type}: {attr_name} cannot be null")

    def presented_fields(self):
        """
        Returns fields that are presented in request
        (fields that have value if it None in case of nullable=True )
        """
        return [attr.strip("_") for attr in self.__dict__]


class ClientsInterestsRequest(BaseRequest):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(BaseRequest):
    _valid_fields_combinations = (
        ("email", "phone"),
        ("first_name", "last_name"),
        ("birthday", "gender"),
    )

    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def validate(self):
        super().validate()

        invalid_request = True
        presented_fields = set(self.presented_fields())
        for valid_combination in self._valid_fields_combinations:
            if len(set(valid_combination) - presented_fields) == 0:
                invalid_request = False
                break
        if invalid_request:
            raise ValueError(
                f"Expected one if required fields set: {self._valid_fields_combinations} "
            )


class MethodRequest(BaseRequest):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        digest = hashlib.sha512(
            (request.account + request.login + SALT).encode("utf-8")
        ).hexdigest()
    return digest == request.token


def make_request(body: dict, target_class: BaseRequest):
    # req = target_class()
    # for field_name, field_value in body.items():
    #     setattr(req, field_name, field_value)    # descriptors are not invoked in this case
    # return req
    return target_class.from_json(body)


def scoring_handler(ctx, store, body, is_admin):
    online_score_req: OnlineScoreRequest = make_request(body, OnlineScoreRequest)
    online_score_req.validate()

    ctx["has"] = online_score_req.presented_fields()

    if is_admin:
        score = ADMIN_SCORE
    else:
        score = get_score(
            store,
            online_score_req.phone,
            online_score_req.email,
            online_score_req.birthday,
            online_score_req.gender,
            online_score_req.first_name,
            online_score_req.last_name,
        )

    return {"score": score}


def interests_handler(ctx, store, body, is_admin):
    clients_interest_req: ClientsInterestsRequest = make_request(
        body, ClientsInterestsRequest
    )
    clients_interest_req.validate()

    ctx["nclients"] = len(clients_interest_req.client_ids)

    interests = dict()
    for cid in clients_interest_req.client_ids:
        interests[cid] = get_interests(store, cid)

    return interests


def method_handler(request, ctx, store):
    router = {
        "online_score": scoring_handler,
        "clients_interests": interests_handler,
    }

    try:
        method_request: MethodRequest = make_request(request["body"], MethodRequest)
        method_request.validate()
        if check_auth(request=method_request):  # make authentication

            try:
                response = router[method_request.method](
                    ctx, store, method_request.arguments, method_request.is_admin
                )
                code = OK

            except KeyError:
                code = BAD_REQUEST
                response = (
                    "Expected method to be one of [online_score, clients_interests]"
                )
        else:
            code = FORBIDDEN
            response = ERRORS[code]
    except (ValueError, TypeError) as err:
        # logging.exception("Request validation error: %s" % err)
        code = INVALID_REQUEST
        response = str(err)

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {"method": method_handler}
    store = None

    def get_request_id(self, headers):
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))

            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers}, context, self.store
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))
        return


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    server = HTTPServer(("localhost", args.port), MainHTTPHandler)

    logging.info("Starting server at %s" % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
