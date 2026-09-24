#!/usr/bin/env python3
"""文章规范校验（规范见 AGENTS.md）。

用法：
  scripts/check_posts.py          校验暂存区中变更的文章（pre-commit 用）
  scripts/check_posts.py --all    校验 content/posts/ 全部文章（CI 用）
"""
import glob
import re
import subprocess
import sys
from datetime import datetime, timedelta

REQUIRED = ("title", "date", "slug")
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
KV_RE = re.compile(r"^([\w-]+):\s*(.*)$")
FUTURE_TOLERANCE = timedelta(minutes=15)


def staged_files():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [f for f in out.splitlines()
            if f.startswith("content/posts/") and f.endswith(".md")]


def all_files():
    return sorted(glob.glob("content/posts/*.md"))


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


def parse_date(value):
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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

    is_draft = meta.get("draft") == "true"
    if is_draft and meta.get("syndicate"):
        errors.append(f"{path}: draft:true 不得与 syndicate 同时出现（草稿不得同步）")
    if is_draft and meta.get("reviewed"):
        errors.append(f"{path}: draft 草稿不应带 reviewed（reviewed 是人工审核标记，发布时才加）")
    if not is_draft and meta.get("reviewed") != "true":
        errors.append(f"{path}: 非 draft 文章缺 reviewed: true —— 发布必须经人工审核，由人改 draft: false 并添加 reviewed: true")
    if not is_draft:
        dt = parse_date(meta.get("date", ""))
        if dt is None:
            errors.append(f"{path}: date 无法解析（{meta.get('date')}）")
        else:
            if dt.tzinfo is None:
                dt = dt.astimezone()
            if dt > datetime.now().astimezone() + FUTURE_TOLERANCE:
                errors.append(f"{path}: date({meta['date']}) 在未来 —— Hugo 默认不构建未来文章，会静默不上线")
    return errors


def main():
    check_all = "--all" in sys.argv[1:]
    paths = all_files() if check_all else staged_files()
    errors = []
    for path in paths:
        errors.extend(check(path))
    if errors:
        print("✗ 文章规范校验未通过（规范见 AGENTS.md）：")
        for e in errors:
            print("  -", e)
        print("修复后再提交/推送。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
