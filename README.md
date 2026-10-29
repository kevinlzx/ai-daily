# 海外 AI 工具情报日报（自动流水线）

每天自动抓取海外 AI 工具与开发动态，中文化成日报，并渲染出知乎 / 公众号 /
小红书 / 知识星球 四个平台版本，供发布。

## 目录结构

    src/fetch.py      抓取（HN + Product Hunt + GitHub Trending，单源隔离、自动重试）
    src/generate.py   LLM 中文化成日报（Agnes 免费档模型，失败自动回退保留上次结果）
    src/publish.py    把日报渲染成 4 个平台版本
    output/           产物：daily.md + zhihu.md + gongzhonghao.md + xiaohongshu.md + planet.md
    data/raw.json     抓取到的原始数据

## 本地运行

    python -m src.fetch        # 抓取
    python -m src.generate     # 生成日报（读 data/raw.json，写 output/daily.md）
    python -m src.publish      # 分平台出稿

依赖只需 requests。API key 放环境变量 AGNES_API_KEY（默认从
%LOCALAPPDATA%/hermes/.env 读取）。

## 一键跑全流程

    python -m src.fetch && python -m src.generate && python -m src.publish

## 部署到 GitHub Actions 定时

1. 初始化并推仓库：

       git init
       git add .
       git commit -m init
       git remote add origin <你的仓库URL>
       git push -u origin main

2. 在仓库 Settings → Secrets and variables → Actions 里新增 secret：AGNES_API_KEY
3. 之后每天 22:00 UTC（北京时间 06:00）自动跑，产物提交回仓库。

## 发布建议

- 知乎 / 公众号 / 小红书：把对应平台 md 内容发布；可配合一键群发工具批量铺号。
- 知识星球：把 planet.md 作为「今日情报」免费发；深度测评、答疑、资源包需要你手动补，
  它是付费承接场所。
- 定价起步：免费日报引流 → 30 天后开 ¥99/年付费星球。

## 防坑

- 各源已做单源隔离 + 自动重试：HN / PH / GitHub 任一挂了，其余照常出稿。
- LLM 调用失败时自动回退到上一次成功的日报，保证每天都有内容。
- 别堆硬广、别搬运原文（本流程是翻译+改写，已规避）。
