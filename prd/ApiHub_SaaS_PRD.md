# ApiHub — SaaS API 管理平台 MVP PRD

**版本**：v2.0
**日期**：2026-04-01

---

## 一、产品概述

ApiHub 是一个面向开发者的 SaaS API 管理平台。用户注册后获得 API Key，按调用量付费。

### 技术栈
- 前端：Next.js 14+ App Router + Tailwind CSS
- 后端：Python FastAPI + SQLite
- 支付：Stripe Checkout（测试模式，key 在 `.env.dev` 中）
- 认证：GitHub OAuth
- 图表：Recharts

### 核心用户旅程

```
访问定价页 → 选择套餐 → GitHub 登录 → 进入 Dashboard → 创建 API Key → 复制 Key → 查看用量 → 升级套餐 → Stripe 支付 → 查看发票
```

---

## 二、页面清单

| 编号 | 页面 | URL | 认证 |
|------|------|-----|------|
| P1 | 定价页 | `/pricing` | 否 |
| P2 | 登录 | `/login` | 否 |
| P3 | Dashboard | `/dashboard` | 是 |
| P4 | API Keys | `/dashboard/keys` | 是 |
| P5 | 账单管理 | `/dashboard/billing` | 是 |

首页 `/` 重定向到 `/pricing`。

---

## 三、页面详细定义

### P1 · 定价页 (`/pricing`)

定价页是公开页面，需要对搜索引擎友好（SSR），社交分享能看到标题和描述。

**导航栏**（所有页面共用）：
- 左侧 Logo，右侧根据登录状态显示不同内容
- 移动端用汉堡菜单，展开侧边抽屉

**定价卡片**：三档横向排列，移动端纵向堆叠

| 套餐 | 价格 | 额度 |
|------|------|------|
| Free | $0/月 | 1,000 次/月 |
| Pro | $29/月 | 50,000 次/月 |
| Enterprise | $199/月 | 500,000 次/月 |

每张卡片有套餐名、价格、特性列表、CTA 按钮。Pro 标记「Most Popular」。

**月付/年付切换**：切换时价格有过渡动画。年付折扣：Pro $24/月，Enterprise $166/月。

**FAQ**：5 个常见问题，手风琴折叠。

---

### P2 · 登录页 (`/login`)

居中卡片，`Continue with GitHub` 按钮。点击后走 GitHub OAuth 流程，授权成功后进入 Dashboard。

用户如果从某个需要登录的页面跳过来的，登录成功后应该回到那个页面。

---

### P3 · Dashboard (`/dashboard`)

需要登录，未登录跳转登录页。

**左侧边栏**（桌面端常驻，移动端隐藏用汉堡菜单）：
- 用户头像 + 用户名
- 导航：Overview / API Keys / Billing
- 底部 Logout

**概览卡片**（3 张）：
- 今日调用量（较昨日变化百分比）
- 月度用量（环形进度条）
- 当前套餐（Free 用户显示 Upgrade 按钮）

**用量图表**：
- 折线图，过去 7 天 / 30 天 / 90 天
- 三个 Tab 切换时间范围，切换时异步加载（显示 loading）
- 鼠标悬停显示 tooltip

**最近调用日志**：
- 表格：Time / Endpoint / Status / Latency
- 默认 20 条，支持按 Status 筛选、按 Endpoint 搜索（防抖）
- 用户的筛选和搜索条件在页面刷新后应该还在
- 每 30 秒自动刷新数据，但不应该把用户正在用的筛选条件重置掉

---

### P4 · API Keys 管理 (`/dashboard/keys`)

**Key 列表**：
- 表格：Name / Key（前 8 位 + ...）/ Created / Last Used / Actions
- Copy 按钮：复制完整 Key，复制后显示「✅ Copied」
- Delete 按钮：弹出确认对话框，确认后删除

**创建 API Key**（多步弹窗）：

点击 `+ Create New Key`，弹出弹窗：

1. **Step 1**：输入 Key 名称（必填）和用途描述（选填），点 Next
2. **Step 2**：选择权限（Read / Write / Delete / Admin，至少选一个），点 Create
3. **Step 3**：显示完整 API Key，提示「这是唯一一次看到完整 Key」，必须复制后才能关闭弹窗

在 Step 1 和 Step 2 之间来回切换时，之前填的内容不应该丢失。

---

### P5 · 账单管理 (`/dashboard/billing`)

**当前套餐**：套餐名 + 价格 + 额度 + 到期日 + `Change Plan` 按钮

**套餐变更弹窗**：
- 显示三个套餐卡片，当前套餐标记 `Current`
- 选择新套餐后，显示额度变化预览（数字增长动画）
- 升级 → 跳转 Stripe Checkout 支付
- 降级 → 确认后当前周期结束生效

**Stripe 支付**：
- 支付成功后回到账单页显示成功提示
- 支付取消后回到账单页显示取消提示

**发票列表**：
- 表格：Date / Amount / Status / Download PDF
- 分页，每页 10 条

**用量进度条**：
- 已用 / 额度，接近上限时变色警告

---

## 四、后端 API

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/login` | 重定向到 GitHub OAuth |
| GET | `/api/auth/callback` | OAuth 回调 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 当前用户信息 |

### API Keys
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/keys` | 用户的所有 Keys |
| POST | `/api/keys` | 创建 Key（返回完整 Key，仅此一次） |
| DELETE | `/api/keys/{key_id}` | 删除 Key |

### 用量
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/usage/summary` | 今日量 + 月度量 + 套餐 |
| GET | `/api/usage/chart?range=7d` | 图表数据 |
| GET | `/api/usage/logs?page=1&status=all&search=` | 日志（分页+筛选+搜索） |

### 账单
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/billing/current` | 当前套餐 |
| POST | `/api/billing/checkout` | 创建 Stripe Checkout Session |
| POST | `/api/billing/downgrade` | 降级 |
| GET | `/api/billing/invoices?page=1` | 发票列表 |
| POST | `/api/billing/webhook` | Stripe Webhook |

### 定价
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/pricing` | 套餐定价 |

---

## 五、数据模型

### users
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 用户 ID |
| github_id | INTEGER | GitHub ID |
| username | TEXT | 用户名 |
| email | TEXT | 邮箱 |
| avatar_url | TEXT | 头像 |
| plan | TEXT | 当前套餐（free/pro/enterprise） |
| stripe_customer_id | TEXT | Stripe 客户 ID |

### api_keys
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | Key ID |
| user_id | TEXT FK | 所属用户 |
| name | TEXT | Key 名称 |
| key_hash | TEXT | Key 哈希（存储用） |
| key_prefix | TEXT | Key 前缀（展示用） |
| permissions | TEXT | 权限（JSON） |

### usage_logs
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| user_id | TEXT FK | 用户 |
| endpoint | TEXT | 调用路径 |
| status_code | INTEGER | 状态码 |
| latency_ms | INTEGER | 延迟 |
| created_at | TEXT | 时间 |

### invoices
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 发票 ID |
| user_id | TEXT FK | 用户 |
| amount_cents | INTEGER | 金额（分） |
| status | TEXT | 状态 |
| pdf_url | TEXT | PDF 链接 |

---

## 六、Stripe 集成

- 使用 `.env.dev` 中的 Stripe 测试 key
- 测试卡号：`4242 4242 4242 4242`
- 三个套餐对应三个 Stripe Price
- Checkout 成功后回到 `/dashboard/billing`
- 通过 Webhook 更新用户套餐状态

---

## 七、测试数据

应用启动时灌入测试数据，确保页面有内容可看：
- 2 个用户（1 个 Pro，1 个 Free）
- 3 个 API Keys
- 90 天的调用日志（约 120 条，混合 2xx/4xx/5xx）
- 12 个月的发票记录

---

*ApiHub · MVP PRD v2.0 · 2026-04-01*
