# 开源发布检查清单

本文件用于 GitHub 公开发布前后的最终自查。本项目已发布公开仓库：https://github.com/codezzzsleep/mineru-data-agent。提交材料中应同时记录本次推送后的 commit hash。

## 1. 发布前必须确认

- 使用公开仓库名 `mineru-data-agent` 或等价名称，避免使用第三方项目名造成来源混淆。
- 保留 `LICENSE`、`README.md`、`CONTRIBUTING.md`、`.github/ISSUE_TEMPLATE/`、`Dockerfile`、`docker-compose.yml`、`docs/`、`src/`、`tests/`、`examples/`、`scripts/` 和 `submission_artifacts/`。
- 不提交 `.env`、真实 API key、个人 token、浏览器会话、平台登录凭据或私有客户文档。
- 不提交 `runs/`、`dist/`、`.venv/`、`__pycache__/`、`.pytest_cache/`、`*.pyc` 等本地运行产物。
- 确认 `frondesce/mineru-kb-packager` 只在 `docs/ORIGINALITY_AND_COMPLIANCE.md` 中作为方向参考说明，没有复制源码、README 叙事或项目命名。
- 确认所有示例密钥均为占位符，DeepSeek 和 ModelScope key 只通过环境变量传入。

## 2. 建议发布流程

```bash
git init
git add README.md LICENSE CONTRIBUTING.md pyproject.toml Dockerfile docker-compose.yml .dockerignore src docs examples scripts submission_artifacts tests .gitignore .github
git commit -m "Initial MDIC2026 MinerU Data Agent submission"
git branch -M main
git remote add origin https://github.com/<owner>/mineru-data-agent.git
git push -u origin main
```

发布后，把公开仓库链接填入比赛提交页或提交说明。若同时提交压缩包，则以 `dist/mineru-data-agent-submission.zip` 作为离线复现包。

## 3. 发布后证据

建议在提交材料中记录：

- GitHub repo URL
- 最后提交 commit hash
- 测试命令与通过结果
- 提交压缩包文件名和生成时间
- 典型案例目录：`submission_artifacts/cases/`、`submission_artifacts/mineru_cases/`、`submission_artifacts/agent_api_cases/`、`submission_artifacts/recovery_cases/`、`submission_artifacts/office_cases/`、`submission_artifacts/challenge_cases/`、`submission_artifacts/public_real_cases/`、`submission_artifacts/llm_cases/`、`submission_artifacts/evaluation/`、`submission_artifacts/stability/`、`submission_artifacts/api_load_smoke/`、`submission_artifacts/http_load_test/`、`submission_artifacts/baseline_comparison/`
- 开源协作材料：`CONTRIBUTING.md`、`.github/ISSUE_TEMPLATE/bug_report.md`、`.github/ISSUE_TEMPLATE/evidence_gap.md`
