# blog

个人博客。Hugo + 自写的 kami 风格模板，托管在 Cloudflare Pages。

线上地址：<https://wxgmjfhy-blog.pages.dev/>

## 目录结构

```
.
├── src/                        # 文章源文件（你要编辑的地方）
│   ├── about.md
│   └── posts/
│       ├── _index.md
│       └── rl-async-rollout.md
├── content/                    # 由 src/ 生成，不要手改（已在 .gitignore）
├── scripts/mathprep.py         # 预处理：保护公式，见下
├── assets/css/kami.css         # 全站样式
├── layouts/                    # 模板
├── static/
│   ├── katex/                  # KaTeX 本地托管（无 CDN 依赖）
│   └── favicon.svg
├── hugo.yaml
└── Makefile
```

## 日常使用

```bash
make dev      # 本地预览 http://localhost:1313（含草稿）
make build    # 生成 public/
```

新增文章：直接在 `src/posts/` 下建 `.md`，front matter 照抄现有文章的格式。

```markdown
---
title: "标题"
date: 2026-10-20T17:00:00+08:00
tags: ["标签"]
description: "一句话摘要，会显示在首页列表和 RSS 里"
---
```

草稿把 `draft: true` 写上就不发布。

## 为什么不直接编辑 content/

`src/` → `content/` 这一步由 `scripts/mathprep.py` 完成，它解决两个 goldmark 的坑：

**1. 多行行间公式会被当成 Markdown 结构解析**

Hugo 的 block passthrough 只对**单行** `$$...$$` 生效。多行公式里单独出现的 `-`
会被读成 setext 标题下划线、`+` 被读成无序列表、行首 `#` 被读成标题，整块公式碎掉。

脚本会给每个行间公式套一层 `<div class="math-display">`。裸 HTML 块的内部文本不
参与 Markdown 解析，所以 `-` `+` `#` 再也不会被误判。

**2. 公式里的 `<` 会破坏 HTML**

`y_{<t}` 这种写法在 passthrough 之后是原样输出的，浏览器的 HTML 解析器会把 `<t`
当成标签开头，一路吞到下一个 `>`，导致正文错乱、字数统计失真。脚本会把公式内的
`<` 与 `&` 转义成 HTML 实体，浏览器解码后 KaTeX 拿到的仍是原始字符。

所以：**永远编辑 `src/`，跑 `make`。**

## 数学公式

`$...$` 行内，`$$...$$` 行间，KaTeX 在浏览器端渲染。KaTeX 及其字体在
`static/katex/` 本地托管，不依赖任何 CDN，国内访问也不会卡。

## 部署

推送到 `main` 即自动部署：`.github/workflows/deploy.yml` 会跑 `mathprep` → `hugo` →
`wrangler pages deploy`，推到 Cloudflare Pages。

- 线上：<https://wxgmjfhy-blog.pages.dev/>
- 项目名：`wxgmjfhy-blog`
- Secrets：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`

本地手动部署（一般不需要）：

```bash
make build
npx wrangler pages deploy public --project-name=wxgmjfhy-blog --branch=main
```

本地凭据放在 `~/.cf-token` 与 `~/.cf-account`，用环境变量接入：

```bash
export CLOUDFLARE_API_TOKEN="$(cat ~/.cf-token)"
export CLOUDFLARE_ACCOUNT_ID="$(cat ~/.cf-account)"
```

## 设计

参考 [tw93.fun](https://tw93.fun/)（Kami 作者的博客）的网页化表达，色板取自 kami
`references/tokens.json`：

- 纸面 `#f5f4ed`、墨蓝单色强调 `#1B365D`，不做多色调
- 楷体主导：`TsangerJinKai02 → STKaiti → Kaiti SC → KaiTi → 楷体 → Songti SC`
- 正文 18px / 行高 1.9 / 字距 0.3px；正文栏 760px，≥1000px 时放宽到 900px
- 表格只用发丝线，无竖线、无斑马纹
- 代码块深色底 + 圆点标题栏 + 复制按钮
- 支持深浅色切换（默认浅色，跟随手动选择，存 localStorage）

字体说明：tw93 原版用商业字体 TsangerJinKai02，不能随站分发，因此退回系统楷体。
macOS 上是 STKaiti、Windows 上是 KaiTi、Linux/Android 会退到宋体或黑体。
若想让各平台完全一致，需要自托管开源楷体（如 LXGW 霞鹜文楷）并按 unicode-range
切片——注意 npm 上的 `lxgw-wenkai-*-webfont` 包实测存在子集与 CSS 声明不匹配的问题，
届时建议改用其它分发渠道再验证。
