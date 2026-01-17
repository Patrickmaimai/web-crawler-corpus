#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import csv
import re
from urllib.parse import urljoin
import time


def extract_article_links(url, limit=None):
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
        
        print(f"正在获取网页链接: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"错误: 无法访问网址，状态码 {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取所有链接
        links = set()
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            # 转换为绝对URL
            full_url = urljoin(url, link)
            # 只保留https链接
            if full_url.startswith('http'):
                links.add(full_url)
        
        links = list(links)
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
    main_url = "https://tass.com/"
    keyword = "Russia"
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
