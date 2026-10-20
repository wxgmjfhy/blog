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

Cloudflare Pages，构建命令 `make build`，输出目录 `public`。

首次配置时需要设置环境变量：

```
HUGO_VERSION = 0.147.0
```

本地用 `wrangler` 直接部署：

```bash
make build
npx wrangler pages deploy public --project-name=wxgmjfhy-blog
```

## 设计来源

排版仿 [Kami](https://github.com/tw93/Kami)：暖白纸面（`#f5f4ed`）、墨蓝单色强调
（`#1B365D`）、衬线字体主导的层级、极细的分隔线，不用阴影和渐变。
