---
name: paper-writing
description: 協助 Leo 寫學術論文（Interspeech/ACL/NeurIPS 水準）。當 Leo 在寫論文、改稿、需要 review feedback、checklist 檢查時使用。觸發詞：寫論文、改稿、review my paper、abstract 怎麼寫、幫我看 intro、checklist、投稿前檢查。
---

# Paper Writing Assistant

基於小金老師的論文寫作教學指南（李宏毅 lab），協助寫出頂會水準的論文。

## 完整指南

→ `references/xiaojin-guide.md`（小金老師原始教學文件）

每次協助寫作時，先讀該檔案中對應 section 的指導。

## Quick Reference

### Ernst 三件事自我檢查
寫論文前必須能回答：
1. 問題很重要嗎？（有影響力）
2. 問題很難嗎？（現有方法不夠好）
3. 你解決了嗎？（有實驗證明）

### Abstract 公式（4-6 句）
背景 → Gap（However...）→ 方法（We propose...）→ 結果（具體數字）

### Introduction 結構
大背景(1段) → 建立 Gap(2-3段) → 方法 overview(1段) → Contributions(bullet points)

### Method 三層
1. Problem Formulation
2. **Key Insight**（為什麼能解決？學生最常跳過！）
3. Technical Details

### Results 解讀
❌ "As shown in Table 1" → ✅ "Table 1 shows X outperforms Y by Z%, suggesting [insight]"

### 提交前 5 分鐘自查
```
grep -i "novel" → 考慮刪除
grep -i "utilize" → 改成 use
grep -i "etc\." → 改成具體列舉
grep -i "significant" → 確認有數字
grep -i "there is\|there are" → 改主動句
```

## 使用模式

| 模式 | 觸發 | 做什麼 |
|------|------|--------|
| **section-help** | 「abstract 怎麼寫」「幫我看 intro」 | 讀 guide 對應章節，給具體建議 |
| **review** | 「review my paper」「幫我改這段」 | 對照 guide 的 before/after 範例給修改建議 |
| **checklist** | 「投稿前檢查」「checklist」 | 跑完整 checklist（第八課 + 實驗 checklist） |
| **style-fix** | 「幫我潤稿」「英文有沒有問題」 | 對照第十一課（中文母語者 30 個常見錯誤）|

## Interspeech 4 頁空間分配
| Section | 佔比 | 備註 |
|---------|------|------|
| Abstract | 固定 | ~150 字，5 句公式 |
| Introduction | 25-30% | 最重要，含 gap + contribution |
| Related Work | 10-15% | 可融入 Intro |
| Method | 25-30% | 重 insight 不重 detail |
| Experiments | 25-30% | Setup + Results + Ablation |
| Conclusion | 5-8% | 3-4 句即可 |

**三個鐵律：** Figure 1 必須在第一頁 | 寧砍 Method 文字不砍 Figure 1 和 Results Table | Related Work 不超過半欄
