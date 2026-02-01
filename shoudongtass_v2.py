import requests
import csv
import re
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import quote

# --- 配置 ---
INPUT_FILE = "urls.txt"
OUTPUT_FILE = "huawei_corpus_google.csv"
KEYWORD = "Huawei"  # 如果你翻译成了中文，记得把关键词也改成 "华为" 或保持英文匹配

# 使用 Google 翻译作为中转的函数
def get_via_google_translate(original_url):
    # 对原始 URL 进行编码，防止特殊字符破坏 Google 链接
    encoded_url = quote(original_url, safe='')
    # 构造 Google 翻译中转链接（这里翻译成中文 zh-CN，方便你查看）
    translate_url = f"https://translate.google.com/translate?sl=auto&tl=zh-CN&u={encoded_url}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    
    try:
        # 增加一点点延迟，虽然 Google 不太会封你，但我们要低调
        time.sleep(random.uniform(1, 2))
        
        response = requests.get(translate_url, headers=headers, timeout=20)
        
        # 检查是否成功拿到了 Google 的响应
        if response.status_code != 200:
            print(f"🛑 Google 翻译中转失败，状态码: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 在 Google 翻译的页面中，原网页的内容通常会被放在特定的标签里
        # 或者直接抓取所有的段落。因为 Google 会保留原有的 <p> 标签
        paragraphs = soup.find_all(['p', 'div', 'span'])
        
        full_text = ""
        for p in paragraphs:
            # 过滤掉脚本和样式代码
            if p.parent.name not in ['script', 'style']:
                full_text += p.get_text(" ", strip=True) + " "

        # 诊断打印
        print(f"📡 中转成功 | 页面文本长度: {len(full_text)}")

        # 分句匹配（匹配 Huawei 或 华为）
        sentences = re.split(r'(?<=[。？！.!?])\s*', full_text)
        
        # 匹配英文 "Huawei" 或 中文 "华为"
        matches = [s.strip() for s in sentences if ("Huawei" in s or "华为" in s) and len(s.strip()) > 10]
        
        return matches

    except Exception as e:
        print(f"❌ Google 中转异常: {e}")
        return []

def main():
    print(f"🚀 启动方案三：Google 翻译中转模式...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8-sig', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['序号', '原链接', '标题', '匹配语料'])

        with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
            lines = [line.strip() for line in f_in.readlines() if ',' in line]

        count = 1
        for i, line in enumerate(lines):
            title, url = line.split(',', 1)
            # 修复 URL
            if "https://" in url[8:]: url = "https://" + url.split("https://")[-1]

            print(f"[{i+1}/{len(lines)}] 正在通过 Google 访问: {title[:20]}...")
            
            sentences = get_via_google_translate(url)
            
            if sentences:
                for s in sentences:
                    writer.writerow([count, url, title, s])
                    count += 1
                print(f"✅ 成功提取 {len(sentences)} 条")
            else:
                print("❓ 未发现关键词")
                
            # 每 10 篇保存一次
            if (i+1) % 10 == 0:
                f_out.flush()

    print(f"✨ 任务结束。")

if __name__ == "__main__":
    main()