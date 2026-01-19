import requests
import csv
import re
import time
import random
from bs4 import BeautifulSoup

# --- 配置 ---
INPUT_FILE = "urls.txt"      # 你刚才保存链接的文件
OUTPUT_FILE = "huawei_corpus.csv"
KEYWORD = "Huawei"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
}

def extract_sentences(url):
    """访问文章链接并提取包含关键词的句子"""
    try:
        # 增加随机延迟，防止 TASS 封锁你的 IP
        time.sleep(random.uniform(0.3, 0.8))
        
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 定位正文：TASS 常见的正文容器
        article = soup.select_one('.article__text, .text-block, .news-text')
        text = article.get_text(" ", strip=True) if article else soup.get_text(" ", strip=True)
        
        # 俄语/英语分句
        sentences = re.split(r'(?<=[.!?])\s+', text)
        matches = [s.strip() for s in sentences if KEYWORD.lower() in s.lower() and len(s.strip()) > 10]
        return matches
    except Exception as e:
        print(f"  ❌ 无法读取 {url}: {e}")
        return []

def main():
    print(f"🚀 开始处理本地链接列表...")
    
    # 准备写入 CSV
    with open(OUTPUT_FILE, 'w', encoding='utf-8-sig', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['序号', '链接', '标题', '匹配语料'])
        
        # 读取你保存的链接文件
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
                lines = f_in.readlines()
        except FileNotFoundError:
            print(f"🛑 找不到 {INPUT_FILE}，请先执行第一步提取链接。")
            return

        count = 1
        for i, line in enumerate(lines):
            if ',' not in line: continue
            
            title, url = line.strip().split(',', 1)
            print(f"[{i+1}/{len(lines)}] 正在提取: {title[:20]}...")
            
            sentences = extract_sentences(url)
            for s in sentences:
                writer.writerow([count, url, title, s])
                count += 1
            
            # 每 10 篇保存一次，防止程序崩溃丢失数据
            if (i + 1) % 10 == 0:
                f_out.flush()
                print(f"💾 已保存前 {i+1} 篇的结果")

    print(f"✨ 任务完成！语料已存入 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()