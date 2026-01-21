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
    if not filename:
        return "unnamed"
    
    # 确保是字符串类型
    if not isinstance(filename, str):
        try:
            filename = str(filename, encoding='utf-8', errors='ignore')
        except:
            filename = str(filename)
    
    # Windows不允许的字符: < > : " / \ | ? *
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        if char in filename:
            filename = filename.replace(char, '_')
    
    # 去除首尾空格和点
    filename = filename.strip(' .')
    
    # 限制文件名长度（Windows最大260字符，但路径也会占用）
    if len(filename) > 200:
        filename = filename[:200]
    
    # 确保文件名可以安全地用于文件系统
    try:
        # 获取系统文件系统编码
        fs_encoding = sys.getfilesystemencoding() or 'utf-8'
        
        # 尝试将文件名编码为系统编码，如果失败则使用替换策略
        try:
            filename_bytes = filename.encode(fs_encoding, errors='strict')
            filename = filename_bytes.decode(fs_encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            filename_bytes = filename.encode(fs_encoding, errors='replace')
            filename = filename_bytes.decode(fs_encoding)
        
        # 如果编码后文件名变空或只有替换字符，使用安全名称
        if not filename or filename.strip() == '':
            # 尝试提取ASCII字符
            ascii_name = ''.join(c for c in filename if ord(c) < 128)
            if ascii_name:
                filename = ascii_name
            else:
                filename = "unnamed"
    except Exception:
        # 如果编码转换完全失败，使用ASCII安全字符
        try:
            filename = ''.join(c for c in filename if ord(c) < 128)
            if not filename:
                filename = "unnamed"
        except:
            filename = "unnamed"
    
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


def get_download_path(base_path, stock_code, market: str = 'CN'):
    """
    获取指定股票代码的下载路径
    
    路径结构示例：
        <base_path>/A股年报/000001/xxx.pdf
        <base_path>/港股年报/00700/xxx.pdf
        <base_path>/美股年报/AAPL/xxx.pdf
    
    Args:
        base_path: 下载基础路径（用户在GUI中选择，或配置中的download_base_path）
        stock_code: 股票代码
        market: 市场标识，'CN' / 'HK' / 'US'
    
    Returns:
        Path: 下载路径
    """
    # 不同市场的子目录名称
    market_dir_map = {
        'CN': 'A股年报',
        'HK': '港股年报',
        'US': '美股年报',
    }
    market_dir = market_dir_map.get(market, market)
    
    download_path = Path(base_path) / market_dir / stock_code
    download_path.mkdir(parents=True, exist_ok=True)
    return download_path

