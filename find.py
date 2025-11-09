#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawl_gitcode.py
爬取 OpenHarmony-TPC 组织下所有仓库（使用 GitCode Personal Access Token）
输出: openharmony_tpc_repos.csv, openharmony_tpc_repos.txt
"""

import os
import time
import argparse
import csv
import sys
from typing import List, Dict, Optional

import requests

ORG = "OpenHarmony-TPC"
API_BASE = f"https://api.gitcode.com/api/v5/orgs/{ORG}/repos"
# 每页请求数量（尽量大以减少翻页）
PER_PAGE = 100

# 请求超时
REQUEST_TIMEOUT = 20.0

def build_headers(token: Optional[str]) -> Dict[str, str]:
    headers = {
        "User-Agent": "gitcode-org-crawler/1.0 (+https://gitcode.com)",
        "Accept": "application/json",
    }
    if token:
        # 尝试用 Authorization: Bearer（推荐），如果失败可切换为 PRIVATE-TOKEN
        headers["Authorization"] = f"Bearer {token}"
    return headers

def fetch_page(page: int, headers: Dict[str,str], per_page: int=PER_PAGE) -> Optional[List[Dict]]:
    params = {"page": page, "per_page": per_page}
    try:
        r = requests.get(API_BASE, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        print(f"❌ 网络请求异常 page={page}: {e}")
        return None

    # 打印状态以便调试
    status = r.status_code
    ctype = r.headers.get("Content-Type", "")
    if status == 401:
        print(f"⚠️ 401 Unauthorized — 令牌无效或权限不足 (page={page})")
        return None
    if status == 403:
        print(f"⚠️ 403 Forbidden — 可能被限流或权限问题 (page={page})\n响应片段: {r.text[:400]}")
        return None
    if status == 429:
        # Too Many Requests
        print(f"⚠️ 429 Too Many Requests (page={page})")
        return None
    if status != 200:
        print(f"⚠️ 非预期 HTTP 状态码 {status} (page={page}), Content-Type={ctype}")
        # 打印前 400 字符帮助排查
        print(r.text[:400])
        return None

    # 尝试解析 JSON
    try:
        data = r.json()
    except Exception as e:
        print(f"❌ JSON 解析失败 page={page}: {e}")
        # 打印前 400 字符帮助排查
        print((r.text or "")[:400])
        return None

    # API 返回应该是列表
    if isinstance(data, list):
        return data
    # 某些情况下 API 返回包含 data 字段
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        return data["data"]
    print(f"⚠️ 返回结构不符合预期 (page={page}), 类型: {type(data)}")
    return None

def normalize_repo_item(item: Dict) -> Dict:
    """
    从API返回的 repo 项中提取我们关心的字段，返回字典保证字段都存在
    """
    # 常见字段：path_with_namespace / full_name / path / name / html_url
    path_with_namespace = item.get("path_with_namespace") or item.get("full_name") or item.get("path")
    # 有些返回使用 "html_url" 或 "web_url"
    html_url = item.get("html_url") or item.get("web_url")
    if not html_url and path_with_namespace:
        html_url = f"https://gitcode.com/{path_with_namespace}"

    return {
        "id": item.get("id"),
        "name": item.get("name") or (path_with_namespace.split("/")[-1] if path_with_namespace else None),
        "path_with_namespace": path_with_namespace,
        "html_url": html_url,
        "description": item.get("description") or "",
        "stars": item.get("stargazers_count") or item.get("star_count") or item.get("watchers_count") or 0,
        "forks": item.get("forks_count") or 0,
        "updated_at": item.get("updated_at") or item.get("last_activity_at") or "",
        "raw": item,
    }

def crawl_all(token: Optional[str]) -> List[Dict]:
    headers = build_headers(token)
    page = 1
    all_repos: List[Dict] = []
    consecutive_empty = 0

    # 简单重试/限流策略：若403/429/解析失败会等候并尝试切换 header strategy once
    tried_private_token_header = False

    while True:
        print(f"正在抓取第 {page} 页：{API_BASE}?page={page}&per_page={PER_PAGE}")
        data = fetch_page(page, headers, PER_PAGE)

        if data is None:
            # 如果未使用 PRIVATE-TOKEN 头，尝试切换一个常见头字段然后重试一次
            if not tried_private_token_header and token:
                print("尝试使用 PRIVATE-TOKEN 头再试一次...")
                headers["Authorization"] = None
                headers["PRIVATE-TOKEN"] = token
                tried_private_token_header = True
                time.sleep(1.0)
                data = fetch_page(page, headers, PER_PAGE)
                if data is None:
                    print("仍然无法获取该页，退出或等待后重试。")
                    break
            else:
                # 如果没有 token 或已尝试过，终止
                break

        if not data:
            # 空页（可能到了末尾）
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
            else:
                # 给点时间（防止短期限流）
                time.sleep(1.0 + page * 0.1)
                page += 1
                continue

        consecutive_empty = 0
        for item in data:
            repo = normalize_repo_item(item)
            all_repos.append(repo)

        # 如果本页返回小于 per_page，可以认为是最后一页
        if isinstance(data, list) and len(data) < PER_PAGE:
            break

        page += 1
        # 友好等待，避免触发限流（如果有大量页面可根据需要增大）
        time.sleep(0.3)

    return all_repos

def save_results(repos: List[Dict], csv_path: str = "openharmony_tpc_repos.csv", txt_path: str = "openharmony_tpc_repos.txt"):
    # 去重（以 html_url 或 path_with_namespace 为准）
    seen = set()
    unique = []
    for r in repos:
        key = (r.get("html_url") or r.get("path_with_namespace") or r.get("id"))
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    # 写 CSV（含常用字段）
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "path_with_namespace", "html_url", "description", "stars", "forks", "updated_at"])
        for r in unique:
            writer.writerow([
                r.get("id"),
                r.get("name"),
                r.get("path_with_namespace"),
                r.get("html_url"),
                (r.get("description") or "").replace("\n", " ").strip(),
                r.get("stars"),
                r.get("forks"),
                r.get("updated_at"),
            ])

    # 写纯链接 txt
    with open(txt_path, "w", encoding="utf-8") as f:
        for r in unique:
            url = r.get("html_url") or (f"https://gitcode.com/{r.get('path_with_namespace')}" if r.get("path_with_namespace") else "")
            if url:
                f.write(url + "\n")

    print(f"✅ 已保存 {len(unique)} 条到 '{csv_path}' 和 '{txt_path}'")

def main():
    parser = argparse.ArgumentParser(description="Crawl OpenHarmony-TPC repos from GitCode using PAT")
    parser.add_argument("--token", help="GitCode personal access token (optional, prefer env GITCODE_TOKEN)")
    args = parser.parse_args()

    token = args.token or os.getenv("GITCODE_TOKEN")
    if not token:
        print("⚠️ 未检测到令牌 (GITCODE_TOKEN)，匿名请求可能被限流或返回不完整结果。")
        print("建议先设置环境变量 GITCODE_TOKEN 或使用 --token 参数。")
        # 继续以匿名方式尝试（可选）
        confirm = input("是否继续匿名尝试抓取（y/N）? ").strip().lower()
        if confirm != "y":
            print("退出。请先设置令牌后重试。")
            sys.exit(1)

    repos = crawl_all(token)
    if not repos:
        print("⚠️ 未获取到任何仓库，可能被限流或令牌权限不足。")
        sys.exit(1)

    save_results(repos)

if __name__ == "__main__":
    main()
