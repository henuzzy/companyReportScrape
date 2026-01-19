"""
爬虫核心模块
解析年报列表页和详情页，提取PDF下载链接
"""
import html
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from utils.config import get_config
from utils.logger import get_logger, safe_log_error
from utils.year_extractor import extract_year
from core.url_handler import URLHandler

logger = get_logger()


class ReportScraper:
    """年报爬虫"""
    
    def __init__(self):
        self.config = get_config()
        self.url_handler = URLHandler()
        self.timeout = self.config.get_request_timeout()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36'
        }
    
    def get_report_list(self, stock_code):
        """
        获取年报列表
        尝试所有URL格式，直到找到有数据的为止
        
        Args:
            stock_code: 股票代码
        
        Returns:
            list: 年报信息列表，每个元素包含 date, title, detail_url, year
        """
        url_formats = self.config.get_url_formats()
        
        # 尝试所有URL格式
        for url_format in url_formats:
            try:
                list_url = url_format.format(code=stock_code)
                
                response = requests.get(list_url, headers=self.headers, timeout=self.timeout)
                
                # 检查状态码
                if response.status_code != 200:
                    safe_log_error("股票代码 %s URL %s 访问失败，状态码: %s", stock_code, list_url, response.status_code)
                    continue  # 尝试下一个URL格式
                
                # 尝试自动检测编码
                if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                    content_type = response.headers.get('content-type', '').lower()
                    if 'charset' in content_type:
                        charset = content_type.split('charset=')[-1].split(';')[0].strip()
                        response.encoding = charset
                    else:
                        for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                            try:
                                test_text = response.text
                                test_text.encode(encoding)
                                response.encoding = encoding
                                break
                            except:
                                continue
                        else:
                            response.encoding = 'utf-8'
                
                # 解析HTML（使用GBK解码+html.parser避免lxml的编码问题）
                try:
                    html_text = response.content.decode('gbk', errors='replace')
                    soup = BeautifulSoup(html_text, 'html.parser')
                except Exception:
                    try:
                        soup = BeautifulSoup(response.content, 'html.parser')
                    except Exception:
                        soup = BeautifulSoup(response.text, 'html.parser')
                
                # 检查是否有"暂时没有数据"的提示
                if soup.find('td', string=re.compile(r'暂时没有数据|暂无数据')):
                    safe_log_error("股票代码 %s URL %s 显示暂时没有数据", stock_code, list_url)
                    continue  # 尝试下一个URL格式
                
                # 解析年报列表
                reports = self._parse_report_list(soup, stock_code)
                
                # 如果找到了年报列表，返回结果
                if reports:
                    return reports
                else:
                    # 没找到年报，尝试下一个URL格式
                    safe_log_error("股票代码 %s URL %s 未找到年报列表", stock_code, list_url)
                    continue
            
            except Exception as e:
                safe_log_error("股票代码 %s URL %s 获取年报列表失败: %s", stock_code, url_format, str(e))
                continue  # 尝试下一个URL格式
        
        # 所有URL格式都失败了
        safe_log_error("股票代码 %s 所有URL格式都失败，未找到年报列表", stock_code)
        return []
    
    def _parse_report_list(self, soup, stock_code):
        """
        解析年报列表页面
        
        Args:
            soup: BeautifulSoup对象
            stock_code: 股票代码
        
        Returns:
            list: 年报信息列表
        """
        reports = []
        
        try:
            # 方法1: 查找 <div class="datelist"><ul>
            datelist_div = soup.find('div', class_='datelist')
            target_element = None
            
            if datelist_div:
                ul = datelist_div.find('ul')
                if ul:
                    target_element = ul
            
            # 方法2: 如果在div中找不到，尝试查找包含"日期列表"文本的元素
            if not target_element:
                # 查找包含"日期列表"文本的td或div
                for tag in soup.find_all(['td', 'div']):
                    text = tag.get_text()
                    if '日期列表' in text or '年度报告' in text:
                        # 在这个元素内查找所有链接
                        target_element = tag
                        break
            
            # 方法3: 如果还是找不到，尝试在整个页面中查找包含年度报告链接的区域
            if not target_element:
                # 查找包含多个年度报告链接的父元素
                all_links = soup.find_all('a', href=re.compile(r'vCB_AllBulletinDetail|ndbg'))
                if all_links:
                    # 找到这些链接的共同父元素
                    parent = all_links[0].parent
                    for _ in range(3):  # 最多向上查找3层
                        if parent:
                            sibling_links = parent.find_all('a', href=re.compile(r'vCB_AllBulletinDetail|ndbg'))
                            if len(sibling_links) >= 3:  # 如果找到至少3个链接，可能是年报列表
                                target_element = parent
                                break
                            parent = parent.parent
            
            if not target_element:
                safe_log_error("股票代码 %s 未找到年报列表元素", stock_code)
                return reports
            
            # 使用BeautifulSoup提取所有链接（会自动处理HTML实体）
            all_links = target_element.find_all('a', href=True)
            
            for link in all_links:
                try:
                    # 获取链接文本（年报标题）
                    title = link.get_text(strip=True)
                    if not title:
                        continue
                    
                    # 确保title是有效的UTF-8字符串
                    if isinstance(title, str):
                        try:
                            title.encode('utf-8', errors='strict')
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            title = title.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                    
                    # 获取href（BeautifulSoup会自动解码HTML实体，如&amp; -> &）
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # 转换为绝对URL
                    detail_url = self.url_handler.make_absolute_url(href)
                    
                    # 尝试从链接前后提取日期
                    date_str = None
                    try:
                        parent_text = link.parent.get_text() if link.parent else ""
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', parent_text)
                        if date_match:
                            date_str = date_match.group(1)
                    except Exception:
                        pass
                    
                    # 提取年份（优先从标题，其次从日期）
                    year = extract_year(title)
                    if year is None and date_str:
                        year = int(date_str.split('-')[0])
                    
                    reports.append({
                        'date': date_str,
                        'title': title,
                        'detail_url': detail_url,
                        'year': year,
                        'stock_code': stock_code
                    })
                
                except Exception as e:
                    safe_log_error("解析年报项失败 %s: %s", stock_code, str(e))
                    continue
        
        except Exception as e:
            safe_log_error("解析年报列表失败 %s: %s", stock_code, str(e))
        
        return reports
    
    def get_pdf_url(self, detail_url):
        """
        从详情页获取PDF下载链接
        
        Args:
            detail_url: 详情页URL
        
        Returns:
            str or None: PDF下载URL，如果获取失败返回None
        """
        try:
            response = requests.get(detail_url, headers=self.headers, timeout=self.timeout)
            
            # 尝试自动检测编码
            if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                content_type = response.headers.get('content-type', '').lower()
                if 'charset' in content_type:
                    charset = content_type.split('charset=')[-1].strip()
                    response.encoding = charset
                else:
                    for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                        try:
                            response.text.encode(encoding)
                            response.encoding = encoding
                            break
                        except:
                            continue
                    else:
                        response.encoding = 'utf-8'
            
            if response.status_code != 200:
                safe_log_error("详情页访问失败 %s，状态码: %s", detail_url, response.status_code)
                return None
            
            # 解析HTML（使用GBK解码+html.parser避免lxml的编码问题）
            try:
                html_text = response.content.decode('gbk', errors='replace')
                soup = BeautifulSoup(html_text, 'html.parser')
            except Exception:
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                except Exception:
                    soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找下载链接
            all_links = soup.find_all('a', href=True)
            
            # 查找所有以.pdf结尾的链接（不区分大小写）
            for link in all_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                # BeautifulSoup已经自动解码了HTML实体，但为了保险再解码一次
                href = html.unescape(href)
                
                # 检查是否以.pdf结尾（不区分大小写）
                if href.upper().endswith('.PDF') or href.lower().endswith('.pdf'):
                    return href
            
            # 如果没找到，记录错误
            safe_log_error("未找到PDF下载链接 %s", detail_url)
            return None
        
        except Exception as e:
            safe_log_error("获取PDF链接失败 %s: %s", detail_url, str(e))
            return None
    
    def filter_reports_by_year(self, reports, start_year=None, end_year=None):
        """
        根据年份范围过滤年报
        
        Args:
            reports: 年报列表
            start_year: 起始年份（包含）
            end_year: 结束年份（包含）
        
        Returns:
            list: 过滤后的年报列表
        """
        if start_year is None and end_year is None:
            return reports
        
        filtered = []
        for report in reports:
            year = report.get('year')
            if year is None:
                # 如果没有年份信息，根据是否指定年份范围决定是否包含
                if start_year is None and end_year is None:
                    filtered.append(report)
                continue
            
            if start_year is not None and year < start_year:
                continue
            if end_year is not None and year > end_year:
                continue
            
            filtered.append(report)
        
        return filtered

