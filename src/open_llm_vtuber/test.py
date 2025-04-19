from mcpp.client import MCPClient
from mcpp.server_manager import MCPServerManager
from mcpp.mixed_constructor import MixedConstructor


{
    "MCP Server Name": {
        "Tool 1": {
            "description": "Description of Tool 1",
            "parameters": {
                "param1": {
                    "type": "string",
                    "description": "Description of param1",
                },
                "param2": {
                    "type": "integer",
                    "description": "Description of param2",
                },
            },
            "required": ["param1", "param2"],
        }
    }
}
[
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of an location, the user shoud supply a location first",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    }
                },
                "required": ["location"]
            },
        }
    },
]


if __name__ == "__main__":
    # Test the MCPClient.
    import asyncio
    
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    server_manager = MCPServerManager()
    mixed_constructor = MixedConstructor(server_manager=server_manager)

    async def main():
        # async with MCPClient(server_manager) as client:
        #     await client.connect_to_server("example")

        #     # Test error handling by calling a non-existent tool.
        #     await client.call_tool("example_tool", {"arg1": "value1"})
            
        await mixed_constructor.run()
        
    asyncio.run(main())
    
