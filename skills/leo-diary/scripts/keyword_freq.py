#!/usr/bin/env python3
"""
關鍵字頻率分析（不需要 LLM，純 Python）
統計日記中各詞彙出現次數
"""
import re
import sys
import json
from collections import Counter
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from read_diary import load_diary

# 停用詞（中文常見詞）
STOPWORDS = set("""
今天 昨天 明天 然後 所以 因為 但是 不過 雖然 如果 就是 還是 
已經 可以 沒有 一個 這個 那個 一些 自己 覺得 感覺 時候 時間
我們 他們 她們 你們 這樣 那樣 什麼 怎麼 為什麼 多少 多久 
一直 一下 一起 一定 一點 一次 一天 一樣 這裡 那裡 
也是 也有 也在 還有 還是 不是 不太 不會 不想 不用 不需要 
有點 有些 有時 有人 有一 然後就 然後再
啊 吧 嗎 呢 哦 哈 欸 嗯 呀 咦 好像 好的 好吧
大家 大概 左右 之後 之前 以後 以前 其實 當然 雖然 
""".split())

def extract_words(text):
    # 提取中文詞（2-4字）和英文單詞
    zh_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    en_words = re.findall(r'[a-zA-Z]{3,}', text)
    return [w for w in zh_words if w not in STOPWORDS] + [w.lower() for w in en_words]

def analyze(start_date=None, end_date=None, top_n=30):
    entries = load_diary(start_date=start_date, end_date=end_date, has_diary_only=True)
    all_words = []
    for e in entries:
        all_words.extend(extract_words(e["diary"]))
    
    counter = Counter(all_words)
    return {
        "total_entries": len(entries),
        "total_words": len(all_words),
        "top_keywords": counter.most_common(top_n)
    }

if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else None
    end = sys.argv[2] if len(sys.argv) > 2 else None
    result = analyze(start, end)
    print(f"分析 {result['total_entries']} 篇日記，共 {result['total_words']} 個詞彙\n")
    print("Top 30 關鍵字：")
    for word, count in result["top_keywords"]:
        bar = "█" * min(count // 5, 40)
        print(f"  {word:8s} {count:4d} {bar}")
