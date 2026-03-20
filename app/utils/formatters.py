from datetime import date
from typing import Any


def format_phone_display(digits: str) -> str:
    if len(digits) != 10 or not digits.isdigit():
        return digits
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def format_date_for_voice(d: date) -> str:
    return d.strftime(f"%B {d.day}, %Y")


def format_patient_for_voice_confirmation(patient_data: dict[str, Any]) -> str:
    lines = ["Here is the information I have collected:"]

    lines.append(f"First name: {patient_data.get('first_name', 'not provided')}.")
    lines.append(f"Last name: {patient_data.get('last_name', 'not provided')}.")

    dob = patient_data.get("date_of_birth")
    if isinstance(dob, date):
        lines.append(f"Date of birth: {format_date_for_voice(dob)}.")
    elif dob:
        lines.append(f"Date of birth: {dob}.")

    sex = patient_data.get("sex")
    if sex:
        lines.append(f"Sex: {sex}.")

    phone = patient_data.get("phone_number")
    if phone:
        lines.append(f"Phone number: {format_phone_display(phone)}.")

    email = patient_data.get("email")
    if email:
        lines.append(f"Email: {email}.")

    addr1 = patient_data.get("address_line_1")
    addr2 = patient_data.get("address_line_2")
    city  = patient_data.get("city")
    state = patient_data.get("state")
    zipcd = patient_data.get("zip_code")
    if addr1:
        addr = addr1
        if addr2:
            addr += f", {addr2}"
        if city and state and zipcd:
            addr += f", {city}, {state} {zipcd}"
        lines.append(f"Address: {addr}.")

    insurance = patient_data.get("insurance_provider")
    if insurance:
        member_id = patient_data.get("insurance_member_id", "")
        if member_id:
            lines.append(f"Insurance: {insurance}, member ID {member_id}.")
        else:
            lines.append(f"Insurance provider: {insurance}.")

    ec_name  = patient_data.get("emergency_contact_name")
    ec_phone = patient_data.get("emergency_contact_phone")
    if ec_name:
        ec = f"Emergency contact: {ec_name}"
        if ec_phone:
            ec += f", reachable at {format_phone_display(ec_phone)}"
        lines.append(ec + ".")

    lang = patient_data.get("preferred_language")
    if lang and lang.lower() != "english":
        lines.append(f"Preferred language: {lang}.")

    lines.append("Is all of that correct?")
    return " ".join(lines)