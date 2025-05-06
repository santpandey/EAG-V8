# agent.py

import asyncio
import yaml
from core.loop import AgentLoop
from core.session import MultiMCP

def log(stage: str, msg: str):
    """Simple timestamped console logger."""
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{stage}] {msg}")


# Global variable to store external input
external_user_input = None

async def main(external_input=None):
    global external_user_input
    print("🧠 Cortex-R Agent Ready")
    
    # Prioritize external input if provided
    if external_input:
        user_input = external_input
        external_user_input = external_input
    else:
        user_input = input("🧑 What do you want to solve today? → ")
        external_user_input = user_input

    # Load MCP server configs from profiles.yaml
    with open("config/profiles.yaml", "r") as f:
        profile = yaml.safe_load(f)
        mcp_servers = profile.get("mcp_servers", [])

    multi_mcp = MultiMCP(server_configs=mcp_servers)
    print("Agent before initialize")
    await multi_mcp.initialize()

    agent = AgentLoop(
        user_input=user_input,
        dispatcher=multi_mcp  # now uses dynamic MultiMCP
    )

    try:
        final_response = await agent.run()
        print("\n💡 Final Answer:\n", final_response.replace("FINAL_ANSWER:", "").strip())
        return final_response.replace("FINAL_ANSWER:", "").strip()

    except Exception as e:
        log("fatal", f"Agent failed: {e}")
        return f"Error: {e}"


if __name__ == "__main__":
    asyncio.run(main())


# Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
# How much Anmol singh paid for his DLF apartment via Capbridge? 
# What do you know about Don Tapscott and Anthony Williams?
# What is the relationship between Gensol and Go-Auto?
# which course are we teaching on Canvas LMS?
# Summarize this page: https://theschoolof.ai/
# What is the log value of the amount that Anmol singh paid for his DLF apartment via Capbridge? 