# 麦麦亲子小饭桌 McLittle Table

面向 **1–12 岁**孩子的家长，按年龄对照每日钠参考值，使用麦当劳官方 MCP 营养数据辅助选餐。不以营销为目标，不声称营养数据覆盖所有门店商品。

## 🍟 Token 配置页面（新增）

在本机运行：

```bash
python3 scripts/token_settings.py
```

浏览器会自动打开本地配置页面。粘贴麦当劳 MCP Token，点击「保存到本机」。Token 存储在 `~/.config/mc-little-table/token`（文件权限 `0600`），后续运行 CLI 自动读取。可随时在页面删除。**请勿把 Token 发到聊天中，也不要把本机 token 文件打包分享。**

如果已设置 `MCD_MCP_TOKEN` 环境变量，则优先使用环境变量。WorkBuddy 自身的 MCP 连接仍需按 `mcp-config.example.json` 在 WorkBuddy 中单独配置；此页面只配置随包提供的 Python 客户端，不会自动修改 WorkBuddy 的连接设置。

## 安装

将本文件夹放入支持 `SKILL.md` 的 Skill 目录（WorkBuddy：`~/.workbuddy/skills/mc-little-table/`）。WorkBuddy MCP 配置可参考 `mcp-config.example.json`（仅含环境变量占位符 `${MCD_MCP_TOKEN}`），**在本机**替换为自己的 Token；不要提交真实配置到 Git。

## 目标用户

- 1–12 岁孩子的家长：想在外出就餐时快速做出少钠、避开过敏原与辣味的选择
- 智能体/Skill 开发者：参考基于麦当劳 MCP 的完整「查询 → 核实 → 决策 → 下单」落地范式

本地 CLI（Python 3.9+，无第三方依赖）：

```bash
export MCD_MCP_TOKEN='在本机填写你的token'
python3 scripts/mclittle.py tools
python3 scripts/mclittle.py nutrition --age 3 --meal-budget 350 --top 10 --save nutrition.json
python3 scripts/mclittle.py compare --file nutrition.json --age 3 --from-name '餐品A' --to-name '餐品B'
```

`nutrition` 查询 `list-nutrition-foods`，解析官方 toon 紧凑格式，并按单品钠含量从低到高排序。它**不是自动生成完整套餐**；最终推荐需由宿主 Skill 综合核对门店菜单、过敏原、进食安全等信息。

查询门店菜单/详情：先 `tools` 查看当前服务器参数定义，然后：

```bash
python3 scripts/mclittle.py call query-meals --args '{"storeCode":"请填真实门店编码","orderType":1,"beType":1}'
```

实际参数以 `tools/list` 返回 schema 为准。若 `query-meals` 不接受上述示例参数，请按真实 schema 调整。

## 安全与局限

- 每日钠参考：美国 2025–2030 膳食指南，1–3 岁 <1200mg；4–8 岁 <1500mg；9–12 岁 <1800mg（原分组为 9–13）。不代表中国标准或每餐限额。
- 无法仅从名称验证“不辣”、过敏原、交叉接触或幼儿呛噎风险。
- MCP 营养数据与门店菜单没有保证一致的 productCode；匹配必须人工/模型谨慎核实。
- 不保证套餐可修改；不会自动下单。
- 未持有用户 Token，**未进行真实 MCP 联调**；离线单元测试覆盖解析、年龄、筛选、比较。

官方 MCP：https://github.com/M-China/mcd-mcp-server

钠参考：https://content.govdelivery.com/attachments/AKDEED/2026/01/09/file_attachments/3515584/DGA.pdf

## v0.3：真正的整餐搭配算法

新增 `scripts/meal_planner.py`，按 **主食 + 可选配菜 + 饮品** 组合，输出至多三套差异化方案（少钠、蛋白质、轻量），整餐累加钠/能量/蛋白质；可设置本餐钠预算并比较同类别替换。

先通过 MCP 查询真实门店菜单和营养资料，并人工/AI 审核后整理为 `verified_catalog.json`：

```json
{"items": [
  {"id":"verified-item-1","name":"实际餐品名称","role":"main",
   "available":true,"nutrition_verified":true,
   "sodium_mg":180,"energy_kcal":200,"protein_g":10,
   "allergens_verified":true,"allergens":[],"spicy":false,
   "texture_checked":true,"age_min":3,"age_max":12}
]}
```

**上面数字仅是字段格式示例，不是任何麦当劳餐品的真实数据。** `available` 应针对实际门店核实，`allergens_verified` 不能只靠名称推断，`texture_checked` 需要针对孩子年龄与进食能力判断。没有足够证据时不要填 `true`。

```bash
python3 scripts/meal_planner.py --catalog verified_catalog.json --age 3.5 --meal-budget 350
python3 scripts/meal_planner.py --catalog verified_catalog.json --age 3.5 --swap mainA,drinkA mainA mainB
```

`--swap` 的第一项为当前组合 ID（英文逗号分隔），第二项为替换前 ID，第三项为替换后 ID。真实 MCP Token 仍由 `python3 scripts/token_settings.py` 的本地页面配置，或由环境变量提供。

## v0.5：优惠券与最优价格

```bash
# 券侦察 + 比价（只读）
python3 scripts/deals.py --store 1400116 --items 6102:1,3757:1,1450:1
# 输出：可领取券 / 卡包券 / 本门店可用券 / 基线价 vs 券后价 排行与节省金额

# 经家长明确同意后领取麦麦省可用券（会写入账户，终端二次确认）
python3 scripts/deals.py --store 1400116 --claim
```

- `query-store-coupons` 才是「本单可用」的判据；`query-my-coupons` 仅代表卡包资产，不校验门店/订单类型。
- 券通过 `couponId`/`couponCode` 挂在对应 `productCode` 上参与 `calculate-price`，自动比价选最省方案。
- 错误码 60006 = 餐品当前时段不可售（早餐时段菜单不同），需按当前菜单重新选品。

## v0.4：下单协助流程
组合确认后主动询问是否代下单：`query-meals` 取商品编码 → `calculate-price` 算价并二次确认 → `create-order`（orderType=1 必传 takeWayCode：eat-in 堂食 / locker-in 取餐柜）→ 呈现 `payH5Url` 交家长本人支付（约 15 分钟时限）。已实测全流程可用（2026-10 广州龙洞餐厅）。
另：`parse_toon` 已兼容官方返回的 Markdown 包装层（`## Original Response` 后定位 JSON）。

**当前限制：**算法与测试已经实现，但尚未接入自动的“菜单 + 营养 + 过敏原 + 质地”跨接口映射管线；需要宿主 AI 按 SKILL.md 核实后生成目录。未使用真实 Token 联调，因此不能宣称生成的方案已验证可在某家门店购买。
