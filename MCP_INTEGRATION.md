# 麦当劳 MCP 接入

- Endpoint: `https://mcp.mcd.cn`
- Transport: Streamable HTTP
- Authentication: `Authorization: Bearer <token>`
- 先 JSON-RPC `initialize`，再发送 `notifications/initialized`，然后 `tools/list`、`tools/call`。
- 客户端处理 `application/json` 与 `text/event-stream` 响应，并保留 `Mcp-Session-Id`。
- WorkBuddy 使用 `mcp-config.example.json` 作为结构模板，在**本机**填写 Token；Python CLI 则使用 `MCD_MCP_TOKEN` 环境变量。
- `list-nutrition-foods` 无参数，营养 `data` 可能是 toon 格式。当前脚本解析常见简单 toon 行，不保证覆盖未来所有扩展格式。
- `query-nearby-stores`、`query-meals`、`query-meal-detail`、`calculate-price` 由宿主通过真实 schema 调用，CLI `call` 支持透传。
- 真实鉴权、服务器兼容性和门店菜单需用户连接后验证。


### 可视化 Token 配置（本地 Python 客户端）

运行 `python3 scripts/token_settings.py` 打开本地设置页面，保存后 `scripts/mclittle.py` 自动读取 `~/.config/mc-little-table/token`。WorkBuddy 的 MCP 配置与此独立，仍需在 WorkBuddy 内设置。
