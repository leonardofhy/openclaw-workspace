#!/usr/bin/env python3
"""日記重要事件候選預處理：字數統計 + 關鍵字掃描（v2: 收緊篩選）"""
import json, sys, statistics
sys.path.insert(0, '/Users/leonardo/.openclaw/workspace/skills/leo-diary/scripts')
from read_diary import load_diary

# 強烈關鍵字（排除「開始」「決定」「結束」等日常用語）
STRONG_KEYWORDS = [
    '崩潰', '震撼', '再見', '後悔', '超爽',
    '離職', '分手', '告白', '吵架', '和好', '道歉', '大哭',
    '恐慌', '絕望', '興奮', '感動', '驚喜', '憤怒',
    '孤獨', '寂寞', '爆炸',
    '突破', '轉折', '里程碑', '第一次', '最後一次', '永遠', '再也不',
    '受不了', '太扯', '傻眼', '不敢相信', '搬家', '畢業',
    '入職', '面試', '錄取', '被拒', '確診', '手術', '住院', '意外',
    '出國', '回國', '求婚', '結婚', '懷孕',
]

# 中等關鍵字：需要 >=2 個同時出現才算
MEDIUM_KEYWORDS = [
    '開心', '難過', '失望', '生氣', '壓力', '焦慮',
    '改變', '生日', '旅行', '哭',
]

entries = load_diary()
print(f"共 {len(entries)} 篇日記", file=sys.stderr)

for e in entries:
    e['length'] = len(e['diary'])

lengths = [e['length'] for e in entries]
mean_len = statistics.mean(lengths)
std_len = statistics.stdev(lengths)
threshold_high = mean_len + 1.5 * std_len
print(f"平均字數: {mean_len:.0f}, 標準差: {std_len:.0f}, 高門檻: {threshold_high:.0f}", file=sys.stderr)

candidates = []

for e in entries:
    reasons = []
    text = e['diary']
    date = e['date']
    length = e['length']
    
    # 字數異常
    len_abnormal = False
    if length > threshold_high:
        reasons.append(f"字數 {length}（超過門檻 {threshold_high:.0f}）")
        len_abnormal = True
    if 0 < length < 100:
        reasons.append(f"字數僅 {length}（極短）")
        len_abnormal = True
    
    # 強烈關鍵字
    strong_found = [kw for kw in STRONG_KEYWORDS if kw in text]
    medium_found = [kw for kw in MEDIUM_KEYWORDS if kw in text]
    
    has_strong = len(strong_found) > 0
    has_medium_cluster = len(medium_found) >= 2
    
    all_kw = strong_found + (medium_found if has_medium_cluster else [])
    
    if all_kw:
        reasons.append(f"關鍵字: {', '.join(all_kw)}")
    
    # 篩選：至少有一個理由
    if reasons:
        candidates.append({
            "date": date,
            "length": length,
            "reasons": reasons,
            "keywords": all_kw,
            "score": (2 if len_abnormal else 0) + len(strong_found) * 2 + len(medium_found),
        })

candidates.sort(key=lambda x: (-x['score'], -x['length']))

output = {
    "generated": "2026-02-18",
    "total_entries": len(entries),
    "stats": {
        "mean_length": round(mean_len),
        "std_length": round(std_len),
        "threshold_high": round(threshold_high),
    },
    "candidate_count": len(candidates),
    "candidates": candidates,
}

out_path = '/Users/leonardo/.openclaw/workspace/memory/diary_event_candidates.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"候選日期數: {len(candidates)}", file=sys.stderr)
print(f"已寫入: {out_path}", file=sys.stderr)
