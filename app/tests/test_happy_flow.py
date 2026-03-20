def test_full_patient_flow(client, call_id, phone_number):
    # 1. Lookup (should not exist)
    payload = {
        "phone_number": phone_number
    }

    res = client.post(
        "/voice/tool-call",
        json={
            "message": {
                "call": {"id": call_id, "customer": {"number": phone_number}},
                "toolCallList": [
                    {
                        "id": "1",
                        "function": {
                            "name": "lookup_caller_by_phone",
                            "arguments": payload,
                        },
                    }
                ],
            }
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data is not None

    # 2. Register patient
    register_payload = {
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": phone_number,
        "date_of_birth": "1995-05-10",
        "sex": "male",
        "address_line_1": "123 Main St",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
    }

    res = client.post(
        "/voice/tool-call",
        json={
            "message": {
                "call": {"id": call_id, "customer": {"number": phone_number}},
                "toolCallList": [
                    {
                        "id": "2",
                        "function": {
                            "name": "register_patient",
                            "arguments": register_payload,
                        },
                    }
                ],
            }
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "data" in data

    # 3. Lookup again (should exist now)
    res = client.post(
        "/voice/tool-call",
        json={
            "message": {
                "call": {"id": call_id, "customer": {"number": phone_number}},
                "toolCallList": [
                    {
                        "id": "3",
                        "function": {
                            "name": "lookup_caller_by_phone",
                            "arguments": {"phone_number": phone_number},
                        },
                    }
                ],
            }
        },
    )
    assert res.status_code == 200
    assert res.json()["data"] is not None

    # 4. End call
    res = client.post(
        "/voice/end-of-call",
        json={
            "message": {
                "call": {"id": call_id, "customer": {"number": phone_number}},
                "artifact": {"transcript": "Test transcript"},
                "durationSeconds": 30,
                "endedReason": "completed",
            }
        },
    )
    assert res.status_code == 200