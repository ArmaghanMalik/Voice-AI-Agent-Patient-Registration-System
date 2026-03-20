def test_invalid_phone(client, call_id):
    res = client.post(
        "/voice/tool-call",
        json={
            "message": {
                "call": {"id": call_id, "customer": {"number": "123"}},
                "toolCallList": [
                    {
                        "id": "1",
                        "function": {
                            "name": "register_patient",
                            "arguments": {
                                "first_name": "John",
                                "last_name": "Doe",
                                "phone_number": "123",
                                "date_of_birth": "1995-05-10",
                                "sex": "male",
                            },
                        },
                    }
                ],
            }
        },
    )
    assert res.status_code in [400, 422]


def test_future_dob(client, call_id, phone_number):
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
                                "first_name": "John",
                                "last_name": "Doe",
                                "phone_number": phone_number,
                                "date_of_birth": "2999-01-01",
                                "sex": "male",
                            },
                        },
                    }
                ],
            }
        },
    )
    assert res.status_code in [400, 422]