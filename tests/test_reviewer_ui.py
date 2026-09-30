from unittest.mock import Mock

import requests

from app.reviewer_ui import get_error_detail


def test_get_error_detail_from_json_response():
    response = Mock()
    response.json.return_value = {
        "detail": "Ticket is not waiting for review"
    }

    exc = requests.HTTPError("409 Conflict")
    exc.response = response

    assert (
        get_error_detail(exc)
        == "Ticket is not waiting for review"
    )


def test_get_error_detail_from_invalid_json_response():
    response = Mock()
    response.json.side_effect = ValueError()

    exc = requests.HTTPError("500 Internal Server Error")
    exc.response = response

    assert (
        get_error_detail(exc)
        == "500 Internal Server Error"
    )


def test_get_error_detail_without_response():
    exc = requests.HTTPError("Connection failed")

    assert (
        get_error_detail(exc)
        == "Connection failed"
    )