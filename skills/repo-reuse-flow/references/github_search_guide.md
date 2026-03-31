# GitHub 搜索技巧指南

## 基本搜索语法

### 按名称搜索
```
repo:name          # 仓库名包含 name
user:name          # 用户名包含 name
org:name           # 组织名包含 name
```

### 按内容搜索
```
in:name            # 在仓库名中搜索
in:description     # 在描述中搜索
in:readme          # 在 README 中搜索
in:topics          # 在话题中搜索
```

### 排序和筛选
```
stars:>=1000       # 至少 1000 stars
forks:>=100        # 至少 100 forks
language:Python     # Python 语言
pushed:>2024-01-01 # 最近更新
created:>2020-01-01 # 创建时间
```

## 组合搜索示例

### 找高质量的 REST API 框架
```
REST API framework language:Python stars:>=5000
```

### 找最近活跃的项目
```
FastAPI pushed:>2024-01-01 language:Python stars:>=1000
```

### 找特定功能的库
```
authentication JWT language:Python stars:>=100
```

### 找工具类项目
```
utils library language:Python stars:>=500
```

## 高级搜索

### 排除特定词
```
python framework -django -flask
```

### 精确匹配
```
"exact phrase" in:name
```

### 按仓库大小
```
size:>=1000         # 至少 1MB
size:<=500          # 最多 500KB
```

### 按许可证
```
license:MIT
license:Apache-2.0
```

## 搜索建议

1. **先用宽泛关键词**，再逐步缩小范围
2. **关注 README**，了解项目功能
3. **检查最近更新时间**，避免使用已停止维护的项目
4. **查看 issue 数量**，活跃项目通常有合理的 issue 数
5. **检查 CI/CD**，有自动化测试的项目更可靠

## 推荐搜索组合

| 场景 | 搜索关键词 |
|------|-----------|
| Web 框架 | `web framework language:Python stars:>=5000` |
| CLI 工具 | `CLI tool language:Python stars:>=1000` |
| 数据处理 | `data processing library language:Python stars:>=2000` |
| REST API | `REST API framework language:Python stars:>=3000` |
| 认证授权 | `authentication JWT library language:Python stars:>=1000` |
