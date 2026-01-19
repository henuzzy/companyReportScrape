# 打包说明文档

## 概述

本文档说明如何将项目打包成独立的exe文件，方便分发给其他用户使用。

## 前置要求

1. **Python环境**：Python 3.7+
2. **安装PyInstaller**：
   ```bash
   pip install pyinstaller
   ```

## 打包步骤

### 方法一：使用打包脚本（推荐）

1. **运行打包脚本**：
   ```bash
   python build_exe.py
   ```

2. **等待打包完成**，打包完成后exe文件位于 `dist/companyReportScrape.exe`

### 方法二：使用PyInstaller命令

1. **直接使用spec文件打包**：
   ```bash
   pyinstaller build_exe.spec --clean
   ```

2. **或者使用命令行参数**：
   ```bash
   pyinstaller --onefile --windowed --name companyReportScrape --add-data "config/config.json;config" --exclude-module matplotlib --exclude-module numpy --exclude-module pandas main.py
   ```

## 打包配置说明

### build_exe.spec 文件说明

- **datas**: 包含的数据文件（如配置文件）
- **hiddenimports**: 需要显式导入的模块
- **excludes**: 排除的模块（减少体积）
- **console**: False - 不显示控制台窗口（GUI应用）
- **upx**: True - 使用UPX压缩（如果可用）

### 已排除的模块（减少体积）

- matplotlib, numpy, pandas, scipy（数据科学库）
- PIL（图像处理，本项目不需要）
- pytest, unittest（测试框架）
- 其他开发工具和测试模块

## 打包后的文件结构

```
dist/
└── companyReportScrape.exe  # 单个可执行文件（约20-30MB）
```

## 分发说明

### 分发给用户

1. **只需要分发exe文件**：
   - `dist/companyReportScrape.exe`

2. **用户首次运行时会自动创建**：
   - `downloads/` - 下载文件夹
   - `logs/` - 日志文件夹
   - `config/` - 配置文件（从exe中提取）

### 使用说明

1. 双击运行 `companyReportScrape.exe`
2. 在GUI界面中：
   - 点击"选择股票代码文件"按钮，选择包含股票代码的txt文件
   - （可选）设置起始年份和结束年份
   - 点击"开始下载"按钮
3. 下载的文件会保存在exe同目录下的 `downloads/` 文件夹中

## 文件大小优化

### 当前优化措施

1. **排除不需要的模块**：已排除matplotlib、numpy等大型库
2. **使用UPX压缩**：如果系统安装了UPX，会自动压缩
3. **单文件模式**：使用`--onefile`生成单个exe文件

### 进一步优化建议

1. **使用虚拟环境打包**：只安装必要的依赖
   ```bash
   python -m venv venv_build
   venv_build\Scripts\activate
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **移除调试信息**：确保代码中没有大量调试输出

3. **压缩exe文件**：使用UPX或其他压缩工具

## 常见问题

### 1. 打包失败：找不到模块

**解决方案**：
- 检查`hiddenimports`列表是否包含所需模块
- 确保所有依赖都已安装

### 2. exe文件太大

**解决方案**：
- 检查`excludes`列表，排除更多不需要的模块
- 使用虚拟环境，只安装必要的依赖
- 使用UPX压缩

### 3. 运行时缺少配置文件

**解决方案**：
- 检查`datas`配置是否正确
- 确保`config/config.json`文件存在

### 4. 运行时出现编码错误

**解决方案**：
- 确保Python环境支持GBK编码
- 检查代码中的编码处理逻辑

### 5. 杀毒软件误报

**解决方案**：
- PyInstaller打包的exe可能被误报为病毒
- 可以添加数字签名（需要证书）
- 或者告知用户添加到白名单

## 测试打包后的exe

1. **在干净的Windows系统上测试**：
   - 不要安装Python环境
   - 直接运行exe文件
   - 测试所有功能

2. **检查文件**：
   - 确认配置文件正确加载
   - 确认下载功能正常
   - 确认日志记录正常

## 更新打包

如果修改了代码，需要重新打包：

1. 清理之前的构建文件：
   ```bash
   python build_exe.py
   ```
   脚本会自动清理

2. 或者手动清理：
   ```bash
   rmdir /s /q build dist
   del companyReportScrape.spec
   ```

## 添加图标（可选）

1. **准备图标文件**：创建或下载 `icon.ico` 文件

2. **修改build_exe.spec**：
   ```python
   icon='icon.ico',  # 在EXE配置中添加
   ```

3. **重新打包**

## 参考资源

- [PyInstaller官方文档](https://pyinstaller.org/)
- [PyInstaller使用指南](https://pyinstaller.readthedocs.io/)

---

**最后更新**：2024年

