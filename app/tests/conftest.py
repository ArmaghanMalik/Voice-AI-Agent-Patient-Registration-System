import pytest
import httpx
from uuid import uuid4

BASE_URL = "http://localhost:8000"


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL)


@pytest.fixture
def call_id():
    return str(uuid4())


@pytest.fixture
def phone_number():
    return "+1234567890"


def build_tool_payload(call_id, phone_number, tool_name, arguments):
    return {
        "message": {
            "call": {
                "id": call_id,
                "customer": {"number": phone_number},
            },
            "toolCallList": [
                {
                    "id": str(uuid4()),
                    "function": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                }
            ],
        }
    }