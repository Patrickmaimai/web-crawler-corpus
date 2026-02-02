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

# --- 核心提取逻辑：增加文章特征过滤 ---
def _collect_links_from_html(soup, base_url):
    links = set()
    for a_tag in soup.find_all('a', href=True):
        link = a_tag['href']
        full_url = urljoin(base_url, link)
        if '/doc/' in full_url:
            if 'page=' not in full_url and 'search_query' not in link:
                clean_url = full_url.split('?')[0]
                links.add(clean_url)
    return links

# --- 改进版：具备“反拦截自愈”的分页提取 ---
def extract_article_links(url, limit=None):
    try:
        all_links = set()
        current_page = 1
        no_new_content_count = 0  
        
        # 模拟真实浏览器头部
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/'
        }

        print("🔍 开始自适应分页抓取（支持防封重试）...")

        while True:
            page_url = _set_query_param(url, 'page', current_page)
            print(f"正在尝试第 {current_page} 页: {page_url}")
            
            try:
                response = requests.get(page_url, headers=headers, timeout=20)
                
                # --- 核心改进：人机校验/频率限制识别 ---
                if response.status_code in [403, 429] or "captcha" in response.text.lower():
                    wait_time = random.uniform(80, 150) # 触发封锁后深度休眠
                    print(f"\n⚠️ 检测到人机验证或访问受限 (Code: {response.status_code})")
                    print(f"🛑 程序将休眠 {int(wait_time)} 秒以解除封锁，随后重试当前页...")
                    time.sleep(wait_time)
                    continue  # 跳过本次循环，重新请求当前 current_page

                if response.status_code != 200:
                    print(f"❌ 异常状态码 {response.status_code}，5秒后尝试下一页...")
                    time.sleep(5)
                    current_page += 1
                    continue

                # --- 正常解析流程 ---
                soup = BeautifulSoup(response.content, 'html.parser')
                new_links = _collect_links_from_html(soup, page_url)
                
                before_count = len(all_links)
                all_links.update(new_links)
                after_count = len(all_links)
                
                new_added = after_count - before_count
                
                if new_added > 0:
                    print(f"  ✅ 发现 {new_added} 个新文章链接，累计 {after_count}")
                    no_new_content_count = 0 
                else:
                    # 只有在请求成功但没内容时，才认为可能到底了
                    no_new_content_count += 1
                    print(f"  ⚠️ 本页未发现新文章内容 (空结果计数: {no_new_content_count})")

                # 如果连续 3 页成功请求但都没有新文章，才真正停止
                if no_new_content_count >= 3:
                    print("\n🏁 探测结束：连续多页无新内容，自动停止。")
                    break

                if limit and after_count >= limit:
                    break

                current_page += 1
                # 正常的步进随机休眠
                time.sleep(random.uniform(2.5, 4.5))

            except (requests.exceptions.RequestException, Exception) as e:
                print(f"❌ 网络波动或异常: {e}，正在重试当前页...")
                time.sleep(10)
                continue

        return list(all_links)[:limit] if limit else list(all_links)
        
    except Exception as e:
        print(f"提取链接异常: {e}")
        return []

# --- 提取语料函数 ---
def extract_sentences_with_keyword(url, keyword):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0'}
        response = requests.get(url, headers=headers, timeout=15)
        
        # 语料提取阶段如果遇到拦截，同样增加保护
        if response.status_code in [403, 429]:
            print(f"\n⚠️ 详情页访问受限，休眠 30 秒...")
            time.sleep(30)
            return []

        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        for s in soup(["script", "style", "nav", "footer"]):
            s.decompose()
        
        text = soup.get_text()
        sentences = re.split(r'[。！？\.\!\?；;]+', text)
        
        matching_sentences = []
        for s in sentences:
            clean_s = s.strip()
            if clean_s and keyword.lower() in clean_s.lower():
                if len(clean_s) > 10:
                    matching_sentences.append(clean_s)
        return matching_sentences
    except:
        return []

# --- 保存结果 ---
def save_results_to_csv(all_results, keyword, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['序号', '来源URL', '语句内容', '关键词'])
        for idx, (url, sentence) in enumerate(all_results, 1):
            writer.writerow([idx, url, sentence, keyword])
    print(f"\n✓ 成功！保存至: {output_file}")

# --- 主程序 ---
def main():
    base_search_url = "https://www.kommersant.ru/search/results?search_query=Huawei&sort_type=0&search_full=1&time_range=2&dateStart=2020-01-02&dateEnd=2026-02-02"
    keyword = "Huawei"
    
    print("=" * 60)
    print(f"🚀 启动自修复分页爬虫 | 关键词: {keyword}")
    print("=" * 60)

    # 1. 抓取链接
    article_links = extract_article_links(base_search_url)
    
    if not article_links:
        print("❌ 未获取到有效链接。")
        return
    
    print(f"\n🔗 共计获取 {len(article_links)} 个链接，开始提取语料...\n")
    
    # 2. 提取语句
    all_results = []
    for i, link in enumerate(article_links, 1):
        print(f"[{i}/{len(article_links)}] 提取中: {link[:50]}...")
        sentences = extract_sentences_with_keyword(link, keyword)
        for s in sentences:
            all_results.append((link, s))
        
        # 详情页爬取也建议稍微放慢速度
        time.sleep(random.uniform(0.8, 1.5))
    
    # 3. 保存
    if all_results:
        output_file = f"result_{keyword}_{int(time.time())}.csv"
        save_results_to_csv(all_results, keyword, output_file)
    else:
        print("📭 未找到包含关键词的语料。")

if __name__ == "__main__":
    main()