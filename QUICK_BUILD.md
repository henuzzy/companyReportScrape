# 快速打包指南

## 一键打包

### 步骤1：安装PyInstaller
```bash
pip install pyinstaller
```

### 步骤2：运行打包脚本
```bash
python build_exe.py
```

### 步骤3：获取exe文件
打包完成后，exe文件位于：`dist/companyReportScrape.exe`

## 打包后的文件

- **单个exe文件**：`dist/companyReportScrape.exe`（约20-30MB）
- **无需其他文件**：配置文件已打包进exe

## 分发给用户

只需要将 `dist/companyReportScrape.exe` 文件发送给用户即可。

用户双击运行后，程序会自动创建：
- `downloads/` - 下载文件夹
- `logs/` - 日志文件夹

## 详细说明

更多信息请查看 `BUILD.md` 文件。

