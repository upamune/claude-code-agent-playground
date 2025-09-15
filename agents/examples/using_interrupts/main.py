#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "claude-code-sdk==0.0.22",
# ]
# requires-python = ">=3.11"
# ///

import asyncio
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions


async def interruptible_task():
    options = ClaudeCodeOptions(allowed_tools=["Bash"], permission_mode="acceptEdits")

    async with ClaudeSDKClient(options=options) as client:
        # Start a long-running task
        await client.query("Count from 1 to 100 slowly")

        # Let it run for a bit
        await asyncio.sleep(2)

        # Interrupt the task
        await client.interrupt()
        print("Task interrupted!")

        # Send a new command
        await client.query("Just say hello instead")

        async for message in client.receive_response():
            # Process the new response
            pass


asyncio.run(interruptible_task())
