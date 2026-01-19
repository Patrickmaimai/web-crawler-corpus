#!/usr/bin/env python
# -*- coding: utf-8 -*-
#终端输入 python extract_keywords.py然后回车运行

import requests
from bs4 import BeautifulSoup
import csv
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
import time


def _set_query_param(url, key, value):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[str(key)] = str(value)
    new_query = urlencode(query, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def _collect_links_from_html(soup, base_url):
    links = set()
    for a_tag in soup.find_all('a', href=True):
        link = a_tag['href']
        full_url = urljoin(base_url, link)
        if full_url.startswith('http'):
            links.add(full_url)
    return links


def extract_article_links(url, limit=None, max_pages=None):
    """
    从网页中提取所有文章链接
    
    参数:
        url (str): 网页链接
        limit (int): 限制链接数量
    
    返回:
        list: 文章链接列表
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        all_links = set()

        # 支持分页抓取：很多站点通过“加载更多/下一页”异步追加结果
        # 尝试常见参数 page / p，从第1页开始递增，直到检测不到新链接或达到上限
        tried_param_names = ['page', 'p']
        current_page = 1
        expected_total = None
        working_param = None  # 记录哪个参数名有效
        no_new_links_count = 0  # 记录连续多少页没有新链接

        while True:
            page_has_new_links = False
            # 如果已经确定有效参数，就只用它；否则尝试所有参数
            params_to_try = [working_param] if working_param else tried_param_names
            
            for param_name in params_to_try:
                page_url = _set_query_param(url, param_name, current_page)
                print(f"正在获取网页链接: {page_url}")
                response = requests.get(page_url, headers=headers, timeout=10)
                response.encoding = 'utf-8'

                if response.status_code != 200:
                    print(f"错误: 无法访问网址，状态码 {response.status_code}")
                    continue

                soup = BeautifulSoup(response.content, 'html.parser')

                # 解析结果总数提示（例如：Результатов: около 143）
                if expected_total is None:
                    text_all = soup.get_text(" ", strip=True)
                    m = re.search(r"Результатов:\s*около\s*(\d+)", text_all)
                    if m:
                        expected_total = int(m.group(1))

                before = len(all_links)
                new_links = _collect_links_from_html(soup, page_url)
                all_links.update(new_links)
                after = len(all_links)

                print(f"  第{current_page}页增加 {after - before} 个新链接，累计 {after}")

                # 如果有新链接，记录该参数有效并重置计数器
                if after > before:
                    page_has_new_links = True
                    no_new_links_count = 0
                    if working_param is None:
                        working_param = param_name
                        print(f"  确定分页参数: {param_name}")

                # 检测是否还有“加载更多/下一页”的字眼，若没有且未增加新链接则停止
                text_page = soup.get_text(" ", strip=True)
                has_load_more = ('Загрузить ещё' in text_page) or ('Показать ещё' in text_page)

                if limit and after >= limit:
                    links = list(all_links)[:limit]
                    print(f"找到 {len(links)} 个链接（达到限制）")
                    return links

                # 如果没有新增加链接，说明该参数名不生效，换下一个参数名或结束
                if (after == before) and (not has_load_more):
                    # 该参数方式可能无效，尝试下一个参数名
                    continue

                # 如果解析到期望总数且达到或超过，停止
                if expected_total and after >= expected_total:
                    links = list(all_links)
                    print(f"找到 {len(links)} 个链接（达到页面标注的总量≈{expected_total}）")
                    return links

                # 如果本页有新链接，停止尝试其他参数名，进入下一页
                if page_has_new_links:
                    break

            # 如果本页所有参数都没有新链接，增加计数
            if not page_has_new_links:
                no_new_links_count += 1
                print(f"  警告: 连续 {no_new_links_count} 页没有新链接")
                
                # 连续3页没有新链接，认为已经到底了
                if no_new_links_count >= 3:
                    print(f"连续 {no_new_links_count} 页无新链接，停止抓取")
                    break

            current_page += 1
            if max_pages and current_page > max_pages:
                print(f"达到最大页数限制: {max_pages}")
                break

            # 温和一些，间隔抓取
            time.sleep(0.6)

        links = list(all_links)
        if limit:
            links = links[:limit]
        print(f"找到 {len(links)} 个链接")
        return links
        
    except Exception as e:
        print(f"提取链接错误: {e}")
        return []


def extract_sentences_with_keyword(url, keyword):
    """
    从网址中提取包含指定关键词的语句
    
    参数:
        url (str): 网页链接
        keyword (str): 关键词
    
    返回:
        list: 包含关键词的句子列表
    """
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"  正在处理: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"  错误: 无法访问，状态码 {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 移除脚本和样式元素
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 获取所有文本
        text = soup.get_text()
        
        # 按句号、感叹号、问号分割句子
        sentences = re.split(r'[。！？\.\!\?；;]+', text)
        
        # 筛选包含关键词的句子
        matching_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and keyword.lower() in sentence.lower():
                matching_sentences.append(sentence)
        
        if matching_sentences:
            print(f"  找到 {len(matching_sentences)} 条包含关键词的语句")
        
        return matching_sentences
        
    except requests.exceptions.RequestException as e:
        print(f"  请求错误: {e}")
        return []
    except Exception as e:
        print(f"  错误: {e}")
        return []


def save_results_to_csv(all_results, keyword, output_file=None):
    """
    将提取结果保存为CSV文件
    
    参数:
        all_results (list): 包含(URL, 句子)的元组列表
        keyword (str): 关键词
        output_file (str): 输出文件名
    
    返回:
        str: 保存的文件路径
    """
    if output_file is None:
        output_file = f"result_{keyword}.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['序号', '来源URL', '语句内容', '关键词'])
        for idx, (url, sentence) in enumerate(all_results, 1):
            writer.writerow([idx, url, sentence, keyword])
    
    print(f"\n✓ 结果已保存到: {output_file}")
    return output_file


def main():
    # 主页面URL
    main_url = "https://russian.rt.com/search?q=Huawei&type=&df=2020-01-18&dt=2026-01-18"#这里改网址
    keyword = "Huawei"#这里改关键词
    max_links = None  # 设置为 None 表示处理所有链接，或改为具体数字限制
    
    print("=" * 60)
    print("网页爬虫关键词提取工具")
    print("=" * 60)
    print(f"主页面: {main_url}")
    print(f"关键词: {keyword}")
    print(f"最多处理链接数: {max_links}")
    print("=" * 60)
    
    # 第一步: 提取主页面上的所有链接
    article_links = extract_article_links(main_url, limit=max_links)
    
    if not article_links:
        print("未找到任何链接")
        return
    
    print(f"\n将处理 {len(article_links)} 个链接\n")
    
    # 第二步: 逐个访问链接并提取关键词
    all_results = []
    for i, link in enumerate(article_links, 1):
        print(f"[{i}/{len(article_links)}]")
        sentences = extract_sentences_with_keyword(link, keyword)
        for sentence in sentences:
            all_results.append((link, sentence))
        time.sleep(1)  # 为了礼貌，每个请求间隔1秒
    
    # 第三步: 保存结果
    print(f"\n总共找到 {len(all_results)} 条包含关键词的语句")
    
    if all_results:
        output_file = f"result_{keyword}.csv"
        save_results_to_csv(all_results, keyword, output_file)
        print("=" * 60)
        print("✓ 提取完成！")
    else:
        print("未找到包含关键词的语句")


if __name__ == "__main__":
    main()
