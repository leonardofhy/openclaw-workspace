# 📢 實驗室公告：共享帳號與 CLIProxyAPI 使用說明

大家好，

為了方便大家共享實驗室資源與使用付費 API，我們建立了一套統一的管理機制。請參考以下說明：

## 1. 共享帳號 (Shared Accounts)
我們建立了一組公用的 Google 帳號與瀏覽器設定，用於存取付費訂閱服務（如 ChatGPT Plus, Claude Pro 等）。

- **公用帳號**: `little.leo.agent@gmail.com` (或是實驗室專用帳號)
- **使用方式**:
    - 請使用實驗室內網的 **共享瀏覽器 (Shared Browser)** 進行登入。
    - **禁止** 將此帳號登入個人設備，以免觸發風控導致帳號被鎖。
    - 若需驗證碼，請在群組 @Little Leo 獲取。

## 2. CLIProxyAPI (API 代理服務)
為了讓大家的程式能方便呼叫 LLM API（OpenAI, Anthropic, Gemini），我們部署了 `CLIProxyAPI` 服務。

- **功能**: 統一管理 API Key，避免 Key 洩漏，並提供用量監控。
- **Endpoint**: `http://192.168.x.x:8000/v1` (請替換為實際 IP)
- **使用範例 (Python)**:
  ```python
  from openai import OpenAI

  client = OpenAI(
      base_url="http://192.168.x.x:8000/v1",
      api_key="sk-lab-shared-key"  # 請向 Leo 索取
  )

  response = client.chat.completions.create(
      model="gpt-4o",
      messages=[{"role": "user", "content": "Hello!"}]
  )
  print(response.choices[0].message.content)
  ```

## 3. 注意事項
- 請勿濫用 API 資源，後台有流量監控。
- 若發現服務異常，請在群組回報。

Best,
Leo & Little Leo 🦁
