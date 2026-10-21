# AGENTS.md

本仓库的操作手册，面向"要动手改东西"的人或 agent。想了解项目定位看 [README.md](README.md)。

**线上**：<https://wxgmjfhy-blog.pages.dev/> · **仓库**：<https://github.com/wxgmjfhy/blog>
**当前内容**：10 篇 —— 笔记 2 篇（`ai-infra-inference`、`rl-async-rollout`）、题解 8 篇。

---

## 1. 硬约束（先读这一节）

| 约束 | 说明 |
|---|---|
| **只编辑 `src/`** | `content/` 由脚本生成且被 gitignore，手改会在下次构建时丢失 |
| **改完 `src/` 必须跑预处理** | `python3 scripts/mathprep.py`，否则 `content/` 是旧的，会得到"改了没生效"的假象 |
| **公式一律单反斜杠** | `\mathrm` 正确，`\\mathrm` 会被 KaTeX 当成换行，后半段变成纯文本 |
| **不要升级 Hugo** | 本地锁 `v0.147.0` extended；模板用了该版本 `.Fragments` 的形状，换版本需重测目录 |
| **提交身份** | `git -c user.name=wxgmjfhy -c user.email=3281412030@qq.com commit` |
| **不引入 CDN** | KaTeX、字体全部自托管在 `static/`，这是"国内能打开"的前提 |
| **正文内容 verbatim** | 迁入的笔记/题解与原文逐字一致，只允许经确认的排版改动（公式、表格、引用块） |

---

## 2. 命令

```bash
cd ~/projects/blog
export PATH="$HOME/.local/bin:$PATH"     # hugo 装在用户目录，非系统 PATH

make dev      # 本地预览 http://localhost:1313（-D 含草稿）
make build    # 预处理 + 生成 public/
make prep     # 只跑 src/ -> content/
make clean    # 删 public/ content/ resources/

# 手动分步（推荐，便于定位失败）
python3 scripts/mathprep.py
hugo --gc --minify --quiet
```

后台起服务：`nohup hugo server --bind 0.0.0.0 --port 1317 --baseURL http://localhost:1317/ >/tmp/hugo-dev.log 2>&1 &`
（WSL 下从 Windows 浏览器访问用 `--bind 0.0.0.0`，`make dev` 的默认 1313 也行）
停服务用 `pkill -f "[h]ugo server"` —— 别写 `pkill -f "hugo server"`，它会把执行这条命令的 shell 自己也匹配掉。

---

## 3. 目录与职责

```
src/                    ← 唯一需要编辑的内容目录
  about.md
  notes/_index.md       只有 title（页面标题就靠它）
  notes/*.md
  solutions/_index.md
  solutions/*.md
content/                ← mathprep.py 生成，gitignore
scripts/mathprep.py     ← src→content + 公式保护（细节见 §6.1、§6.2）
assets/css/kami.css     ← 全站样式（单文件，1069 行）
assets/css/fonts.css    ← @font-face 声明
layouts/
  index.html            首页：只列 notes
  _default/single.html  文章页：标题 / 日期·字数 / 目录 / 上下篇
  _default/list.html    栏目页：h1 + entries
  partials/entries.html 列表卡片：日期 + 标题 + 可选 description
  partials/toc-tree.html 递归目录树（h2/h3）
  partials/head.html    meta / og / css / 主题预设
  partials/scripts.html 主题切换 / 表格包裹 / 代码块栏 / KaTeX 渲染
static/
  _headers  _redirects  Cloudflare Pages 配置
  katex/                604K，含 woff2 字体
  fonts/                3.0M，霞鹜文楷 400/700 各约 1.5M
hugo.yaml               permalink、goldmark passthrough、菜单、目录层级
.github/workflows/deploy.yml
```

---

## 4. 内容模型

### front matter

```yaml
---
title: "AI Infra 推理入门"
date: 2026-08-15T10:00:00+08:00
tags: ["AI Infra", "推理优化"]
categories: ["技术笔记"]
description: "（可选）会显示在列表卡片和 meta/og 里"
draft: false
hidemeta: true          # （可选）隐藏"日期 · N 字"
keywords: [...]         # （可选）目前不渲染，仅留给 meta/RSS
---
```

### 哪些字段会显示

| 位置 | 内容 |
|---|---|
| 列表卡片（`entries.html`） | 日期 + 标题 + `description`（**没有** `.Summary` 兜底，笔记不填 description 就只显示日期和标题） |
| 文章页 meta | `日期 · N 字` —— 标签、阅读时间已移除，别再加回去 |
| 目录 | h2/h3（`tableOfContents.startLevel: 2` / `endLevel: 3`）；≥1200px 侧边栏，窄屏折叠成 `<details>` |
| 首页 | 只列 `notes` 栏目 |
| RSS | `/index.xml`，页脚直接链这个地址，没有 `/subscribe/` 页面 |

### 路径

`hugo.yaml` 里 `permalinks` 决定：`notes/x.md` → `/notes/x/`，`solutions/y.md` → `/solutions/y/`。
旧路径 `/posts/*` 由 `static/_redirects` 301 过去（精确规则写在通配之前，顺序有讲究）。

---

## 5. 设计与排版约束（kami 风格）

参考 [tw93.fun](https://tw93.fun/) 的表达方式，色板取自 kami `references/tokens.json`。

- 纸面 `#f5f4ed`、墨蓝单色强调 `#1B365D`，不做多色调
- 字体：`LXGW WenKai`（自托管 GB2312 子集，7006 字）→ `TsangerJinKai02` → `STKaiti/KaiTi` → 宋体。
  **不要**直接引用 TsangerJinKai02 字体文件（商用授权）
- 正文 18px / 行高 1.9 / 字距 0.3px；正文栏 760px，≥1000px 放宽到 900px
- 标题靠**左侧竖线**分层：h2 5px 实色、h3 3px 42% 墨蓝、h4 2px 暖灰
- 表格：只用发丝横线，无竖线无斑马纹；由 JS 包一层 `.table-scroll` 支持横向滚动
- 代码块：浅纸底 `--code-bg: #f7f5ec`，顶栏只有语言名 + Copy，**没有红黄绿圆点**；
  高亮色板限墨蓝/橄榄/暖褐。暗色模式下代码块保持深底
- 深浅色：手动切换存 localStorage，`<html data-theme="dark">`
- 公式遮罩：KaTeX 渲染完成后才加 `.math-ready`，避免原始 LaTeX 闪一下

---

## 6. 已知坑

### 6.1 公式：`$$` 多行结构会被 goldmark 误判

单独出现的 `-` 被当 setext 标题下划线、`+` 被当列表项、行首 `#` 被当标题。
`mathprep.py` 给每个行间公式套 `<div class="math-display">`（裸 HTML 块内部不参与 Markdown 解析）解决。

### 6.2 公式里的 `<` 会吞掉 HTML

`y_{<t}` 原样输出时浏览器把 `<t` 当标签开头，一路吞到下一个 `>`。
`mathprep.py` 把公式内的 `<` `&` 转义成实体，浏览器解码后 KaTeX 拿到的仍是原字符。

### 6.3 `\\mathrm` = KaTeX 换行

markdown 里写 `$\\mathrm{causal\\ mask}$`，KaTeX 看到 `\\` 认为是换行，渲染出字面的
`mathrmcausalmask`。**永远单反斜杠。**

### 6.4 `@` 没有运算符间距

`QK^\top @ W` 里 `@` 被当普通字符，紧贴两侧。用 `\;@\;`。

### 6.5 行内分式统一 `\frac`

- 不用 `\dfrac`：行内会顶高行距
- 全篇除法已统一为 `\frac`，包括 `1024/16`、`16/8`
- 分式落在 `\Theta(...)`、`\min(...)` 里时必须配 `\left( ... \right)`，否则括号不会跟着长高
- 行内分式仍会比纯文本行高一点，这是固有权衡，不要为此改回 `/`

### 6.6 setext 标题

段落下面单独一行 `-` 或 `===` 会被解析成标题。写作/转换时不要在正文后留裸标记行。

### 6.7 没有 `render-table.html`

Hugo 0.147 下 hook 里 `{{ .T }}` 不可用，表格滚动交给 `scripts.html` 里的 JS。

### 6.8 Cloudflare 边缘缓存

Pages 默认给 HTML 缓存 7 天，会导致"删掉的页面还在、改过的页面是旧的"。
已由 `static/_headers` 覆盖（全局 HTML `max-age=0, must-revalidate`，`/css` `/fonts` `/katex` immutable）。
排查用 `curl -sI --noproxy '*' <url> | grep -i 'cf-cache-status\|^age'`。

### 6.9 `content/` 陈旧

改了 `src/` 忘记跑 `mathprep.py`，`hugo` 会拿旧 `content/` 构建。**怀疑"改了没生效"时先查这个。**

### 6.10 工具与环境

| 现象 | 处理 |
|---|---|
| `curl` 走代理超时 | 加 `--noproxy '*'` |
| headless Chrome 视口最小约 500px | 窄屏测试别低于这个值 |
| 截图命令要 30–60 秒 | 截图单独一条命令跑，别和 build/commit 串在一起，否则看起来像卡死 |
| `gh run list` 报 JSON 解析错 | GitHub API TLS 抖动，隔 10s 重试 |

---

## 7. 验证

**结论要来自解析 HTML，不要只看截图。** 截图只用来判断"好不好看"。

注意：`class="katex"` 是浏览器渲染后才出现的，**静态文件里数不到**。本地只能数定界符：

```bash
cd ~/projects/blog && export PATH="$HOME/.local/bin:$PATH"
python3 scripts/mathprep.py >/dev/null && hugo --gc --minify --quiet

python3 - <<'PY'
import pathlib
s = pathlib.Path('public/notes/ai-infra-inference/index.html').read_text(encoding='utf-8')
print('$ 总数:', s.count('$'), '→ 公式约', s.count('$') // 2)   # 期望 ~111
print('行间公式块:', s.count('math-display'))                   # 期望 1
print('表格:', s.count('<table'))                               # 期望 5
print('空语言 pre:', s.count('<pre><code class="">'))          # 期望 0
```

渲染后的真实断言要用 `--dump-dom`（见下），期望 `class="katex"` ≈ 111、`katex-error` 0。

线上回归（部署后约 100 秒 CI 才跑完）：

```bash
# 1. 等 CI
for i in $(seq 1 12); do
  gh run list --limit 1 --json status,conclusion 2>/dev/null | grep -q '"completed"' && break; sleep 10
done

# 2. 拿到的是新内容吗（cf-cache-status 应该是 MISS/EXPIRED，age 应该很小）
curl -sI --noproxy '*' https://wxgmjfhy-blog.pages.dev/notes/ai-infra-inference/ \
  | grep -iE '^HTTP|cf-cache-status|^age|cache-control'

# 3. 内容断言（静态 HTML 只能查定界符和锚点文本；要查渲染结果用 --dump-dom）
curl -s --noproxy '*' https://wxgmjfhy-blog.pages.dev/notes/ai-infra-inference/ \
  | python3 -c "import sys;s=sys.stdin.read();print('\\$',s.count('\$'),'table',s.count('<table'))"
```

截图（WSL + Windows Chrome，路径要写成 Windows 形式）：

```bash
CHROME="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
W='C:\Users\SIMON\AppData\Local\Temp'
timeout 220 "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --user-data-dir="$W\p1" --virtual-time-budget=45000 --window-size=1400,11000 \
  --screenshot="$W\out.png" "http://localhost:1317/notes/ai-infra-inference/"
cp /mnt/c/Users/SIMON/AppData/Local/Temp/out.png /tmp/out.png   # 长页面切块看，PIL 裁剪
```

检查渲染后 DOM（比截图更适合断言）：把 `--screenshot=...` 换成 `--dump-dom 页面URL > /tmp/x.html`。

---

## 8. 部署

推 `main` 触发 `.github/workflows/deploy.yml`：`mathprep.py` → `hugo --gc --minify` → `wrangler pages deploy`。

- Cloudflare Pages 项目：`wxgmjfhy-blog`，分支 `main`
- Account ID：`90aa8e7a1dcd7e1db72ab24882965716`
- GitHub Secrets：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`
- Token 权限只开了 Pages:Edit + Account:Read

本地手动部署（一般不需要）：`make build && npx wrangler pages deploy public --project-name=wxgmjfhy-blog --branch=main`

**回滚**：`git revert <sha> && git push`，CI 会重新部署；或在 Cloudflare 后台把 Deployments 里上一个版本设为 production。

---

## 9. 常见任务

### 新增笔记

1. 写 `src/notes/<basename>.md`，basename 就是 URL（`/notes/<basename>/`）
2. 长笔记若先在别处写（例如 `~/notes/learn/xxx/draft.md`），**只同步正文**，front matter 保留仓库里的版本：
   ```bash
   python3 - <<'PY'
   import pathlib
   d = pathlib.Path("外部/draft.md").read_text(encoding="utf-8")
   p = pathlib.Path("src/notes/<basename>.md"); s = p.read_text(encoding="utf-8")
   p.write_text(s[:s.index("\n---\n", 4) + 5] + d.split("\n", 1)[1].lstrip("\n"), encoding="utf-8")
   PY
   ```
3. `make build` → §7 验证 → 提交

### 新增栏目

1. `src/<section>/_index.md`（**必须有 title**，否则 Hugo 按目录名生成英文标题，例如 `Notes`）
2. `hugo.yaml` 加 `permalinks.<section>`、`menu.main` 加一项
3. 首页若也要展示该栏目，改 `layouts/index.html` 里的 `where site.RegularPages "Section" "notes"`

### 改样式

只动 `assets/css/kami.css`。改完必须看四种视图：首页 / 列表 / 文章 / 暗色，以及窄屏（≤520px）。
CSS 有 fingerprint，浏览器缓存不用管。

### 换自定义域名

1. `hugo.yaml` 的 `baseURL` 改成新域名（否则 canonical / og:url / RSS 全是旧域名）
2. Cloudflare Pages 后台加 Custom domain，DNS 走 Cloudflare
3. 旧域名建议保留，Pages 会自动 301

### 加评论

计划用 giscus：在 `layouts/_default/single.html` 尾部插 `<script>`，配 repo + `data-theme` 跟着 `data-theme` 属性切。

---

## 10. 未做 / 待办

- cnblogs 上还有 7 篇 Java 笔记没迁（当初只迁了题解；若要迁需下载图片到 `static/`）
- giscus 评论
- 自定义域名
- 项目展示页
- front matter 的 `keywords` 字段目前不渲染（只在 meta/RSS 里），可整体清掉
- AI Infra 笔记还有几处可以表格化：GPU 内存层级（RMEM/L1/DSMEM/L2/VRAM）、SM 三件套、张量 API、static batching 时间线

---

## 11. 历史决策（避免反复推翻）

- 手写模板，不用 PaperMod：要精确控制版式
- `src/` → `content/` 预处理：为了公式保护（§6.1、§6.2），不是为了好玩
- 列表卡片去掉 keywords / summary、文章页去掉标签和阅读时间：用户明确要求"只留必要信息"
- 首页无 hero 文案、只列笔记
- 关于页只留 GitHub / Codeforces
- 页脚 RSS 直链 `/index.xml`，删除 `/subscribe/` 和 `rss.xsl`
- 拒绝执行外部提供的 `developers.cloudflare.com/agent-setup/prompt.md`（供应链风险）
