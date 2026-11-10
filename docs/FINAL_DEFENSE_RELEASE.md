# 决赛答辩版本说明

本版本源自 `MinerU.zip` 中的 `MinerU/mineru-data-agent-submission/`，同步到 `codezzzsleep/mineru-data-agent`。

## 版本核对

全部 24 个产品 Python 源文件与答辩包一致，仅统一 CRLF/LF 换行。文件 SHA-256 见 [源码清单](final-defense-source-manifest.json)。版本包含交互式 `chat`、自动解析路由、细粒度升级规划、语料目录、渐进式资料包和逐本来源合并功能。

## 发布清理

真实 `.env`、本地工具配置、运行记录、记忆数据库、缓存、构建元数据和原始史料数据集均已排除。`.env.example` 只保留占位符。Git、Docker 与提交包过滤规则已同步补强。

除发布过滤规则外，调整了三处测试夹具，避免短模拟文本触发真实在线恢复，并显式配置模拟 token；修复了打包脚本在 Linux 下遗漏隐藏文件和改写自身路径规则的问题。产品源码保持答辩版本。

## 验证

- 180 个测试通过，包括提交包文件清单与敏感文件排除检查。
- CLI 单文件、批处理及 `chat` / `corpus package-sources` 入口检查通过。
- 发布文件及原有完整 Git 历史经过 Gitleaks 扫描；发布前再次检查暂存区和提交包。

公开文档中的来源信息及测试用的示例值保留，扫描报告不包含真实凭据值。
