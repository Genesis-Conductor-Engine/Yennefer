import os
from dotenv import load_dotenv
from uagents_core.utils.registration import (
    register_chat_agent,
    RegistrationRequestCredentials,
)

# Load environment variables from .env if present
load_dotenv(os.path.expanduser('~/.env'))

def main():
    if "AGENTVERSE_KEY" not in os.environ or "AGENT_SEED_PHRASE" not in os.environ:
        print("Error: AGENTVERSE_KEY and AGENT_SEED_PHRASE must be set in the environment.")
        print("Please add them to your ~/.env file or export them directly.")
        return

    print("Registering QFLOP chat agent...")
    try:
        register_chat_agent(
            "QFLOP",
            "https://qflop.yennefer.quest/badtouch",
            active=True,
            credentials=RegistrationRequestCredentials(
                agentverse_api_key=os.environ["AGENTVERSE_KEY"],
                agent_seed_phrase=os.environ["AGENT_SEED_PHRASE"],        
            ),
        )
        print("Successfully registered QFLOP chat agent!")
    except Exception as e:
        print(f"Failed to register agent: {e}")

if __name__ == "__main__":
    main()
