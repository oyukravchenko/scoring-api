import datetime
import pytest
import re

from scoring.api import ArgumentsField, BirthDayField, CharField, ClientIDsField, DateField, EmailField, GenderField, PhoneField


@pytest.mark.parametrize("cls", [
        CharField,
        EmailField,
        PhoneField,
        DateField,
        BirthDayField,
        ArgumentsField
    ])
def test_nullable_field( cls):
    field = cls(nullable=True)
    field.validate(None)


@pytest.mark.parametrize("cls", [
        CharField,
        EmailField,
        PhoneField,
        DateField,
        BirthDayField,
        ArgumentsField
    ])
def test_required_field(cls):
    field = cls(required=True, nullable=False)
    with pytest.raises(AttributeError):
        field.__get__(None)


class TestCharField:
    @pytest.mark.parametrize("test_str", [
        "valid_string",
        "2123123",
        "",
        "a",
        "very long str" * 1_000_000,
        "!@#%^&*(()_+=[])"
    ])
    def test_validate_valid_string(self, test_str):
        field = CharField(required=True)
        field.validate(test_str) 

    def test_validate_invalid_type(self):
        field = CharField(required=True)
        with pytest.raises(TypeError, match="Expected 123 to be an str"):
            field.validate(123)


class TestArgumentsField:
    def test_validate_valid_dict(self):
        field = ArgumentsField(required=True)
        field.validate({"key": "value"})  

    def test_validate_invalid_type(self):
        field = ArgumentsField(required=True)
        with pytest.raises(TypeError, match=re.escape("Expected [1, 2] to be an dict")):
            field.validate([1, 2])   


class TestEmailField:
    @pytest.mark.parametrize("email", [
        "user@example.com",
        "u@e.c",
        "123@123.123"
    ])
    def test_validate_valid_email(self, email):
        field = EmailField(required=True)
        field.validate(email) 

    @pytest.mark.parametrize("email", [
        "@adsd.ru",
        "asd@com",
        "asdasda",
        "12123123",
        "1212-12-12"
        "@a@.re",
        ""
    ])
    def test_validate_invalid_email(self, email):
        field = EmailField(required=True)
        with pytest.raises(ValueError, match=f"invalid email {email}"):
            field.validate(email)


class TestPhoneField:
    @pytest.mark.parametrize("phone_value", [
        "71234567890",
        "70000000000",
        "79999999999",
        70000000000,
        79999999999,
    ])
    def test_validate_valid_phone_string(self, phone_value):
        field = PhoneField(required=True)
        field.validate(phone_value)

    @pytest.mark.parametrize("phone_value", [
        "7123456789",
        "80000000000",
        "60000000000",
        "asdasdasdas",
        "asd",
        "a",
        ""
    ])
    def test_validate_invalid_phone_string(self, phone_value):
        field = PhoneField(required=True)
        with pytest.raises(ValueError, match=f"Expected '{phone_value}' to be a 11-digit string starting with 7"):
            field.validate(phone_value)  
    
    @pytest.mark.parametrize("phone_value", [
        7123456789,
        60000000000,
        80000000000,
    ])
    def test_validate_invalid_phone_int(self, phone_value):
        field = PhoneField(required=True)
        with pytest.raises(ValueError, match=f"Expected {phone_value} 11-digit number starting with 7"):
            field.validate(phone_value)  

    def test_nullable_field_with_none(self):
        field = PhoneField(nullable=True)
        field.validate(None)  # Не должно вызывать исключений


class TestDateField:
    def test_validate_valid_date(self):
        field = DateField(required=True)
        field.validate("31.12.2020") 

    @pytest.mark.parametrize("date", [
        "01/01/2000",
        "01-01-2025",
        "01 Jan 1926"
    ])
    def test_validate_invalid_date_format(self, date):
        field = DateField(required=True)
        with pytest.raises(ValueError, match=f"Expected '{date}' to be in format dd.mm.yyyy"):
            field.validate(date) 


class TestBirthDayField:
    @pytest.mark.parametrize("bday", [
        "01.01.2000",
        "01.01.2025",
        "01.01.1926"
    ])
    def test_validate_under_max_age(self, bday):
        field = BirthDayField(required=True, max_age=100)
        field.validate(bday)  

    def test_validate_over_max_age(self):
        field = BirthDayField(required=True, max_age=30)
        with pytest.raises(ValueError, match="Expected '01.01.1960' to be not more than 30 years old"):
            field.validate("01.01.1960")

    @pytest.mark.parametrize("date", [
        "01/01/2000",
        "01-01-2025",
        "01 Jan 1926"
    ])
    def test_validate_invalid_date_format(self, date):
        field = BirthDayField(required=True)
        with pytest.raises(ValueError, match=f"Expected '{date}' to be in format dd.mm.yyyy"):
            field.validate(date)


class TestGenderField:

    @pytest.mark.parametrize("gender", [0, 1, 2])
    def test_valid_gender(self, gender):
        field = GenderField(required=True)
        field.validate(gender) 

    def test_invalid_gender(self):
        field = GenderField(required=True)
        with pytest.raises(ValueError,
                           match=re.escape("Expected one of [0, 1, 2]")):
            field.validate("other")  


class TestClientIDsField:
    def test_validate_valid_client_ids(self):
        field = ClientIDsField(required=True, min_size=2)
        field.validate([1, 2, 3])  

    @pytest.mark.parametrize("client_ids", [
        "invalid",
        True,
        datetime.datetime.now(),
        123,
        {"key": "value"}
    ])
    def test_validate_invalid_type(self, client_ids):
        field = ClientIDsField(required=True)
        with pytest.raises(TypeError, match=f"Expected {client_ids} to be a list or tuple"):
            field.validate(client_ids)  

    def test_validate_empty_client_ids(self):
        field = ClientIDsField(required=True, min_size=2)
        with pytest.raises(ValueError, match=re.escape("Expected client_ids [] to be not empty")):
            field.validate([])

    def test_validate_invalid_item_type(self):
            field = ClientIDsField(required=True)
            with pytest.raises(TypeError, match=re.escape("Expected client id [1, 'invalid'] to be a integer")):
                field.validate([1, 'invalid'])