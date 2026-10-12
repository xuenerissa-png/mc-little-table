# WorkBuddy 集成说明（WorkBuddy Integration）

本项目是一个原生运行于**腾讯 WorkBuddy 智能体**的 Skill，与 WorkBuddy 的 MCP（Model Context Protocol）能力深度整合。本文档说明真实的集成方式、配置方法与已验证的对话上下文。

## 一、项目在 WorkBuddy 中的形态

```
用户级 Skill（~/.workbuddy/skills/mc-little-table/）
├── SKILL.md                  # WorkBuddy 技能协议文件（触发词、对话流程、安全边界、下单流程）
├── scripts/                  # Python 客户端（纯标准库，WorkBuddy 托管 Python 3.13 直接运行）
└── tests/                    # 离线单元测试

WorkBuddy MCP 配置（~/.workbuddy/mcp.json）
└── mcd-mcp                   # Streamable HTTP → https://mcp.mcd.cn（Bearer 鉴权）
```

- **Skill 层**：WorkBuddy 依据 `SKILL.md` 的 description 在用户提及「孩子吃麦当劳 / 儿童营养 / 麦麦选餐」等意图时自动挂载本技能，按其中定义的对话流程（询问年龄/过敏原/忌辣 → 排除风险餐品 → 给出至多三套差异明确的组合）驱动对话。
- **MCP 层**：WorkBuddy 通过 `mcp.json` 直连麦当劳官方 MCP Server，Skill 亦可调用随包 Python 客户端（读取本机 Token）作为备用通道。

## 二、安装与配置（WorkBuddy 环境）

```bash
# 1. 安装 Skill 到用户级目录
git clone https://github.com/xuenerissa-png/mc-little-table.git ~/.workbuddy/skills/mc-little-table

# 2. 本机保存麦当劳 MCP Token（本地页面，仅 127.0.0.1，Token 权限 0600）
python3 ~/.workbuddy/skills/mc-little-table/scripts/token_settings.py

# 3. WorkBuddy MCP 配置（参考 mcp-config.example.json，Token 从本机文件注入）
#    写入 ~/.workbuddy/mcp.json 后，在 WorkBuddy 连接器管理页对 mcd-mcp 执行「信任」激活
```

## 三、真实对话上下文（已验证的使用记录）

以下为 2026-10-13 在 WorkBuddy 中的真实使用过程摘要，验证了从安装、联调到下单的全链路：

1. **安全审计与安装**：WorkBuddy 对 Skill 包执行全文件安全审计（结论：无命令执行/全局安装/敏感路径风险），安装至用户级 Skill 目录，并通过 12 个离线单元测试。
2. **MCP 配置**：通过 WorkBuddy 写入 `mcp.json` 的 `mcd-mcp` 配置（Streamable HTTP + Bearer Token），Token 由本地页面保存、本机注入，未经过对话传输。
3. **真实联调**：`initialize` + `tools/list` 成功（35 个工具）；`list-nutrition-foods` 返回 160 条真实餐品营养数据。期间发现官方返回带 Markdown 包装层（`## Original Response`），已修复解析器并通过回归测试。
4. **选餐实战**：用户提问「3.5 岁孩子吃麦当劳，在柯木朗附近，能吃啥」——
   - `query-nearby-stores`（keyword=柯木朗, city=广州）→ 5 家门店，最近 437 米；
   - `query-meals` 获取在售菜单（68 品）与营养库按名称精确匹配（10 品）；
   - 按 3.5 岁钠参考值（保守取 1–3 岁 <1200mg/日）筛选，输出：苹果片(0mg) + 纯悦(0mg) + 麦香鸡(731mg, 61% 日参考) 的推荐组合，并显式标注过敏原未核实项与不推荐的高钠餐品（双层吉士 1017mg / 板烧 1041mg / 麦辣系列）。
5. **下单实战**（家长明确同意后）：
   - `calculate-price` 确认购物车 ¥31.50 → 家长二次确认 → `create-order`（orderType=1 + takeWayCode=eat-in）→ 返回 orderId 与 payH5Url，付款链接交由家长本人在 15 分钟时限内完成支付；
   - 该实战中发现并沉淀了 `takeWayCode` 必传规则（缺失报错 600042）。

## 四、与 WorkBuddy 能力的结合点

| WorkBuddy 能力 | 本项目的使用方式 |
|---|---|
| Skill 触发与对话流程管理 | `SKILL.md` 定义选餐对话流程、安全边界与下单 SOP |
| MCP 连接器（mcp.json） | 直连麦当劳官方 MCP Server，35 个工具可调用 |
| 本地文件系统 | Token 本机 0600 保存；营养目录 JSON 读写 |
| 托管 Python 运行时 | 纯标准库脚本零依赖运行 |
| 任务确认交互 | 下单前购物车二次确认、支付交还家长本人 |

## 五、业务价值

- **家长侧**：把「带娃吃麦当劳」从碰运气变成有数据支撑的决策——按年龄钠参考值量化每餐风险，过敏原与辣度显式标记，不编造缺失数据。
- **开发者侧**：展示了 MCP 在「查询 → 核实 → 决策 → 交易」完整业务链路上的落地范式，含解析容错（Markdown 包装层）、降级策略（休息门店切换）等真实工程细节。
