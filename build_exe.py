"""
打包脚本
用于将项目打包成exe文件
"""
import os
import sys
import shutil
import subprocess

def clean_build_dirs():
    """清理之前的构建文件"""
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理.spec文件生成的临时文件
    if os.path.exists('companyReportScrape.spec'):
        # 保留.spec文件，只清理临时文件
        pass

def check_pyinstaller():
    """检查PyInstaller是否已安装"""
    try:
        import PyInstaller
        print(f"PyInstaller版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("错误: PyInstaller未安装")
        print("请运行: pip install pyinstaller")
        return False

def build_exe():
    """执行打包"""
    print("=" * 50)
    print("开始打包项目为exe文件...")
    print("=" * 50)
    
    # 检查PyInstaller
    if not check_pyinstaller():
        return False
    
    # 清理之前的构建文件
    print("\n1. 清理之前的构建文件...")
    clean_build_dirs()
    
    # 使用spec文件打包
    print("\n2. 开始打包（使用build_exe.spec配置文件）...")
    try:
        result = subprocess.run(
            ['pyinstaller', 'build_exe.spec', '--clean'],
            check=True,
            capture_output=False
        )
        
        print("\n" + "=" * 50)
        print("打包完成！")
        print("=" * 50)
        print(f"\nexe文件位置: dist/companyReportScrape.exe")
        print(f"\n文件大小: {os.path.getsize('dist/companyReportScrape.exe') / (1024*1024):.2f} MB")
        print("\n提示:")
        print("1. 可以将dist/companyReportScrape.exe单独分发给用户")
        print("2. 用户首次运行时会在exe同目录下创建downloads和logs文件夹")
        print("3. 确保config.json配置文件已正确打包")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败: {e}")
        return False
    except FileNotFoundError:
        print("\n错误: 找不到pyinstaller命令")
        print("请确保PyInstaller已正确安装并在PATH中")
        return False

if __name__ == '__main__':
    success = build_exe()
    sys.exit(0 if success else 1)

