# Git Commit Statistics Dashboard

加载 Excel 成员表、Git 提交记录和 GitHub ID 映射，按人员和部门统计代码贡献。

## 快速开始

```bash
# 1. 生成示例 Excel（可选，用你的真实数据替换后重新生成）
node generate_sample.js

# 2. 导出 Git 提交记录
./export_git_log.sh /path/to/your/repo > commits.json

# 3. 解析 GitHub ID 映射（需要 GitHub token）
python3 resolve_github_ids.py /path/to/your/repo ghp_xxxx

# 4. 启动页面
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080，点击"一键加载"或手动选择三个文件
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `index.html` | 单页应用，浏览器直接打开（需 HTTP 方式） |
| `export_git_log.sh` | 从 Git 仓库导出 commit 记录为 JSON |
| `resolve_github_ids.py` | 通过 GitHub API 解析作者的真实 GitHub ID |
| `generate_sample.js` | 生成示例 Excel 成员表 |
| `sample.xlsx` | 示例成员表（GitHub ID / 姓名 / 部门） |
| `chart.umd.min.js` | Chart.js 图表库（本地副本） |
| `xlsx.full.min.js` | SheetJS Excel 解析库（本地副本） |

## 三个数据文件

### ① Excel 成员表

三列：GitHub ID / 真实姓名 / 所属部门。支持 `.xlsx` `.xls` `.csv`。

> **提示：** 如果一个人有多个 GitHub ID，可以加第 4 列"别名"，多个别名用逗号分隔。例如：
> 
> | GitHub ID | 真实姓名 | 所属部门 | 别名 |
> |-----------|---------|---------|------|
> | wxsIcey   | wxsIcey | 某部门   | Icey,icey-dev |
>
> 匹配时系统会同时检查主 ID 和别名，提交量会自动合并到同一人。

### ② commits.json

由 `export_git_log.sh` 生成。JSON 数组，每条记录包含：

```json
{
  "hash": "abc123...",
  "author_name": "wangxiyuan",
  "author_email": "wangxiyuan1007@gmail.com",
  "date": "2026-07-01",
  "additions": 42,
  "deletions": 18
}
```

### ③ github_id_map.json

由 `resolve_github_ids.py` 生成。将 Git 作者映射到真实 GitHub ID：

```json
{
  "wangxiyuan|||wangxiyuan1007@gmail.com": "wangxiyuan",
  "Li Wang|||wangli858794774@gmail.com": "wangli"
}
```

## GitHub Token

`resolve_github_ids.py` 需要 GitHub API token。在 https://github.com/settings/tokens 创建一个，权限选 `read-only` 即可。

Token 也可以设到环境变量：

```bash
export GITHUB_TOKEN=ghp_xxxx
python3 resolve_github_ids.py /path/to/repo
```

## 匹配逻辑

页面加载三个文件后，按以下顺序将 Git 作者匹配到 Excel 成员：

1. **GitHub ID 映射**（`github_id_map.json`）—— 最可靠
2. **邮箱前缀匹配** —— `wangxiyuan@corp.com` → `wangxiyuan`
3. **姓名匹配** —— Git 作者名 == Excel 真实姓名
4. **作者名匹配** —— Git 作者名 == Excel GitHub ID

未匹配的作者显示在独立标签页。

## 时间筛选

支持预设周期（近 1 周 / 1 月 / 3 月 / 6 月 / 1 年）或自定义起止日期。切换后汇总卡片、表格、图表全部自动更新。

## 增量更新

`resolve_github_ids.py` 支持增量运行——已缓存的不重复请求，只处理新出现的作者和之前网络失败的。

## 依赖

- Python 3（`resolve_github_ids.py`）
- Node.js（`generate_sample.js`，仅生成示例 Excel 时用到）
- 浏览器，无其他后端依赖
