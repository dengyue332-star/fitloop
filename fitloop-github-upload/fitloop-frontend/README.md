# FitLoop 前端 · 饮食记录

这一页对应 Figma 的“03 · 饮食记录”，已经接上后端：

1. 用户输入一餐；
2. 点击“查询营养”调用 `POST /food/estimate`；
3. 用户看见估算后，点击“确认并保存”；
4. 前端调用 `POST /food-logs` 写进 Supabase。

它不含任何 DeepSeek、Supabase 或 LangSmith 密钥。那些密钥只留在后端的 `fitloop-mvp/.env`。

## 启动

先从 `.env.local.example` 复制出 `.env.local`，并填入演示用户 UUID；然后：

```bash
npm install
npm run dev
```

打开 Vite 显示的本地网址（通常为 <http://127.0.0.1:5173>）。后端须先在 `fitloop-mvp` 文件夹启动。
