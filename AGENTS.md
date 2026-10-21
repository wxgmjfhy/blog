# AGENTS.md

Hugo 博客，手写模板，部署在 Cloudflare Pages（<https://wxgmjfhy-blog.pages.dev/>）。

## 规则

- **只编辑 `src/`**。`content/` 由 `scripts/mathprep.py` 生成并 gitignore，手改会丢。
- **改完 `src/` 必须跑 `python3 scripts/mathprep.py`**，否则构建用的是旧 `content/`——这是"改了没生效"最常见的原因。
- **公式一律单反斜杠**：`\mathrm` 正确，`\\mathrm` 会被 KaTeX 当成换行。
- **不升级 Hugo**（锁 0.147.0 extended）。模板依赖该版本 `.Fragments` 的形状。
- **不加 CDN**：KaTeX 与字体全部自托管。也不要引入 TsangerJinKai02（商用授权）。
- 提交身份：`git -c user.name=wxgmjfhy -c user.email=3281412030@qq.com commit`

## 命令

```bash
export PATH="$HOME/.local/bin:$PATH"   # hugo 在用户目录
make dev     # :1313，含草稿
make build   # 预处理 + 生成 public/
```

停本地服务用 `pkill -f "[h]ugo server"`；写成 `"hugo server"` 会把执行它的 shell 一起杀掉。

## 内容约定

- 文件名即 URL：`src/notes/foo.md` → `/notes/foo/`。
- 每个栏目的 `_index.md` **必须写 `title`**，否则 Hugo 按目录名生成英文标题（`Notes`）。
- 列表卡片 = 日期 + 标题 + 可选 `description`；**故意没有 `.Summary` 兜底**，笔记不填 description 就只显示日期和标题。
- 文章页 meta 只有 `日期 · N 字`。标签、阅读时间、关键词都是**用户明确要求移除的**，不要加回来。
- 首页只列笔记；无 hero 文案。RSS 直接链 `/index.xml`，没有订阅页。
- front matter 的 `keywords` 目前不渲染。

## 公式陷阱

| 写法 | 后果 |
|---|---|
| `$\\mathrm{x}$` | `\\` 是 KaTeX 换行，渲染出字面 `mathrmx` |
| `$a @ b$` | `@` 无运算符间距，紧贴两侧；用 `\;@\;` |
| 行内 `\dfrac` | 撑开行距；全篇统一 `\frac` |
| `\Theta(\min(d, M/d))` 里写 `\frac` | 括号不跟着长高；必须配 `\left( \right)` |
| 段落下方单独一行 `-` | 被解析成 setext 标题 |

多行 `$$` 与公式里的 `<`、`&` 由 `mathprep.py` 处理（套 `<div class="math-display">` + 转义），细节见脚本 docstring。不要绕过它手写 `content/`。

## 验证

结论要来自解析 HTML，截图只用来判断好不好看。

```bash
python3 scripts/mathprep.py >/dev/null && hugo --gc --minify --quiet
python3 -c "
import pathlib; s = pathlib.Path('public/notes/ai-infra-inference/index.html').read_text()
print('\$', s.count('\$'), 'table', s.count('<table'), 'empty-pre', s.count('<pre><code class=\"\">'))"
```

**`class="katex"` 只存在于渲染后的 DOM**，静态文件里数不到。要断言渲染结果必须用浏览器：

```bash
CHROME="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"   # WSL
timeout 200 "$CHROME" --headless=new --disable-gpu --no-sandbox --user-data-dir='C:\Users\SIMON\AppData\Local\Temp\p1' \
  --virtual-time-budget=45000 --dump-dom URL > /tmp/x.html
```

截图命令要跑 30–60 秒，单独执行，别和 build/commit 串在一起。curl 需要 `--noproxy '*'`。

## 部署

推 `main` → GitHub Actions（`mathprep` → `hugo` → `wrangler pages deploy`）。
项目 `wxgmjfhy-blog`，Account ID `90aa8e7a1dcd7e1db72ab24882965716`，
Secrets `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID`。回滚用 `git revert`。

Cloudflare 默认给 HTML 缓存 7 天，`static/_headers` 已覆盖（HTML 不缓存，`/css` `/fonts` `/katex` immutable）。怀疑内容不是新的，先看 `curl -sI` 的 `cf-cache-status` 与 `age`。

## 不要重新讨论的决定

- 手写模板而非 PaperMod；`src/` → `content/` 预处理不是多余步骤。
- 代码块浅纸底 + 语言名 + Copy，**没有红黄绿圆点**；标题靠左侧竖线分层。
- 表格只用发丝横线；滚动由 `scripts.html` 的 JS 包 `.table-scroll`（Hugo 0.147 下 `render-table.html` 的 `{{ .T }}` 不可用）。
- 关于页只留 GitHub / Codeforces。
- 迁入的笔记与题解保持原文逐字一致，只做经确认的排版改动。
