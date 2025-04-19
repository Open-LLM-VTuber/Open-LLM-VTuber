# Open-LLM-VTuber的MCP模块

[English](./readme.md) / 中文

## 📄 简介

> MCP（Model Context Protocol，模型上下文协议）是一个开放协议，用于标准化应用程序如何向LLM提供上下文。可以将MCP视为AI应用的USB-C接口。就像USB-C为设备连接各种外设和配件提供了标准化方式，MCP为AI模型连接不同数据源和工具提供了标准化方式。
> 来源：[MCP官方文档][1]

由于MCP是LLM调用函数、访问计算机资源和提供有用提示的强大工具，在Open-LLM-VTuber中实现它似乎是一个回报很高的行动。所以它就在这里了。

## 📁 文件结构

- `mcp/` - MCP模块的主文件夹。
    - `configs/` - 配置文件。
        - `mcp_servers.json` - MCP的配置文件。
        - `servers_prompt.json` - MCP服务器的提示，将传递给LLM。
    - `servers/` - 自定义MCP服务器应该存储在这里（或者可以在'mcp_servers.json'中更改）。
        - `example.py` - 基本的Python MCP服务器示例，包含一个名为`calculate_bmi`的工具。
    - `client.py` - MCP客户端实现。
    - `prompt_constructor` - MCP服务器/工具提示构造器。
    - `readme.md` - 英文版说明文件。
    - `readme.zh.md` - 你正在阅读的中文版说明文件。
    - `server_manager.py` - MCP服务器管理器。

## 🔧 使用方法

你不必修改客户端文件，因为何时以及如何与MCP服务器交互已经定义好了。如果你是项目(Open-LLM-VTuber)开发者，可以参考[#开发](#️-开发)。

对于普通用户（或MCP服务器开发者），你可以按照以下步骤添加你的MCP服务器：

1. 确认你的**MCP服务器类型**。这里我们将服务器分为两种类型：
    - ***官方***：指你在[Model Context Protocol servers][2]找到的服务器或任何可以通过`npx`或`uvx`运行的服务器（参见[#参考#uvx & npx](#uvx--npx)）。
    - ***自定义***：指由你自己开发的服务器或无法通过`npx`或`uvx`运行的服务器，但它们应该通过`python`或`node`运行。

2. 确认你的**MCP服务器文件类型**是否被支持。目前，我们支持`.py`（Python文件）和`.js`（从TypeScript编译）。

3. 打开`mcp_servers.json`

4. 对于***官方***MCP服务器，你需要按照以下格式扩展`mcp_servers.json`的`officials`字段：
```json
"<MCP服务器名称>": {
    "command": "uvx/npx",
    "args": ["<MCP服务器模块/包名>", "...(其他参数)"]
}
```
用`<>`包裹的字段是你应该更改的内容，而'a/b'表示你应该选择'a'或'b'。如果你仍然感到困惑，这里有一个添加[MCP Servers - Time][3]的例子：
在其readme文件的**Configuration-Configure for Claude.app-Using uvx**部分，我们看到这样的json配置（2缩进）：
```json
"mcpServers": {
  "time": {
    "command": "uvx",
    "args": ["mcp-server-time"]
  }
}
```
那么，在我们的`mcp_servers.json`中应该是这样的（4缩进）：
```json
"officials": {
    "time": {
        "command": "uvx",
        "args": ["mcp-server-time"]
    }
}
```
> 你可能需要使用json验证工具来正确配置它
> [JSON格式化工具][4]

**重要提示：官方服务器需要你正确配置它们，否则你将遇到问题。**

5. 对于***自定义***MCP服务器，你需要确认`custom_servers_path`字段，我们建议不要更改它，但如果你仍然想更改它，最好使用绝对路径。然后，将你的服务器文件放入文件夹中，默认是`./servers`（如[#文件结构](#-文件结构)所示）。除此之外，没有其他要做的。
**注意：**`mcp_servers.json`中的相对路径是相对于`/mcp`的

## 📚 参考

### uvx & npx
通过`uvx`或`npx`运行MCP服务器的要求

**uvx用于基于Python的MCP服务器：**

- **已安装Python包和项目管理器 - uv**，更多信息请参见[uv文档][5]。
- MCP服务器必须已发布并注册在**PyPI**（Python包索引）上
- 运行时会自动从PyPI下载并安装MCP服务器（如果本地不可用）
- 提供了一种方便的方式来使用基于Python的MCP服务器，无需手动安装步骤

例如：`uvx mcp-server-git --repository ./my-repo`将运行git MCP服务器，为你的LLM提供存储库上下文

**npx用于基于Node.js的MCP服务器：**

- **已安装Node.js**，请参见[Node.js网站][6]
- 可以运行本地安装的MCP服务器（作为项目依赖或全局包）
- 可以直接获取并运行发布到npm注册表的MCP服务器
- MCP服务器必须在npm存储库中注册
- MCP服务器包必须在其package.json中定义可执行命令

例如：`npx @mcp/server-filesystem --directory ./my-docs`将运行文件系统MCP服务器以提供文件访问功能

这两个命令都通过自动处理依赖项来简化运行MCP服务器的过程。

## 🛠️ 开发

> 我还没有想好如何写这部分

[1]: <https://mcp-docs.cn/introduction>
[2]: <https://github.com/modelcontextprotocol/servers>
[3]: <https://github.com/modelcontextprotocol/servers/tree/main/src/time#configuration>
[4]: <https://www.json.cn/>
[5]: <https://hellowac.github.io/uv-zh-cn/#_2>
[6]: <https://nodejs.org/zh-cn>