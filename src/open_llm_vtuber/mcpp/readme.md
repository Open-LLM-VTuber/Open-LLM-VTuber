# MCP Plus for Open-LLM-VTuber

English / [中文](./readme.zh.md)



## 📄 Introduction

> MCP (Model Context Protocol) is an open protocol that standardizes how applications provide context to LLMs. Think of MCP like a USB-C port for AI applications. Just as USB-C provides a standardized way to connect your devices to various peripherals and accessories, MCP provides a standardized way to connect AI models to different data sources and tools.
> From: [MCP Official Document][1]

As MCP is a powerful tool for LLMs to call functions, reach resources on your computer and give some useful prompts, implementing it in Open-LLM-VTuber seems a high rewarding action. So it just right here.



## ➕ About "Plus"

As some LLMs' API support `tools` parameter, we decided to integrate the `Tool Use` feature into the MCP implemention. Don't be worried, we didn't make any modifications to the Protocol itself, just stitched two features together.



## 📁 File Structure

- `mcpp/` - The main folder of MCP Plus module.
    - `configs/` - Configuration files.
        - `mcp_servers.json` - Config file for MCP.
        - `servers_prompt.json` - MCP servers' prompts, will pass to LLMs.
    - `servers/` - Custom MCP servers should be stored here (or may change it at 'mcp_servers.json').
        - `example.py` - Basic python MCP server example, contains a tool named `calculate_bmi`.
    - `utils/` - Some useful generic functions.
        - `path.py` - Now contains a common file validation logic.
    - `client.py` - The MCP client implemention.
    - `json_detector.py` - Used to detect JSON objects from text.
    - `prompt_constructor` - MCP server/tool prompts constructor.
    - `readme.md` - You are reading it.
    - `readme.zh.md` - The Chinese version of readme file.
    - `server_manager.py` - The MCP servers manager.
    - `types.py` - Standard data structures.



## 🔧 Usage

Well, you don't have to modify client file, because about when and how to interact with a MCP server is already defined. If you're a project(Open-LLM-VTuber) developer, you can refer to [#Developing](#️-developing). 

So for common users (or MCP server developers), you can follow these steps to add your MCP server:

1. Confirm your **MCP server type**. Here we categorize servers into two types:
    - ***official***: refer to the servers you found at [Model Context Protocol servers][2] or any server can be run via `npx` or `uvx` (see details at [#References#uvx & npx](#uvx--npx)).
    - ***custom***: refer to the servers developed by yourself or servers cannot be run via `npx` or `uvx`, but they should be run via `python` or `node`.

2. Confirm your **MCP server file type** is supported. Currently, we support `.py`(Python files) and `.js`(Compiled from TypeScipt).

3. Open `mcp_servers.json`

4. For ***official*** MCP servers, you need to extend the `officials` field of `mcp_servers.json` with following format:
```json
"<MCP server name>": {
    "command": "uvx/npx",
    "args": ["<MCP server module/package name>", "...(other arguments)"]
}
```
Fields wrapped in '<>' are things you shuold change and 'a/b' means you should choose 'a' or 'b'. If you are still confused, here is an example of adding [MCP Servers - Time][3]:
In the section **Configuration-Configure for Claude.app-Using uvx** of its readme file, we see such json config(2 indent):
```json
"mcpServers": {
  "time": {
    "command": "uvx",
    "args": ["mcp-server-time"]
  }
}
```
Then, it should be like this in our `mcp_servers.json`(4 indent):
```json
"officials": {
    "time": {
        "command": "uvx",
        "args": ["mcp-server-time"]
    }
}
```
> You may need to use json validate tool to configure it correctly
> [JSON formatter][4]

**Important: Official servers require you to configure them correctly, otherwise you will meet problems.**

5. For ***custom*** MCP Servers, you need to confirm field `custom_servers_path`, we recommand not to change it, but if you still want to change it, it is better to use absolute path. Then, put your server file into the folder, default is `./servers`(as [#File Structure](#-file-structure)). And, nothing else.
**NOTE:** The relative path in `mcp_servers.json` is relative to `/mcp`



## 📚 References

### uvx & npx
Requirements for Running MCP Servers via `uvx` or `npx`

**uvx for Python-based MCP Servers:**

- **Installed the python package and project manager - uv**, see [uv Document][5] for further information.
- The MCP server must be published and registered on **PyPI** (Python Package Index)
- It automatically downloads and installs the MCP server from PyPI when running (if not locally available)
- Provides a convenient way to use Python-based MCP servers without manual installation steps

For example: `uvx mcp-server-git --repository ./my-repo` will run the git MCP server for providing repository context to your LLM

**npx for Node.js-based MCP Servers:**

- **Installed Node.js**, see [Node.js Website][6]
- Can run locally installed MCP servers (as project dependencies or global packages)
- Can directly fetch and run MCP servers published to the npm registry
- The MCP server must be registered in the npm repository
- The MCP server package must define executable commands in its package.json

For example: `npx @mcp/server-filesystem --directory ./my-docs` will run the filesystem MCP server to provide file access capabilities

Both commands help simplify the process of running MCP servers by handling dependencies automatically。



## 🛠️ Developing

> I haven't figured out how to write it yet



[1]: <https://modelcontextprotocol.io/introduction>
[2]: <https://github.com/modelcontextprotocol/servers>
[3]: <https://github.com/modelcontextprotocol/servers/tree/main/src/time#configuration>
[4]: <https://jsonformatter.org/>
[5]: <https://docs.astral.sh/uv/getting-started/installation/>
[6]: <https://nodejs.org/en>