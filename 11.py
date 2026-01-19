import requests
import csv
import re
import time
from bs4 import BeautifulSoup

# 使用你提供的 cURL 信息
COOKIES = {
    'spid': '1768719007602_ec7647d43c8221785c41e5e8a154c79b_0dfdfrbr7k084j27',
    'domain_sid': 'gqjJ2jhW0FbDn3dJcilUO:1768719026120',
    'ma_id_api': 'z2NSv23Rdi7/Vql34KxC5spuDJavtr8fv9GDKh/9fhaXSkHozbQ7haiXZH/89yYHxQlitSXeMCQvNdZnASSvrUJyArT3nacd9V+dqG+1BTSq/x9iH/v3n9oXK8a6GTFvnbMblBG2MioRajTztVsslqPZ/8wMGZsPn1RFrsiNi5Z2U34IwAEQj3S3wf+Q7MscVFa1BM75u88cvgLCDxVcx9++LJabxiQFspxPX+2uA7yD/ClVI5BcRtnfsu1N3oBdyfGh8O3our6U2O9J9Tchl1G9tlW0GKrsQmYToM2Cd+PytgoWY5epBkdN07n3P+Qj0cGxCIol7ABXa81g95B/VQ==',
}

HEADERS = {
    'accept': '*/*',
    'accept-language': 'en,zh-CN;q=0.9,zh;q=0.8',
    'referer': 'https://tass.ru/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
}

def get_tass_links(query, total_limit=50):
    all_links = []
    search_after = None
    api_url = "https://tass.ru/tbp/api/v1/search"

    print(f"🚀 开始根据真实报文抓取: {query}")

    while len(all_links) < total_limit:
        params = {'search': query, 'limit': '30', 'lang': 'ru'}
        if search_after:
            params['search_after'] = search_after

        try:
            response = requests.get(api_url, params=params, headers=HEADERS, cookies=COOKIES, timeout=15)
            if response.status_code != 200: break

            data = response.json()
            result_obj = data.get('result', {})
            
            # --- 核心修正：根据你的报文，字段名为 'contents' ---
            contents = result_obj.get('contents', [])
            
            if not contents:
                print("🏁 未发现文章内容。")
                break

            for item in contents:
                path = item.get('url', '')
                if path:
                    full_url = "https://tass.ru" + path if path.startswith('/') else path
                    if full_url not in [l['url'] for l in all_links]:
                        all_links.append({'url': full_url, 'title': item.get('title', '')})
                if len(all_links) >= total_limit: break

            print(f"✅ 已抓取 {len(all_links)} 条链接")

            # 检查是否有更多
            if not result_obj.get('has_more', False):
                print("🔚 接口提示没有更多相关内容了。")
                break
                
            # 更新 search_after 逻辑 (如果有的话)
            search_after = result_obj.get('search_after')
            if not search_after: break
            time.sleep(1)

        except Exception as e:
            print(f"⚠️ 出错: {e}")
            break
    return all_links

def extract_sentences(url, keyword):
    """提取正文匹配句"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        # TASS 常用正文容器
        content = soup.find('div', class_=re.compile(r'article__text|text-block|news-text'))
        text = content.get_text(" ", strip=True) if content else soup.get_text(" ", strip=True)
        
        sentences = re.split(r'[.!?。！？]+', text)
        return [s.strip() for s in sentences if keyword.lower() in s.lower() and len(s.strip()) > 5]
    except:
        return []

def main():
    keyword = "Huawei"
    links = get_tass_links(keyword, total_limit=50)
    
    if not links:
        print("🛑 抓取失败，请检查关键词或 Cookie。")
        return

    final_data = []
    for i, item in enumerate(links, 1):
        print(f"[{i}/{len(links)}] 正在提取正文: {item['url']}")
        matches = extract_sentences(item['url'], keyword)
        for s in matches:
            final_data.append([i, item['url'], s, keyword])
        time.sleep(0.5)

    if final_data:
        fname = f"tass_{keyword}_results.csv"
        with open(fname, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['序号', '链接', '匹配语句', '关键词'])
            writer.writerows(final_data)
        print(f"\n✨ 任务完成！保存至: {fname}")

if __name__ == "__main__":
    main()