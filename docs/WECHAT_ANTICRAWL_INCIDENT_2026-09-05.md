# 微信反爬拦截事件档案与解决指南（2026-09-05）

> **一句话解决方法**：运行 `./venv/Scripts/python.exe test/manual/wxchat/wxchat_verify_once.py`，
> 在弹出的浏览器窗口里点击"去验证"完成滑块验证，通过后 cookie 自动存入 `.wxchat_browser_profile` 档案，
> 之后所有批量任务（无头浏览器）自动复用该 cookie，不再被拦截。

---

## 1. 事件症状

- `--crawler-wxchat` / `--wxchat` 批量下载时**全部文章失败**
- 日志特征（`logs/app.log`）：
  ```
  [INFO]    Playwright PDF生成成功，文件大小: 29907 bytes (29.21 KB)
  [WARNING]    PDF仅 29 KB（低于 100 KB 阈值），疑似微信拦截页: 85
  [ERROR] ❌ PDF为拦截页假PDF: 85
  ```
- 假 PDF 统一为 **29~38KB**（真实文章为 2.2~14.7MB），内容是微信"环境异常，完成验证后即可继续访问"验证页
- 同一网络下**本人 Chrome 浏览器可正常打开文章**，但自动化浏览器一律被拦

## 2. 快速诊断：是"被风控"还是"检查机制误判"？

| 检查 | 方法 | 结论判断 |
|---|---|---|
| 看 PDF 大小 | 日志搜 `PDF仅`，或 `grep "PDF仅" logs/app.log \| tail` | 29~38KB=拦截页（真被风控）；≥100KB 被拦=检查机制误判（需查阈值） |
| 看是否字节级雷同 | 多篇失败文章的 PDF 字节数完全相同（如都是 29907） | 同一张拦截页 → 是风控，非文章本身问题 |
| 直接看页面 | `./venv/Scripts/python.exe test/diagnostic/probe_wechat_block.py` | 输出页面标题/正文/`navigator.webdriver`，截图在 `output/test_crawler_wxchat/probe_*.png` |
| 验证 cookie 是否在档 | `test/diagnostic/probe_wechat_profile.py` | 打印档案 cookie 列表；**有 `poc_sid` 即通行凭证有效** |

## 3. 根因（实测结论，非猜测）

微信本次风控是**三层叠加**，逐层排除法实测定位：

**第1层（IP + 验证cookie）**：无"已完成人机验证"的 cookie 时，该 IP 上所有新会话一律返回验证页。与 Playwright 自动化指纹基本无关：

| 方案 | 结果 |
|---|---|
| 隐藏 `navigator.webdriver` + 真实 Chrome UA + 去掉 `--enable-automation` 开关 | ❌ 仍被拦 |
| 系统真实 Chrome **有头**窗口 + 上述全部隐身参数 | ❌ 仍被拦（关键证据：排除指纹/无头检测） |
| 先访问 mp.weixin.qq.com 首页种普通 cookie，再访问文章 | ❌ 仍被拦 |
| 人工完成一次"去验证"滑块 → 档案获得 **`poc_sid`** cookie → 无头复用 | ✅ 通过，正文正常渲染 |

**第2层（会话行为）**：有了 poc_sid 后，**每篇文章新开一个浏览器进程仍会被拦**——短时间大量"全新浏览器会话"是典型自动化特征；而**一个浏览器会话内连续翻页**（像真人）全程放行。→ 解决：批次级浏览器复用（`PDFGenerator._get_context`/`close_browser`）。

**第3层（URL 记分，2026-09-05 11:47 修正）**：**与 URL 格式强相关**——全表统计：短链（`/s/xxx`）47 篇 0 失败、长链（`?__biz=...&mid=...&sn=...`）83 篇历史总计 0 成功。早晨风控期的批量失败把长链格式整体拉黑（公众号级别无差别：中金点睛有成功也有被拦，冠南全过，区别只在长短链）。→ 解决：短链正常下载；长链靠 20 分钟×N 退避自动缓释（记分会随时间衰减，探针曾观测到个别长链短暂放行）；取数按 `retry_count ASC` 排序让有前科的垫底；用户指示对重试≥3 次的 5 篇永久放弃（见 4.3）。若外部爬虫系统能提供短链格式 URL，长链文章即可绕开。

## 4. 解决方法（完整步骤）

### 4.1 一次性人工验证（首次 / cookie 失效时）

```bash
./venv/Scripts/python.exe test/manual/wxchat/wxchat_verify_once.py
```

- 会弹出 Chrome 窗口并打开一篇文章；点"去验证"完成滑块
- 脚本每 3 秒自动检测，检测到文章正文（`rich_media_content` 出现且无"环境异常"字样）即自动退出
- 通过后 `poc_sid` cookie 写入持久档案 `./.wxchat_browser_profile/`（已加入 .gitignore，勿删勿提交）
- 可选 `--url <文章链接>` 指定验证用文章

### 4.2 恢复批量下载

验证通过后直接重跑，失败的文章会按退避规则自动被重新扫到：

```bash
./venv/Scripts/python.exe main.py --crawler-wxchat          # 爬虫源全量续跑（断点续传）
./venv/Scripts/python.exe main.py --wxchat --wxchat-days 3  # wewe 源
```

无需任何额外参数——PDF 生成器自动使用 `.wxchat_browser_profile` 档案。

### 4.3 永久搁置被标记的文章（2026-09-05 用户指示）

被反复请求仍失败的 URL（重试≥3次）按永久失败处理，不再自动重试：

```sql
-- mysql -u root -p test
UPDATE crawler_wx_article
SET retry_count = 1000000,
    error_message = CONCAT(error_message, ' | 用户指示：被微信标记，永久放弃重试')
WHERE processed_at IS NULL AND retry_count >= 3;
```

原理：取数条件 `NOW() >= updated_at + retry_count×20分钟`，retry_count=1000000 等效约190年退避。如需恢复某篇：`UPDATE crawler_wx_article SET retry_count=0, error_message=NULL WHERE article_key='<url>';`

### 4.4 注意事项

- ⚠️ **验证脚本和批次任务绝对不能同时运行**（10:51 实测事故：有头验证窗口未关时启动批次，两个浏览器实例挂同一档案，会话状态被破坏 → 批次全拦）。正确顺序：**跑验证 → 窗口关闭、脚本退出 → 再跑批次**；反之亦然。

- **不要删除 `.wxchat_browser_profile/`**，否则下次又需要人工验证
- `poc_sid` 有有效期（微信侧控制，实测数天内有效）；若批量再次全部失败且日志出现"环境异常"，**重跑 4.1 即可**
- 验证时弹出的是受控浏览器窗口，**在它里面完成滑块**，不要在自己日常 Chrome 里验证（cookie 不互通）
- 长期预防：保持反限流配置（默认每篇随机暂停 20~50 秒），避免单次批量过多触发新一批风控

## 5. 配套防御机制（src/wxchat/processor.py）

| 机制 | 配置/常量 | 说明 |
|---|---|---|
| **浏览器会话复用** | 固定代码（`_get_context`/`close_browser`） | **批次只启动一次浏览器，文章间仅新开页面**——每篇新开浏览器进程会触发风控（10:35 实测连败，复用后 3/3 全过） |
| **早期拦截页检测** | 固定代码 | 打开页面即检测"环境异常"，命中立刻失败（省约40秒/篇），日志记录 `页面为微信验证页（早期检测）` |
| 假 PDF 检测 | `MIN_VALID_PDF_SIZE=100KB` | 生成后校验文件大小，拦截页不上传 |
| 熔断 | `FAKE_PDF_CIRCUIT_BREAKER=5` | 连续 5 篇假 PDF → 判定风控，中止本次运行 |
| 单次尝试 | （2026-09-05 起固定行为） | 一次运行内每篇只试 1 次，不运行内重试 |
| 跨运行退避 | `RETRY_BACKOFF_MINUTES=20` | 失败 N 次需等 N×20 分钟才被再次扫描（retry_count 记账在 `crawler_wx_article` / `new_wx_article`） |
| 前科文章垫底 | 取数 SQL `ORDER BY COALESCE(s.retry_count,0) ASC` | 有失败记录的文章排最后处理，避免开局撞墙 |
| 随机延时 | `WXCHAT_DOWNLOAD_DELAY` / `WXCHAT_DOWNLOAD_DELAY_MAX`（默认 5/50，当前 20/50） | 每篇之间随机暂停，日志打印 `⏸️ 随机暂停 N 秒` |
| 持久化档案 | `WXCHAT_BROWSER_PROFILE`（默认 `./.wxchat_browser_profile`） | 保存验证 cookie，无头复用 |
| 拟真参数 | 固定代码 | 系统 Chrome（channel=chrome）+ 隐藏 webdriver + 真实 UA |

## 6. 相关文件索引

| 文件 | 用途 |
|---|---|
| `test/manual/wxchat/wxchat_verify_once.py` | **一次性人工验证（核心解法）** |
| `test/diagnostic/probe_wechat_block.py` | 多配置对比探针（诊断风控维度） |
| `test/diagnostic/probe_wechat_profile.py` | 无头/有头 + cookie 档案状态探针 |
| `test/diagnostic/probe_wechat_warmup.py` | 首页暖场种 cookie 探针 |
| `test/diagnostic/verify_fake_pdf_mechanisms.py` | 防御机制 9 项断言自检 |
| `test/manual/wxchat/test_crawler_wxchat_single.py` | 单篇文章端到端测试（--url/--limit/--skip-upload） |
| `src/wxchat/processor.py` | `PDFGenerator._launch_stealth_browser`（浏览器启动核心） |
| `docs/active/PRIVATE_MESSAGE_SOLUTION.md` 等历史文档 | 相关背景 |

## 7. 历史坑位备注（排查时容易再踩）

1. **逐篇日志曾整体消失**：`processor.py` 曾用裸 `logging.getLogger(__name__)`（无 handler），INFO 全部丢弃；已改为 `get_logger`（写 `logs/app.log` + 控制台）。若日志再失踪，先查各模块 logger 是否走 `get_logger`。
2. **每篇文章的链接必须出现在日志里**：`📄 开始处理文章` 下方的 `链接:` / `文章链接:` 两行（2026-09-05 需求），排查时直接 `grep "链接:" logs/app.log`。
3. **控制台中文乱码**：Windows GBK 控制台打印 UTF-8 中文/emoji 会崩或乱码，诊断脚本统一 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`。
4. **Playwright 持久化 context 的 UA**：只能在 `launch_persistent_context(..., user_agent=...)` 传入，`context.new_page()` 不接受该参数。
5. **状态表与爬虫表 JOIN 必须显式 `COLLATE utf8mb4_0900_ai_ci`**，否则混合排序规则报错 1267。
6. **"main.py 必败、测试脚本必过"是取样偏差，不是代码差异**（2026-09-05 11:50 实锤）：测试脚本调的就是同一个 `_process_single_article`，浏览器/档案/UA 完全相同（日志可证）。差别只在**各自第一篇撞上的文章不同**——main.py 按排序总是先撞被记分的长链文章，且每次都在第一篇失败后被人工中断，从未走到干净文章；测试脚本/探针恰好都在访问干净的短链文章。同一进程四轮对照实验（有/无裸 Chromium 预检）全部被拦、同刻干净短链通过，证明与调度代码无关。**下次再遇到"某个入口全失败"，先对比两边实际访问的文章清单，再怀疑代码。**（二分实验脚本：`test/diagnostic/bisect_main_vs_test.py`，可传 URL 参数、`BISECT_FULL=1` 跑完整四轮）
