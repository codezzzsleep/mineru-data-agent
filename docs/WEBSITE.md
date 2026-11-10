# 项目展示页

公开地址：https://codezzzsleep.github.io/mineru-data-agent/

`site/` 是无需构建的静态项目页，HTML、CSS 和原生 JavaScript 均在仓库内维护。使用相对资源路径，兼容 GitHub Pages 的仓库子目录。

## 内容与来源

- 获奖信息来自 [MDIC 2026 官方名单](https://mineru.net/MDIC2026/competition)：YCYC 团队，智能进化 · Agent 能力评测赛道三等奖。
- 142 本资料、3 万余页为决赛答辩中的应用场景规模。
- 演示视频取自决赛 PPT 中的 19 秒 GIF，是答辩用界面流程示意；公开执行证据另行链接到 `submission_artifacts/`。
- 17 个案例、45 个标注字段来自 `submission_artifacts/evaluation/evaluation_metrics.json`；180 项测试为决赛版本开源发布时的验证结果。
- 页面采用与 MinerU 获奖页相近的黑色、金色与暖白配色。图标及文档流程插图为本项目绘制，未复制官网图片。
- README 的信息组织参考 OnCue 和 gosim26-agentic-observer：定位、获奖、演示、使用、原理、证据与文档。

## 本地预览

```bash
python -m http.server 8000 --directory site
```

访问 `http://localhost:8000`。移动导航、工作流程页签、视频播放和命令复制均在浏览器内运行，不调用模型或解析 API。

## 发布

GitHub Pages 从 `gh-pages` 分支根目录发布。与 OnCue、gosim26-agentic-observer 相同，使用已提交的 `site/` 子树，正常推送，保留部署历史。

```bash
git add site README.md docs scripts/publish_pages.sh
git commit -m "Update project website"
bash scripts/publish_pages.sh --dry-run
bash scripts/publish_pages.sh
```

首次发布后，将仓库 Pages 设置为 `gh-pages` 分支根目录。页面只发布 `site/` 中的静态文件。API 凭据、本地设置、原始答辩包和运行数据均不属于展示页资源。

## 验证

[浏览器验证记录](website-verification.json)：320、390、768、1024、1440、1920 六种宽度均无页面横向溢出。四个流程页签、键盘切换、手机导航、视频播放与命令复制通过，未发现 JavaScript 错误或资源加载错误。README 与页面的 36 个本地链接已检查，24 个产品源码哈希仍与答辩版本一致。
