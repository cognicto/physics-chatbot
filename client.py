import asyncio
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage

async def main():
    # Connect to the LangGraph server using SDK
    url_for_cli_deployment = "http://localhost:8123"
    client = get_client(url=url_for_cli_deployment)

    try:
        print("✅ Connected to the physics-chatbot API")

        # Create a new thread to store conversation state
        thread = await client.threads.create()
        print(f"🧵 Created Thread: {thread['thread_id']}")

        # Send a test query
        user_input = input("Enter your question: ")
        config = {}
        graph_name = "RetrievalGraph"

        # Create a run (fire and forget)
        run = await client.runs.create(
            thread["thread_id"],
            graph_name,
            input={"messages": [HumanMessage(content=user_input)]},
            config=config
        )
        print(f"🚀 Run created: {run['run_id']}")

        # Poll the status until completion
        print("⏳ Waiting for response...")
        await client.runs.join(thread["thread_id"], run["run_id"])
        result = await client.runs.get(thread["thread_id"], run["run_id"])

        print("✅ Response Received:")
        for message in result.get("values", {}).get("messages", []):
            print(f"{message.get('type', 'AI')}: {message.get('content')}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

