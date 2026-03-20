
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import httpx
from app.core.config import get_settings
from app.agents.system_prompt import VOICE_AGENT_SYSTEM_PROMPT
from app.agents.tool_definations import VOICE_AGENT_TOOLS

VAPI_BASE_URL = "https://api.vapi.ai"


def get_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def create_vapi_assistant(api_key: str, webhook_url: str) -> dict:
    """
    POST /assistant — creates a new Vapi assistant.
    Returns the full assistant object (id field is what you need).
    """
    payload = {
        "name": "Patient Registration Agent",
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.3,   # lower = more consistent, less hallucination
            "systemPrompt": VOICE_AGENT_SYSTEM_PROMPT,
            "tools": VOICE_AGENT_TOOLS,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "sarah",   # natural female voice; change to any ElevenLabs voice ID
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en-US",
        },
        "serverUrl": f"{webhook_url.rstrip('/')}/voice/tool-call",
        "serverUrlSecret": os.getenv("VAPI_WEBHOOK_SECRET", ""),
        "endCallFunctionEnabled": True,
        "recordingEnabled": False,   # set True if you want call recordings
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 900,   # 15 min max — enough for any registration
        "backgroundSound": "off",
        "backchannelingEnabled": True,  # agent says "mm-hmm" etc while caller speaks
        "backgroundDenoisingEnabled": True,
    }

    response = httpx.post(
        f"{VAPI_BASE_URL}/assistant",
        headers=get_headers(api_key),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def update_vapi_assistant(api_key: str, assistant_id: str, webhook_url: str) -> dict:
    """
    PATCH /assistant/:id — updates an existing assistant's prompt and tools.
    Use this instead of create after the first run.
    """
    payload = {
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.3,
            "systemPrompt": VOICE_AGENT_SYSTEM_PROMPT,
            "tools": VOICE_AGENT_TOOLS,
        },
        "serverUrl": f"{webhook_url.rstrip('/')}/voice/tool-call",
    }

    response = httpx.patch(
        f"{VAPI_BASE_URL}/assistant/{assistant_id}",
        headers=get_headers(api_key),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def provision_phone_number(api_key: str, assistant_id: str) -> dict:
    """
    POST /phone-number — buys a US phone number and links it to the assistant.
    This uses a Vapi-provided number (no Twilio account needed).
    """
    payload = {
        "provider": "vapi",
        "assistantId": assistant_id,
        "numberDesiredAreaCode": "415",  # SF area code — change as preferred
    }

    response = httpx.post(
        f"{VAPI_BASE_URL}/phone-number",
        headers=get_headers(api_key),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def list_phone_numbers(api_key: str) -> list:
    """List all phone numbers on the account."""
    response = httpx.get(
        f"{VAPI_BASE_URL}/phone-number",
        headers=get_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Main — run this script once to provision everything
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    settings = get_settings()

    api_key = settings.vapi_api_key
    webhook_url = getattr(settings, "voice_agent_webhook_url", "")

    if not api_key:
        print("ERROR: VAPI_API_KEY is not set in .env")
        sys.exit(1)

    if not webhook_url:
        print("ERROR: VOICE_AGENT_WEBHOOK_URL is not set in .env")
        print("  Set it to your public API URL, e.g. https://your-app.railway.app")
        sys.exit(1)

    existing_id = getattr(settings, "vapi_assistant_id", "")

    if existing_id:
        print(f"Updating existing assistant {existing_id}...")
        assistant = update_vapi_assistant(api_key, existing_id, webhook_url)
        print(f"Assistant updated: {assistant['id']}")
    else:
        print("Creating new Vapi assistant...")
        assistant = create_vapi_assistant(api_key, webhook_url)
        assistant_id = assistant["id"]
        print(f"\nAssistant created!")
        print(f"  Assistant ID: {assistant_id}")
        print(f"  Add to .env:  VAPI_ASSISTANT_ID={assistant_id}\n")

        print("Provisioning phone number...")
        phone = provision_phone_number(api_key, assistant_id)
        print(f"\nPhone number provisioned!")
        print(f"  Number: {phone.get('number', 'see response')}")
        print(f"  Phone ID: {phone.get('id', 'see response')}")
        print(f"\nFull phone response:")
        print(json.dumps(phone, indent=2))