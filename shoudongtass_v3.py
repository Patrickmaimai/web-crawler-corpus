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
# 匹配英俄文及翻译后的中文关键词
KEYWORDS = ["Huawei", "华为", "Хуавэй"]

def get_via_google_translate(original_url):
    """通过 Google 翻译中转访问"""
    encoded_url = quote(original_url, safe='')
    # 翻译成中文 (tl=zh-CN) 以利用 Google 服务器中转
    translate_url = f"https://translate.google.com/translate?sl=auto&tl=zh-CN&u={encoded_url}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        # 核心：必须慢。Google 对翻译接口的爬虫检测很严
        time.sleep(random.uniform(6.0, 12.0))
        
        response = requests.get(translate_url, headers=headers, timeout=30)
        
        if response.status_code == 429:
            print("\n🛑 触发 Google 频率限制 (429)。程序将休眠 60 秒尝试自愈...")
            time.sleep(60)
            return []
            
        if response.status_code != 200:
            print(f"⚠️  访问失败，状态码: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Google 翻译会将内容包裹在特定结构中，直接提取所有文本块
        # 排除掉脚本、样式等干扰标签
        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text(" ", strip=True)
        
        # 诊断打印：如果文本太短，可能是中转页没加载完
        if len(text) < 500:
            return []

        # 分句逻辑：支持中英俄标点
        sentences = re.split(r'(?<=[。？！.!?])\s*', text)
        
        # 关键词匹配
        matches = []
        for s in sentences:
            s_clean = s.strip()
            if any(kw.lower() in s_clean.lower() for kw in KEYWORDS):
                if len(s_clean) > 10: # 过滤掉太短的碎片
                    matches.append(s_clean)
        
        return list(set(matches)) # 去重

    except Exception as e:
        print(f"❌ 异常: {e}")
        return []

def main():
    print(f"🚀 启动 Google 翻译中转模式 (带自愈保护)...")
    
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8-sig', newline='') as f_out:
            writer = csv.writer(f_out)
            writer.writerow(['序号', '原链接', '标题', '匹配语料'])

            with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
                # 过滤掉不含逗号或空的行
                lines = [l.strip() for l in f_in.readlines() if ',' in l]

            total = len(lines)
            count = 1
            
            for i, line in enumerate(lines):
                parts = line.split(',', 1)
                title = parts[0]
                url = parts[1]
                
                # 自动修复畸形链接
                if "https://" in url[8:]:
                    url = "https://" + url.split("https://")[-1]

                print(f"[{i+1}/{total}] 访问: {title[:20]}...", end=" ", flush=True)
                
                sentences = get_via_google_translate(url)
                
                if sentences:
                    for s in sentences:
                        writer.writerow([count, url, title, s])
                        count += 1
                    print(f"✅ 提取 {len(sentences)} 条")
                else:
                    print("❓ 无匹配或被拦截")
                
                # 每 5 篇强制保存
                if (i + 1) % 5 == 0:
                    f_out.flush()

    except KeyboardInterrupt:
        print("\n👋 用户中断程序。")
    except Exception as e:
        print(f"\n🛑 运行出错: {e}")

    print(f"\n✨ 任务结束。结果已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()