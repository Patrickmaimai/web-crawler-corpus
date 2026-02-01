#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import csv
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
import time
import random

# --- 辅助函数：处理 URL 参数 ---
def _set_query_param(url, key, value):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[str(key)] = str(value)
    new_query = urlencode(query, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

# --- 核心修改：精准提取文章链接 ---
def _collect_links_from_html(soup, base_url):
    """
    只提取真正的文章链接，排除分页按钮、搜索跳转等干扰。
    """
    links = set()
    for a_tag in soup.find_all('a', href=True):
        link = a_tag['href']
        full_url = urljoin(base_url, link)
        
        # 针对 Kommersant 的过滤规则：
        # 1. 链接中必须包含 '/doc/'（文章标识）
        # 2. 排除掉包含 'page=' 或 'search_query' 的分页/重复搜索链接
        if '/doc/' in full_url:
            if 'page=' not in full_url and 'search_query' not in link:
                # 规范化：移除 URL 末尾可能存在的参数，防止重复
                clean_url = full_url.split('?')[0]
                links.add(clean_url)
    return links

# --- 改进版：自动检测结束点 ---
def extract_article_links(url, limit=None):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/'
        }
        
        all_links = set()
        current_page = 1
        no_new_content_count = 0  # 计数器：连续多少页没发现新文章

        print("🔍 开始自动探测分页抓取...")

        while True:
            # 构造带页码的搜索 URL
            page_url = _set_query_param(url, 'page', current_page)
            print(f"正在尝试第 {current_page} 页: {page_url}")
            
            try:
                # 设置超时，防止死挂
                response = requests.get(page_url, headers=headers, timeout=15)
                if response.status_code != 200:
                    print(f"🛑 停止：服务器返回状态码 {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 提取这一页中符合规则的文章链接
                new_links = _collect_links_from_html(soup, page_url)
                
                before_count = len(all_links)
                all_links.update(new_links)
                after_count = len(all_links)
                
                new_added = after_count - before_count
                
                if new_added > 0:
                    print(f"  ✅ 发现 {new_added} 个新文章链接，累计 {after_count}")
                    no_new_content_count = 0  # 只要有新内容，重置计数器
                else:
                    no_new_content_count += 1
                    print(f"  ⚠️ 本页未发现新文章内容 (空结果或内容重复，累计次数: {no_new_content_count})")

                # 【自动停止逻辑】
                # 如果连续 2 页都没有抓到任何“新”的文章链接，说明已经彻底跑出了搜索结果范围
                if no_new_content_count >= 2:
                    print("\n🏁 探测结束：后续页面已无新内容，程序自动停止。")
                    break

                # 总量限制（如果你在 main 里设置了 limit 参数）
                if limit and after_count >= limit:
                    print(f"🚩 已达到设定的总量限制: {limit}")
                    break

                current_page += 1
                # 随机休眠 1-2 秒，防止触发反爬
                time.sleep(random.uniform(1.0, 2.2))

            except Exception as e:
                print(f"❌ 访问第 {current_page} 页出错: {e}")
                break

        return list(all_links)[:limit] if limit else list(all_links)
        
    except Exception as e:
        print(f"提取链接错误: {e}")
        return []

# --- 提取正文语料 ---
def extract_sentences_with_keyword(url, keyword):
    try:
        headers = {'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36'
        ])}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 移除干扰标签
        for s in soup(["script", "style", "nav", "footer"]):
            s.decompose()
        
        text = soup.get_text()
        # 适配中俄英常用分句符号
        sentences = re.split(r'[。！？\.\!\?；;]+', text)
        
        matching_sentences = []
        for s in sentences:
            clean_s = s.strip()
            if clean_s and keyword.lower() in clean_s.lower():
                # 过滤太短的噪音（如菜单词）
                if len(clean_s) > 10:
                    matching_sentences.append(clean_s)
        
        return matching_sentences
        
    except Exception:
        return []

# --- 保存 ---
def save_results_to_csv(all_results, keyword, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['序号', '来源URL', '语句内容', '关键词'])
        for idx, (url, sentence) in enumerate(all_results, 1):
            writer.writerow([idx, url, sentence, keyword])
    print(f"\n✓ 成功！语料已保存至: {output_file}")

# --- 执行 ---
def main():
    # 这里不需要改 page 参数，程序会自动循环
    base_search_url = "https://www.kommersant.ru/search/results?places=&categories=&datestart=2025-02-01&dateend=2026-02-01&sort_type=0&regions=&results_count=&search_query=Huawei"
    keyword = "Huawei"
    
    print("=" * 60)
    print(f"🚀 启动自动分页爬虫 | 关键词: {keyword}")
    print("=" * 60)
    
    # 第一步: 自动提取所有有效链接
    article_links = extract_article_links(base_search_url)
    
    if not article_links:
        print("❌ 未抓取到任何有效链接。")
        return
    
    print(f"\n🔗 共计获取 {len(article_links)} 个文章链接，开始提取语料...\n")
    
    # 第二步: 提取关键词语句
    all_results = []
    for i, link in enumerate(article_links, 1):
        print(f"[{i}/{len(article_links)}] 提取中: {link[:50]}...")
        sentences = extract_sentences_with_keyword(link, keyword)
        for s in sentences:
            all_results.append((link, s))
        time.sleep(random.uniform(0.5, 1.2)) # 礼貌间歇
    
    # 第三步: 保存
    if all_results:
        output_file = f"result_{keyword}_{int(time.time())}.csv"
        save_results_to_csv(all_results, keyword, output_file)
    else:
        print("📭 未找到包含关键词的语料。")

if __name__ == "__main__":
    main()