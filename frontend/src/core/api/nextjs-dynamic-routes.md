# Next.js App Router 动态路由语法完整指南

## 官方文档验证

App Router 的动态路由语法仅有 **3 种** 核心语法。但是变幻无穷，功能灵活。

***

## 📋 动态路由语法清单

| 语法             | 名称          | 匹配示例                                           | 参数类型                    |
| -------------- | ----------- | ---------------------------------------------- | ----------------------- |
| `[param]`      | **动态段**     | `/chats/123` → `param="123"`                   | `string`                |
| `[...param]`   | **捕获所有段**   | `/a/b/c` → `param=["a","b","c"]`               | `string[]`              |
| `[[...param]]` | **可选捕获所有段** | `/a/b` 或 `/` → `param=["a","b"]` 或 `undefined` | `string[] \| undefined` |

***

## 1️⃣ 动态段 `[param]`

**语法**：单个中括号包裹参数名

```
app/
└── blog/
    └── [slug]/
        └── page.tsx
```

**匹配示例**：

| 访问 URL              | 参数值                       |
| ------------------- | ------------------------- |
| `/blog/hello-world` | `{ slug: "hello-world" }` |
| `/blog/123`         | `{ slug: "123" }`         |

**代码示例**：

```typescript
export default async function Page({ params }: { params: { slug: string } }) {
  const { slug } = await params; // Next.js 15+ 需使用 await
  return <h1>Post: {slug}</h1>;
}
```

***

## 2️⃣ 捕获所有段 `[...param]`

**语法**：三个点 + 参数名，包裹在中括号内

```
app/
└── docs/
    └── [...slug]/
        └── page.tsx
```

**匹配示例**：

| 访问 URL                 | 参数值                               |
| ---------------------- | --------------------------------- |
| `/docs/intro`          | `{ slug: ["intro"] }`             |
| `/docs/guide/chapter1` | `{ slug: ["guide", "chapter1"] }` |
| `/docs/a/b/c/d`        | `{ slug: ["a", "b", "c", "d"] }`  |

**代码示例**：

```typescript
export default async function Page({ params }: { params: { slug: string[] } }) {
  const { slug } = await params;
  return <h1>Path: {slug.join('/')}</h1>;
}
```

***

## 3️⃣ 可选捕获所有段 `[[...param]]`

**语法**：双中括号 + 三个点 + 参数名

```
app/
└── docs/
    └── [[...slug]]/
        └── page.tsx
```

**匹配示例**：

| 访问 URL                 | 参数值                               |
| ---------------------- | --------------------------------- |
| `/docs`                | `{ slug: undefined }` ✅           |
| `/docs/intro`          | `{ slug: ["intro"] }`             |
| `/docs/guide/chapter1` | `{ slug: ["guide", "chapter1"] }` |

**代码示例**：

```typescript
export default async function Page({ params }: { params: { slug?: string[] } }) {
  const { slug } = await params;
  if (!slug) {
    return <h1>Docs Home</h1>;
  }
  return <h1>Path: {slug.join('/')}</h1>;
}
```

***

## 🔀 组合使用示例

### 示例 1：嵌套动态路由

```
app/
└── shop/
    └── [category]/
        └── [product]/
            └── page.tsx
```

| URL                           | 参数                                                  |
| ----------------------------- | --------------------------------------------------- |
| `/shop/electronics/iphone-15` | `{ category: "electronics", product: "iphone-15" }` |

### 示例 2：动态段 + 捕获所有

```
app/
└── docs/
    └── [version]/
        └── [...path]/
            └── page.tsx
```

| URL                       | 参数                                               |
| ------------------------- | ------------------------------------------------ |
| `/docs/v1/intro`          | `{ version: "v1", path: ["intro"] }`             |
| `/docs/v2/guide/chapter1` | `{ version: "v2", path: ["guide", "chapter1"] }` |

### 示例 3：复杂组合

```
app/
└── [lang]/
    └── docs/
        └── [[...slug]]/
            └── page.tsx
```

| URL              | 参数                                |
| ---------------- | --------------------------------- |
| `/en/docs`       | `{ lang: "en", slug: undefined }` |
| `/zh/docs/guide` | `{ lang: "zh", slug: ["guide"] }` |

***

## ⚠️ 注意事项

### 1. 命名冲突

```
❌ 错误：同一层级不能有多个捕获所有段
app/
├── [...a]/
└── [...b]/

✅ 正确：可以混合动态段和捕获所有
app/
└── [id]/
    └── [...files]/
```

### 2. 优先级顺序

```
静态路由 > 动态段 > 捕获所有段
```

例如：

```
app/
├── help/          # 静态路由（最高优先级）
├── [id]/          # 动态段
└── [...catch]/    # 捕获所有段（最低优先级）
```

### 3. 参数获取方式

**Next.js 15+**（推荐）：

```typescript
export default async function Page({ params }: { params: { id: string } }) {
  const { id } = await params; // 需要 await
}
```

**Next.js 13-14**：

```typescript
export default function Page({ params }: { params: { id: string } }) {
  const { id } = params; // 直接解构
}
```

***

## 📊 语法对比表

| 特性          | `[param]` | `[...param]` | `[[...param]]`          |
| ----------- | --------- | ------------ | ----------------------- |
| 匹配层级        | 单段        | 多段           | 多段（可选）                  |
| 参数类型        | `string`  | `string[]`   | `string[] \| undefined` |
| 必须存在        | ✅         | ✅            | ❌                       |
| 匹配 `/a`     | ✅         | ✅            | ✅                       |
| 匹配 `/a/b/c` | ❌         | ✅            | ✅                       |
| 匹配根路径 `/`   | ❌         | ❌            | ✅                       |

***

## 🎯 实际项目中的应用

### 项目中看到的路由示例：

| 路由文件夹                  | 匹配 URL 示例                        | 用途            |
| ---------------------- | -------------------------------- | ------------- |
| `[...all]`             | `/api/auth/*`                    | 统一处理所有认证请求    |
| `[thread_id]`          | `/workspace/chats/{任意 ID}`       | 显示特定聊天会话      |
| `[agent_name]`         | `/workspace/agents/{任意名称}`       | 显示特定 Agent 页面 |
| `[[...artifact_path]]` | `/artifacts` 或 `/artifacts/任意路径` | 处理可选的文件路径     |

***

## 📚 官方文档参考

- **Next.js 官方文档**：[Dynamic Route Segments](https://nextjs.org/docs/routing/dynamic-routes)
- **Next.js 15 文档**：[Routing: Dynamic Routes](https://nextjs.org/docs/15/pages/building-your-application/routing/dynamic-routes)
- **GitHub 源码文档**：[Dynamic Routes](https://github.com/vercel/next.js/blob/main/docs/01-app/03-api-reference/03-file-conventions/dynamic-routes.mdx)

***

## 🏁 总结

Next.js App Router 的动态路由语法共有 **3 种** 核心模式，通过组合这些模式，可以构建任何复杂的路由结构：

1. **`[param]`** - 单段动态参数
2. **`[...param]`** - 多段捕获所有参数
3. **`[[...param]]`** - 可选的多段捕获所有参数

这些语法是 Next.js App Router 的核心特性，使前端路由管理更加灵活和强大。
