"""
年份提取工具模块
从年报标题中提取年份信息
"""
import re


def extract_year(title):
    """
    从标题中提取年份
    
    Args:
        title: 年报标题，如 "金风科技：2024年年度报告2"
    
    Returns:
        int or None: 提取到的年份，如果提取失败返回None
    """
    if not title:
        return None
    
    # 匹配年份模式：4位数字 + "年"
    pattern = r'(\d{4})年'
    match = re.search(pattern, title)
    
    if match:
        try:
            year = int(match.group(1))
            # 年份合理性检查（1900-2100）
            if 1900 <= year <= 2100:
                return year
        except ValueError:
            pass
    
    return None


def extract_year_from_date(date_str):
    """
    从日期字符串中提取年份
    
    Args:
        date_str: 日期字符串，如 "2024-03-29"
    
    Returns:
        int or None: 提取到的年份
    """
    if not date_str:
        return None
    
    # 匹配年份模式：开头4位数字
    pattern = r'^(\d{4})'
    match = re.match(pattern, date_str)
    
    if match:
        try:
            year = int(match.group(1))
            if 1900 <= year <= 2100:
                return year
        except ValueError:
            pass
    
    return None

