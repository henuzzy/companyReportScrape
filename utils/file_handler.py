"""
文件处理工具模块
处理文件读取、去重判断等功能
"""
import os
import sys
from pathlib import Path


def read_stock_codes(file_path):
    """
    读取股票代码文件（txt格式，每行一个代码）
    
    Args:
        file_path: 文件路径
    
    Returns:
        list: 股票代码列表，去除空行和重复项
    """
    codes = []
    
    if not os.path.exists(file_path):
        return codes
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                code = line.strip()
                if code and code not in codes:
                    codes.append(code)
    except Exception as e:
        # 使用logger而不是print，避免控制台编码问题
        import logging
        logger = logging.getLogger('company_report_scraper')
        try:
            logger.error(f"读取文件失败: {e}")
        except:
            pass  # 如果日志记录也失败，忽略错误
    
    return codes


def sanitize_filename(filename):
    """
    清理文件名，去除非法字符，确保编码正确（转换为系统编码）
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 清理后的文件名（系统编码，Windows上为GBK）
    """
    print(f"[编码调试] sanitize_filename - 输入: {repr(filename)}")
    
    if not filename:
        print(f"[编码调试] 文件名为空，返回unnamed")
        return "unnamed"
    
    # 确保是字符串类型
    original_type = type(filename)
    if not isinstance(filename, str):
        print(f"[编码调试] 文件名不是字符串类型: {original_type}")
        try:
            filename = str(filename, encoding='utf-8', errors='ignore')
            print(f"[编码调试] 转换为UTF-8字符串: {repr(filename)}")
        except:
            filename = str(filename)
            print(f"[编码调试] 强制转换为字符串: {repr(filename)}")
    else:
        print(f"[编码调试] 文件名已经是字符串类型")
    
    # Windows不允许的字符: < > : " / \ | ? *
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        if char in filename:
            filename = filename.replace(char, '_')
            print(f"[编码调试] 替换非法字符 '{char}' 为 '_'")
    
    # 去除首尾空格和点
    filename = filename.strip(' .')
    
    # 限制文件名长度（Windows最大260字符，但路径也会占用）
    if len(filename) > 200:
        filename = filename[:200]
        print(f"[编码调试] 文件名过长，截断为200字符")
    
    # 确保文件名可以安全地用于文件系统
    print(f"[编码调试] 开始编码转换...")
    print(f"[编码调试] 系统文件系统编码: {sys.getfilesystemencoding()}")
    
    try:
        # 获取系统文件系统编码
        fs_encoding = sys.getfilesystemencoding() or 'utf-8'
        
        # 尝试将文件名编码为系统编码，如果失败则使用替换策略
        print(f"[编码调试] 尝试编码为系统编码 ({fs_encoding})...")
        try:
            filename_bytes = filename.encode(fs_encoding, errors='strict')
            filename = filename_bytes.decode(fs_encoding)
            print(f"[编码调试] ✓ 编码转换成功: {repr(filename)}")
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            print(f"[编码调试] ✗ 严格编码失败: {type(e).__name__}: {e}")
            print(f"[编码调试] 使用replace模式重新编码...")
            filename_bytes = filename.encode(fs_encoding, errors='replace')
            filename = filename_bytes.decode(fs_encoding)
            print(f"[编码调试] ✓ 替换模式编码成功: {repr(filename)}")
        
        # 如果编码后文件名变空或只有替换字符，使用安全名称
        if not filename or filename.strip() == '':
            print(f"[编码调试] 编码后文件名为空，尝试提取ASCII字符")
            # 尝试提取ASCII字符
            ascii_name = ''.join(c for c in filename if ord(c) < 128)
            if ascii_name:
                filename = ascii_name
                print(f"[编码调试] ASCII文件名: {repr(filename)}")
            else:
                filename = "unnamed"
                print(f"[编码调试] 使用默认名称: unnamed")
    except Exception as e:
        print(f"[编码调试] ✗ 编码转换异常: {type(e).__name__}: {e}")
        # 如果编码转换完全失败，使用ASCII安全字符
        try:
            filename = ''.join(c for c in filename if ord(c) < 128)
            if not filename:
                filename = "unnamed"
            print(f"[编码调试] 使用ASCII安全字符: {repr(filename)}")
        except:
            filename = "unnamed"
            print(f"[编码调试] 使用默认名称: unnamed")
    
    print(f"[编码调试] sanitize_filename - 输出: {repr(filename)}")
    return filename


def is_file_downloaded(download_dir, filename):
    """
    检查文件是否已下载（去重判断）
    
    Args:
        download_dir: 下载目录
        filename: 文件名（不含扩展名或包含扩展名）
    
    Returns:
        bool: 如果文件已存在返回True，否则返回False
    """
    # 确保filename是.pdf格式
    if not filename.endswith('.pdf'):
        filename = filename + '.pdf'
    
    try:
        # 使用os.path.join避免Path对象的编码转换问题
        file_path = os.path.join(str(download_dir), filename)
        
        # 只检查.pdf文件，不检查.tmp文件
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return True
    except (OSError, UnicodeEncodeError, UnicodeDecodeError):
        # 如果编码错误，假设文件不存在
        return False
    
    return False


def get_download_path(base_path, stock_code):
    """
    获取指定股票代码的下载路径
    
    Args:
        base_path: 下载基础路径
        stock_code: 股票代码
    
    Returns:
        Path: 下载路径
    """
    download_path = Path(base_path) / stock_code
    download_path.mkdir(parents=True, exist_ok=True)
    return download_path

