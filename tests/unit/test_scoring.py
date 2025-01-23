import hashlib
import json
import pytest
from unittest.mock import Mock
from datetime import datetime
from scoring.scoring import get_score, get_interests
from scoring.store import StorageError


@pytest.fixture
def mock_storage():
    return Mock()

@pytest.mark.parametrize(
        "phone, email, birthday, gender, first_name, last_name, expected_score",
        [
            # Тестовые случаи, соответствующие классу эквивалентности и граничным значениям
            (None, None, None, None, None, None, 0.0),                         # все поля None
            ("1234567890", None, None, None, None, None, 1.5),              # только телефон
            (None, "test@example.com", None, None, None, None, 1.5),        # только email
            ("1234567890", "test@example.com", None, None, None, None, 3.0),# телефон и email
            (None, None, datetime(1990, 1, 1), 1, None, None, 1.5),         # только дата рождения и пол
            (None, None, datetime(1990, 1, 1), 1, "John", "Doe", 2.0),      # дата рождения, пол и имена
            ("1234567890", "test@example.com", datetime(1990, 1, 1), 1, "John", "Doe", 5.0),  # все поля заполнены
        ])
def test_get_score(mock_storage, phone, email, birthday, gender, first_name, last_name, expected_score):
    
    mock_storage.cache_get.return_value = None  

    score = get_score(mock_storage, phone, email, birthday, gender, first_name, last_name)
    assert score == expected_score

    key_parts = [
        first_name or "",
        last_name or "",
        str(phone) or "",
        str(birthday.strftime("%Y%m%d")) if birthday else "",
    ]
    key = "uid:" + hashlib.md5("".join(key_parts).encode("utf-8")).hexdigest()
    
    mock_storage.cache_set.assert_called_once_with(key, expected_score, 60 * 60)


@pytest.mark.parametrize(
        "cid, expected_interests", [
            ("user1", ["interest1", "interest2"]),  
            ("user2", []), 
])
def test_get_interests(mock_storage, cid, expected_interests):
    mock_storage.get.return_value = json.dumps(expected_interests)

    interests = get_interests(mock_storage, cid)
    assert interests == expected_interests

    mock_storage.get.assert_called_once_with(f"i:{cid}")


@pytest.mark.parametrize("cid", ["error_case"])
def test_get_interests_storage_error(mock_storage, cid):
    mock_storage.get.side_effect = StorageError("get", "Storage failure")
    with pytest.raises(StorageError):
        get_interests(mock_storage, cid)

    mock_storage.get.assert_called_once_with(f"i:{cid}")


def test_get_score_connection_error(mock_storage):
    mock_storage.cache_get.side_effect = StorageError("cache_get", "ConnectionError: connection failed")

    score = get_score(mock_storage, 
                      phone="1234567890", 
                      email="test@example.com", 
                      birthday=datetime(1990, 1, 1), 
                      gender=1, 
                      first_name="John", 
                      last_name="Doe")

    expected_score = 5.0  

    assert score == expected_score

