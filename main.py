from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


APP_NAME = "weather_app"
USER_ID = "1234"
SESSION_ID = "session1234"


# Mock tool implementation
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    return {"status": "success", "city": city, "time": "10:30 AM"}


root_agent = Agent(
    model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
    name="root_agent",
    description="Tells the current time in a specified city.",
    instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.",
    tools=[get_current_time],
)
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent, app_name="root_agent", session_service=session_service
)


def get_or_create_session():
    """Get existing session or create a new one if it doesn't exist."""
    try:
        return session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
    except Exception:
        return session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )


# Agent Interaction
def call_agent(query: str) -> str:
    """Call the agent with a user query and return the response."""
    try:
        print(f"\n📝 Received query: {query}\n")

        # Ensure session exists
        get_or_create_session()

        content = types.Content(role="user", parts=[types.Part(text=query)])
        events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

        final_answer = None
        event_count = 0

        for event in events:
            event_count += 1
            print(f"\nDEBUG EVENT #{event_count}: {event}\n")
            if event.is_final_response() and event.content:
                final_answer = event.content.parts[0].text.strip()
                print(f"\n🟢 FINAL ANSWER\n{final_answer}\n")

        print(f"\nTotal events processed: {event_count}")

        if final_answer is None:
            print("\n⚠️  WARNING: No final answer was generated\n")
            return "Error: Agent did not generate a response"

        return final_answer

    except Exception as e:
        print(f"\n❌ ERROR in call_agent: {e}\n")
        import traceback

        traceback.print_exc()
        return f"Error: {str(e)}"


from fastapi import FastAPI

app = FastAPI()

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(message: ChatRequest) -> dict:
    """Chat endpoint that processes user messages through the agent."""
    try:
        response = call_agent(message.message)
        return {"message": response}
    except Exception as e:
        print(f"\n❌ ERROR in chat endpoint: {e}\n")
        return {"message": None, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
