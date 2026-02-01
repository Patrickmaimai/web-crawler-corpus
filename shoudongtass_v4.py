import requests
import csv
import re
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import quote

# --- 配置 ---
INPUT_FILE = "urls.txt"
OUTPUT_FILE = "huawei_corpus_final.csv"
# 涵盖所有翻译可能，确保匹配不漏
KEYWORDS = ["Huawei", "华为", "Хуавэй", "Hua wei"]

# 备选 User-Agent 池，每次重试更换身份
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

def get_with_retry(url):
    """遇到 429 不放弃，死磕到底直到拿到内容"""
    encoded_url = quote(url, safe='')
    # 设为翻译成英文 (tl=en)，因为英文分句更准，且对原始关键词保留最好
    translate_url = f"https://translate.google.com/translate?sl=auto&tl=en&u={encoded_url}"
    
    retry_count = 0
    max_retries = 5 # 单篇最大重试次数，防止死循环
    
    while retry_count < max_retries:
        headers = {
            'User-Agent': random.choice(UA_POOL),
            'Referer': 'https://www.google.com/',
        }
        
        try:
            # 基础延迟：5-10秒
            wait_time = random.uniform(6, 10) + (retry_count * 20) # 越错等越久
            if retry_count > 0:
                print(f"\n⏳ 第 {retry_count} 次重试，正在休眠 {int(wait_time)} 秒...")
            time.sleep(wait_time)
            
            response = requests.get(translate_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # 检查内容是否包含正常的翻译框架，防止拿到空的 200 页面
                if "google-src-active" in response.text or "result-container" in response.text or len(response.text) > 5000:
                    return response.text
                else:
                    print("⚠️  页面加载不全，准备重试...")
            
            if response.status_code == 429:
                print("🛑 触发 429 限制，Google 正在赶人...")
                retry_count += 1
                continue
            
            # 其他错误码也重试
            retry_count += 1
            
        except Exception as e:
            print(f"❌ 网络异常: {e}")
            retry_count += 1
            
    return None

def extract_sentences(html):
    if not html: return []
    
    soup = BeautifulSoup(html, 'html.parser')
    # 提取所有文本块
    for script in soup(["script", "style"]):
        script.extract()
        
    # 获取全文并按照多语种标点分句
    text = soup.get_text(" ", strip=True)
    sentences = re.split(r'(?<=[。？！.!?])\s*', text)
    
    matches = []
    for s in sentences:
        s_clean = s.strip()
        # 只要命中任何一个关键词就保留
        if any(kw.lower() in s_clean.lower() for kw in KEYWORDS):
            if 15 < len(s_clean) < 500:
                matches.append(s_clean)
    
    return list(set(matches))

def main():
    print("🔥 启动‘死磕重试’模式。目标：语料完整提取。")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8-sig', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['序号', '链接', '标题', '匹配语料'])

        with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
            lines = [l.strip() for l in f_in.readlines() if ',' in l]

        count = 1
        for i, line in enumerate(lines):
            title, url = line.split(',', 1)
            if "https://" in url[8:]: url = "https://" + url.split("https://")[-1]

            print(f"[{i+1}/{len(lines)}] 处理: {title[:20]}...", end=" ", flush=True)
            
            html_content = get_with_retry(url)
            sentences = extract_sentences(html_content)
            
            if sentences:
                for s in sentences:
                    writer.writerow([count, url, title, s])
                    count += 1
                print(f"✅ 成功拿回 {len(sentences)} 条")
                f_out.flush() # 每一篇都强制保存一次，防断电
            else:
                print("❓ 依然未匹配 (可能该文确实无关键词)")

    print(f"\n✨ 任务彻底完成！结果已存入 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()