#!/usr/bin/env python3
"""把 src/ 下的 Markdown 同步到 content/，同时把数学公式保护起来。

要解决两个 goldmark 的坑：

1. **行间公式的块级结构被误判**
   Hugo(goldmark) 的 block passthrough 只对**单行** `$$...$$` 生效。多行公式会被
   当成普通段落解析，公式里单独出现的 `-`（减号）会被读成 setext 标题下划线、
   `+` 被读成无序列表项、行首 `#` 被读成标题。裸 HTML 块（CommonMark type 6）
   的内部文本不参与 Markdown 解析，所以在公式外套一个 `<div>` 即可。

2. **公式里的 `<` 破坏 HTML**
   形如 `y_{<t}` 的写法在 passthrough 之后是原样输出的，`<` 会被浏览器当成标签
   开头，一路吞到下一个 `>`，导致正文渲染错乱。因此公式内部的 `<` 与 `&` 需要
   转义成 HTML 实体——浏览器解码后 KaTeX 拿到的仍是原始字符。

除公式区域外，其余文本逐字符搬运。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DST = ROOT / "content"

OPEN = '<div class="math-display">'
CLOSE = "</div>"
D = "$$"


def esc(tex: str) -> str:
    """只转义会破坏 HTML 的两个字符。"""
    return tex.replace("&", "&amp;").replace("<", "&lt;")


def split_front_matter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    end = text.find("\n", end + 1)
    if end == -1:
        return text, ""
    return text[: end + 1], text[end + 1 :]


def esc_dollars(buf: str) -> str:
    """转义一段文本中 `$...$` 内部的内容，跳过反斜杠转义的 \\$。"""
    pieces: list[str] = []
    i = 0
    n = len(buf)
    while i < n:
        ch = buf[i]
        if ch == "\\" and i + 1 < n:
            pieces.append(buf[i : i + 2])
            i += 2
            continue
        if ch != "$":
            pieces.append(ch)
            i += 1
            continue
        j = i + 1
        while j < n:
            if buf[j] == "\\":
                j += 2
                continue
            if buf[j] == "$":
                break
            j += 1
        if j < n and j > i + 1:
            pieces.append("$" + esc(buf[i + 1 : j]) + "$")
            i = j + 1
        else:
            pieces.append(ch)
            i += 1
    return "".join(pieces)


def esc_inline(line: str) -> str:
    """转义一行中 `$...$` 内部的内容，`code span` 内原样保留。"""
    res: list[str] = []
    for idx, chunk in enumerate(line.split("`")):
        if idx > 0:
            res.append("`")
        res.append(chunk if idx % 2 == 1 else esc_dollars(chunk))
    return "".join(res)


def protect(text: str) -> str:
    head, body = split_front_matter(text)
    lines = body.splitlines(keepends=True)
    out: list[str] = [head] if head else []
    n = len(lines)
    i = 0
    in_fence = False
    fence_tok = ""

    def blank_before() -> None:
        if out and out[-1].strip():
            out.append("\n")

    def blank_after(idx: int) -> None:
        if idx < n and lines[idx].strip():
            out.append("\n")

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        # 围栏代码块原样保留
        if stripped.startswith("```") or stripped.startswith("~~~"):
            tok = stripped[:3]
            if not in_fence:
                in_fence, fence_tok = True, tok
            elif tok == fence_tok:
                in_fence = False
            out.append(raw)
            i += 1
            continue
        if in_fence:
            out.append(raw)
            i += 1
            continue

        # `$$` 独占一行：向下找配对
        if stripped == D:
            j = i + 1
            while j < n and lines[j].strip() != D:
                j += 1
            if j < n:
                blank_before()
                out.append(OPEN + "\n")
                out.append(D + "\n")
                for k in range(i + 1, j):
                    out.append(esc(lines[k]))
                out.append(D + "\n")
                out.append(CLOSE + "\n")
                blank_after(j + 1)
                i = j + 1
                continue

        # 单行 `$$ ... $$`
        elif stripped.startswith(D) and stripped.endswith(D) and len(stripped) > 4:
            inner = stripped[2:-2]
            blank_before()
            out.append(OPEN + "\n")
            out.append(D + esc(inner) + D + "\n")
            out.append(CLOSE + "\n")
            blank_after(i + 1)
            i += 1
            continue

        out.append(esc_inline(raw))
        i += 1

    return "".join(out)


def main() -> int:
    if not SRC.is_dir():
        print(f"error: 找不到源目录 {SRC}", file=sys.stderr)
        return 1

    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)

    count = 0
    for path in sorted(SRC.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(SRC)
        target = DST / rel
        target.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix.lower() in {".md", ".markdown"}:
            target.write_text(protect(path.read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copy2(path, target)
        count += 1

    print(f"mathprep: {count} 个文件 -> {DST.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
