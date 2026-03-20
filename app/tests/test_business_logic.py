def test_duplicate_registration(client, call_id, phone_number):
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": phone_number,
        "date_of_birth": "1995-05-10",
        "sex": "male",
    }

    for _ in range(2):
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
                                "arguments": payload,
                            },
                        }
                    ],
                }
            },
        )

    # second call should fail or handle gracefully
    assert res.status_code in [200, 400]


def test_partial_update(client, call_id, phone_number):
    res = client.post(
        "/voice/tool-call",
        json={
            "message": {
                "call": {"id": call_id, "customer": {"number": phone_number}},
                "toolCallList": [
                    {
                        "id": "1",
                        "function": {
                            "name": "update_patient",
                            "arguments": {
                                "phone_number": phone_number,
                                "email": "john@example.com",
                            },
                        },
                    }
                ],
            }
        },
    )

    assert res.status_code == 200