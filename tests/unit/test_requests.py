import re
from datetime import datetime
import pytest

from scoring.api import ADMIN_LOGIN, ClientsInterestsRequest, MethodRequest, OnlineScoreRequest


@pytest.mark.parametrize("request_data", [
    {},
    {"date": "01.01.2025"}
])
def test_clients_interests_request_invalid_json(request_data):
    with pytest.raises(ValueError, match="ClientsInterestsRequest: client_ids is required"):
        req = ClientsInterestsRequest.from_json(request_data)
        req.validate()



@pytest.mark.parametrize("request_data", [
    {"client_ids": [1]},
    {"client_ids": [1, 2, 3]},
    {"client_ids": [1, 2, 3], "date": None},
    {"client_ids": [1, 2, 3], "date": "01.01.2025"},
])
def test_clients_interests_request_valid_json(request_data):
    request = ClientsInterestsRequest.from_json(request_data)
    assert request.client_ids == request_data["client_ids"]

    expected_date = None
    if request_data.get("date"):
        print(f"request_data.get('date')={request_data.get("date")}")
        expected_date = datetime.strptime(request_data.get("date"), '%d.%m.%Y')
    assert request.date == expected_date


def test_method_request_validate_missing_fields():
    request = MethodRequest.from_json({
        "login": ADMIN_LOGIN, "token": "token", "method": "method"
        })
    with pytest.raises(ValueError, match=re.escape("MethodRequest: arguments is required")):
        request.validate()


def test_presented_fields():
    request = OnlineScoreRequest()
    request.first_name = "John"
    request.email = "john@example.com"
    assert request.presented_fields() == ["first_name", "email"]


def test_clients_interests_request_presented_fields():
    data = {
        "client_ids": [1, 2, 3],
        "date": None
    }
    request = ClientsInterestsRequest.from_json(data)
    assert request.presented_fields() == ["client_ids", "date"]


@pytest.mark.parametrize("arg_combination", [
    {"first_name":"Alice", "birthday":"01.01.2000"}
])
def test_online_score_request_validate_invalid_combination(arg_combination):
    request = OnlineScoreRequest.from_json(arg_combination)
    print("!!!!!!!" +  str(request.__dict__))
    with pytest.raises(ValueError, match=re.escape("Expected one of required fields set  "
                                           "(('email', 'phone'), ('first_name', 'last_name'), ('birthday', 'gender')) "
                                           "to be presented in request")):
        request.validate()

@pytest.mark.parametrize("arg_combination", [
    {"first_name":"Ivan", "last_name":"Petrov"},
    {"email":"alice@example.com", "phone":"71234567890"},
])
def test_online_score_request_validate_valid_combination(arg_combination):
    request = OnlineScoreRequest.from_json(arg_combination)
    request.validate()  

def test_method_request_is_admin():
    request = MethodRequest.from_json({
        "login": ADMIN_LOGIN, "token": "token", "arguments":{}, "method": "method"
        })
    assert request.is_admin

def test_method_request_is_not_admin():
    request = MethodRequest.from_json({
        "login": "user", "token": "token", "arguments":{}, "method": "method"
        })
    assert not request.is_admin
