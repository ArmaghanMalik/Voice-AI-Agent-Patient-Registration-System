def test_unknown_tool(client, call_id, phone_number):
    res = client.post(
        "/voice/tool-call",
        json={
            "message": {
                "call": {"id": call_id, "customer": {"number": phone_number}},
                "toolCallList": [
                    {
                        "id": "1",
                        "function": {
                            "name": "unknown_tool",
                            "arguments": {},
                        },
                    }
                ],
            }
        },
    )

    assert res.status_code in [400, 404]


def test_missing_fields(client, call_id, phone_number):
    res = client.post(
        "/voice/tool-call",
        json={
            "message": {
                "call": {"id": call_id, "customer": {"number": phone_number}},
                "toolCallList": [
                    {
                        "id": "1",
                        "function": {
                            "name": "register_patient",
                            "arguments": {
                                "first_name": "John"
                            },
                        },
                    }
                ],
            }
        },
    )

    assert res.status_code in [400, 422]