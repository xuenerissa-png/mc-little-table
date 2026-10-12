# 参赛声明（CONTEST DECLARATION）

**参赛项目**：麦麦亲子小饭桌 McLittle Table
**参赛者 GitHub 账号**：xuenerissa-png
**参赛活动**：麦当劳程序员创意开发大赛（2026-10-09 至 2026-10-25，北京时间）

---

## 一、原创性声明

1. 本项目（含 `SKILL.md`、`scripts/`、`tests/`、文档及配置示例）为参赛者**原创成果**，参赛者对其拥有合法的著作权与处分权。
2. 本项目不侵犯任何第三方的知识产权、隐私权、商业秘密或其他合法权益，亦不违反参赛者与任何第三方的在先合同约定。
3. 本项目仅调用麦当劳官方提供的 MCP Server（`https://mcp.mcd.cn`）获取公开的餐品营养与门店数据，未抓取、未存储、未再分发任何麦当劳 proprietary 数据。
4. 因本项目内容引发的任何纠纷、投诉、索赔或法律责任，由参赛者自行承担。

## 二、合规性声明

1. 本项目内容符合中华人民共和国相关法律法规及平台规则，不含违反国家尊严/利益、妨碍社会安定、违背公序良俗的内容。
2. 本项目不含侮辱、诋毁、讽刺、贬低麦当劳品牌、产品及形象的内容，也未将麦当劳品牌与其他品牌进行对比。
3. 本项目**不包含任何恶意脚本、钓鱼链接、违规内容、病毒或恶意命令**；所有源代码均可公开审查：
   - `scripts/mclittle.py`：MCP 客户端与营养解析（仅使用 Python 标准库）
   - `scripts/meal_planner.py`：整餐搭配算法（仅使用 Python 标准库）
   - `scripts/token_settings.py`：本地 Token 配置页（仅监听 127.0.0.1，文件权限 0600）
   - `tests/`：离线单元测试
4. 本项目不宣扬不健康饮食方式；恰恰相反，其核心设计目标是帮助家长**控制儿童钠摄入**（对照权威膳食指南参考值）、规避过敏原与辣味风险，并将所有营养与安全的不确定项显式标记为「待确认」，不编造数据、不夸大宣传。

## 三、敏感信息声明

1. 本仓库**不包含**任何真实 MCP Token、密码、个人身份信息或私密配置。
2. `mcp-config.example.json` 仅使用环境变量占位符（`${MCD_MCP_TOKEN}`）；真实 Token 仅保存在参赛者本机（`~/.config/mc-little-table/token`，权限 0600），不进入版本库。
3. `token_settings.py` 的本地配置页仅绑定 `127.0.0.1` 回环地址，不记录任何请求日志，不向任何第三方传输 Token。
4. 仓库历史与文档中均不含参赛者的手机号、收货地址等个人信息。

## 四、真实性声明

1. 本项目真实使用麦当劳 MCP 能力：已通过 `initialize` / `tools/list` / `tools/call` 完成 `list-nutrition-foods`（160 条餐品数据）、`query-nearby-stores`、`query-meals`、`calculate-price`、`create-order` 等工具的真实联调（详见 `MCP_INTEGRATION.md` 与 `workbuddy.md`）。
2. 本项目真实运行于腾讯 WorkBuddy 智能体环境（用户级 Skill + WorkBuddy MCP 配置），详见 `workbuddy.md`。

参赛者：xuenerissa-png
声明日期：2026-10-13
