#!/usr/bin/env python3
"""pre-commit 校验：content/posts/ 下暂存的文章是否符合 AGENTS.md 规范。"""
import re
import subprocess
import sys

REQUIRED = ("title", "date", "slug")
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
KV_RE = re.compile(r"^([\w-]+):\s*(.*)$")


def staged_files():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [f for f in out.splitlines()
            if f.startswith("content/posts/") and f.endswith(".md")]


def parse_front_matter(text):
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return None
    meta = {}
    for line in m.group(1).splitlines():
        kv = KV_RE.match(line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip().strip('"').strip("'")
    return meta


def check(path):
    errors = []
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        return [f"{path}: 无法读取（{e}）"]
    meta = parse_front_matter(text)
    if meta is None:
        return [f"{path}: 缺少 front matter（应通过 hugo new 生成）"]
    for key in REQUIRED:
        if not meta.get(key):
            errors.append(f"{path}: 缺少必填字段 {key}")
    stem = path.replace("\\", "/").rsplit("/", 1)[-1][:-3]
    if meta.get("slug") and meta["slug"] != stem:
        errors.append(f"{path}: slug({meta['slug']}) 必须等于文件名({stem})")
    if meta.get("draft") == "true" and meta.get("syndicate"):
        errors.append(f"{path}: draft:true 不得与 syndicate 同时出现（草稿不得同步）")
    return errors


def main():
    errors = []
    for path in staged_files():
        errors.extend(check(path))
    if errors:
        print("✗ 文章规范校验未通过（规范见 AGENTS.md）：")
        for e in errors:
            print("  -", e)
        print("修复后重新 git add 再提交。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
