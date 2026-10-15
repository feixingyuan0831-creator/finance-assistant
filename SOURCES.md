# 来源、许可证与发布版说明

打包日期：2026-10-15。上游固定版本由先前本地下载核验记录提供；这里列的是来源版本，不声称已验证其今天的全部运行环境。

| 模块 | 上游与固定提交 | 许可/改动 |
|---|---|---|
| 应急金、储蓄目标 | [openaccountant/skills](https://github.com/openaccountant/skills/tree/f5abe381f24b5b7d59f1d0b4a825b14494ff2034/personal) | MIT，Open Accountant；中文适配，去除账户连接和自动划款 |
| 预算 | [SkillMedev/skills](https://github.com/SkillMedev/skills/tree/6b3044d569595b481a3677da8f68af7aa239dc09/skills/budget-builder) | MIT，Alexander Ouellet；适配不规则收入和人民币 |
| 配置流程 | [henrywen98/asset-allocation](https://github.com/henrywen98/asset-allocation/tree/96507e725f950242586f05567fe4fac2d775265d) | MIT，Henry Wen；只保留研究流程，不打包/默认运行回测引擎 |
| 入口、规则、模板、月报、余额与同步工具、其他发布版内容 | Graduate Finance Skills contributors | MIT；原创整合与本地文件实现 |

上述改编文件的许可证和逐项来源在 `licenses/`，原作者版权保留。根LICENSE适用于原创内容，不替换第三方声明。

历史本地版本参考过 `belos-street/stock-analytics-skill`。其README用途限制与MIT文字存在冲突；本公开版本不分发其代码、原文、改编模块或许可证副本。对应六类研究说明从本产品需求独立编写，未复制该上游模块。此处仅披露历史来源，不主张得到该项目授权或背书。

Obsidian本地财务库的产品思路曾参考 `lovepigpanda/obsidian-personal-finance-tracker`；本仓库不分发其实现、示例账户或自动通知代码。Python同步器为独立实现，无Obsidian API依赖。

公共示例仅为人工合成测试数据；初始化金额留空。第三方商标仅用于兼容性说明。外部项目更新不自动进入本Skill，也不自动下载执行。
