# 工单查询与导入工具

通过传票号查询整机工单产品型号信息，并导入到 ATE 系统。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 传票号查询 | 登录生产管理系统，查询整机工单对应的产品型号、客户代码、工单状态等信息 |
| 自动提取关键词 | 从产品型号中自动提取 HPC/SPC 开头的信息作为匹配名称 |
| 手动搜索匹配 | 支持修改匹配名称后在 ATE 系统中搜索对应产测属性 |
| NR01 过滤 | 勾选「仅显示 NR01 开头」快速过滤匹配列表 |
| 一键导入 | 手动选择匹配项后导入到 ATE 系统，结果显示在底部 |
| 配置自动保存 | 首次输入账户密码后自动保存到 `config.ini`，下次打开自动填入 |

## 快速开始

### 运行环境

- Windows 10/11
- Python 3.8+（调试运行需要；编译后的 exe 无需 Python）

### 调试运行

双击 `scripts/run.bat`，或命令行执行：

```bash
pip install -r src/requirements.txt
python src/workorder_app.py
```

### 配置文件

编辑 `src/config.ini` 设置默认账户、密码和服务器地址：

```ini
[login]
account = your_account
password = your_password

[server]
base_url = https://192.168.96.248
```

> **提示：** 运行 exe 时，首次输入账户密码并点击查询后，会自动保存到 exe 同级目录的 `config.ini`，下次打开自动填入。

## 使用流程

```
1. 填写账户、密码、传票号
        │
        ▼
2. 点击「查询」(Enter)
   ── 登录生产管理系统，查询并显示产品型号信息
   ── 自动提取 HPC/SPC 关键词填入匹配名称
        │
        ▼
3. 如需修改「匹配名称」，手动编辑后点击「搜索匹配」(Ctrl+F)
   ── 登录 ATE 系统，按关键词过滤产测属性列表
   ── 可勾选「仅显示 NR01 开头」进一步过滤
        │
        ▼
4. 从列表选择正确的产测属性
        │
        ▼
5. 点击「导入」(Ctrl+I)
   ── 执行导入，结果显示在底部区域
```

## 编译打包

### 一键编译

双击 `scripts/build.bat`，脚本会自动：

1. 创建 `.venv` 虚拟环境（首次运行）
2. 安装依赖和 PyInstaller
3. 使用 `src/WorkorderTool.spec` 编译打包

编译后生成的 exe 在 `dist/WorkorderTool.exe`，可直接分发给别人使用。

### 清理编译产物

双击 `scripts/clean.bat`。

## GitHub 自动编译

项目配置了 GitHub Actions（`.github/workflows/build.yml`）：

- **打 Tag 自动发布**：推送 `v*` 格式的 tag 自动编译并创建 Release
- **手动触发**：GitHub 仓库 → Actions → Run workflow

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 项目结构

```
├── src/                      # 源码
│   ├── workorder_app.py      # 主应用
│   ├── config.ini            # 配置文件（账户/密码/服务器）
│   ├── app_icon.ico          # 应用图标
│   ├── app_icon.png          # 应用图标 PNG
│   ├── requirements.txt      # Python 依赖
│   └── WorkorderTool.spec    # PyInstaller 编译配置
├── scripts/                  # 运行脚本
│   ├── run.bat               # 调试运行
│   ├── build.bat             # 编译打包
│   └── clean.bat             # 清理产物
├── .github/workflows/
│   └── build.yml             # GitHub Actions CI/CD
├── .gitignore
└── README.md
```

## 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 查询 |
| `Ctrl+F` | 搜索匹配 |
| `Ctrl+I` | 导入 |
