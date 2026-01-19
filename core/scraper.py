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
                
                # 【调试日志】打印响应头信息
                print(f"[编码调试] 股票代码 {stock_code}, URL: {list_url}")
                print(f"[编码调试] HTTP状态码: {response.status_code}")
                print(f"[编码调试] Content-Type响应头: {response.headers.get('content-type', '未找到')}")
                print(f"[编码调试] requests自动检测的编码: {response.encoding}")
                print(f"[编码调试] 响应内容长度: {len(response.content)} 字节")
                
                # 检查状态码
                if response.status_code != 200:
                    safe_log_error("股票代码 %s URL %s 访问失败，状态码: %s", stock_code, list_url, response.status_code)
                    continue  # 尝试下一个URL格式
                
                # 尝试自动检测编码
                original_encoding = response.encoding
                print(f"[编码调试] 开始编码检测，原始编码: {original_encoding}")
                
                if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                    content_type = response.headers.get('content-type', '').lower()
                    print(f"[编码调试] Content-Type (lower): {content_type}")
                    
                    if 'charset' in content_type:
                        charset = content_type.split('charset=')[-1].split(';')[0].strip()
                        print(f"[编码调试] 从响应头提取的charset: {charset}")
                        response.encoding = charset
                    else:
                        print(f"[编码调试] 响应头中无charset，开始尝试常见编码")
                        for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                            try:
                                print(f"[编码调试] 尝试编码: {encoding}")
                                # 测试能否用该编码重新编码（这个方法有问题，但先看看）
                                test_text = response.text
                                test_text.encode(encoding)
                                print(f"[编码调试] ✓ 编码 {encoding} 测试通过")
                                response.encoding = encoding
                                break
                            except Exception as e:
                                print(f"[编码调试] ✗ 编码 {encoding} 测试失败: {e}")
                                continue
                        else:
                            print(f"[编码调试] 所有编码测试失败，使用默认UTF-8")
                            response.encoding = 'utf-8'
                
                print(f"[编码调试] 最终使用的编码: {response.encoding}")
                
                # 尝试解析HTML
                print(f"[编码调试] 开始使用BeautifulSoup解析HTML...")
                try:
                    # 重要：使用原始字节创建BeautifulSoup，避免requests自动解码的问题
                    # BeautifulSoup会从HTML内容中自动检测编码
                    print(f"[编码调试] 响应原始字节长度: {len(response.content)}")
                    print(f"[编码调试] 尝试使用原始字节创建BeautifulSoup...")
                    try:
                        # 方法1: 先解码为UTF-8字符串，再传给BeautifulSoup（使用html.parser避免lxml的编码问题）
                        # 因为response.encoding是gbk，我们需要手动解码
                        print(f"[编码调试] 使用GBK编码解码原始字节...")
                        html_text = response.content.decode('gbk', errors='replace')
                        print(f"[编码调试] 解码成功，文本长度: {len(html_text)}")
                        print(f"[编码调试] 使用html.parser解析（避免lxml的编码问题）...")
                        soup = BeautifulSoup(html_text, 'html.parser')
                        print(f"[编码调试] ✓ BeautifulSoup解析成功（GBK解码+html.parser）")
                    except Exception as e:
                        print(f"[编码调试] GBK解码失败: {e}")
                        # 方法2: 尝试使用原始字节和lxml
                        try:
                            print(f"[编码调试] 尝试使用原始字节+lxml...")
                            soup = BeautifulSoup(response.content, 'lxml')
                            print(f"[编码调试] ✓ BeautifulSoup解析成功（使用原始字节+lxml）")
                        except Exception as e2:
                            # 方法3: 使用已解码的文本
                            print(f"[编码调试] lxml也失败: {e2}")
                            print(f"[编码调试] 尝试使用已解码文本+html.parser...")
                            soup = BeautifulSoup(response.text, 'html.parser')
                            print(f"[编码调试] ✓ BeautifulSoup解析成功（使用已解码文本+html.parser）")
                except Exception as e:
                    print(f"[编码调试] ✗ BeautifulSoup解析失败: {type(e).__name__}: {e}")
                    print(f"[编码调试] 错误详情: {str(e)}")
                    raise  # 重新抛出异常
                
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
            print(f"[编码调试] 开始提取年报链接...")
            all_links = target_element.find_all('a', href=True)
            print(f"[编码调试] 找到 {len(all_links)} 个链接")
            
            for link_idx, link in enumerate(all_links):
                try:
                    print(f"[编码调试] 处理第 {link_idx + 1} 个链接...")
                    
                    # 获取链接文本（年报标题）
                    print(f"[编码调试] 提取链接文本...")
                    try:
                        # BeautifulSoup在解析GBK编码的HTML时，可能会返回包含错误编码的字符串
                        # 我们需要从原始字节重新解码，或者安全地处理文本
                        title = link.get_text(strip=True)
                        print(f"[编码调试] 原始链接文本: {repr(title[:50] if len(title) > 50 else title)}")
                        print(f"[编码调试] 链接文本类型: {type(title)}")
                        print(f"[编码调试] 链接文本长度: {len(title)}")
                        
                        # 尝试检查文本的编码情况
                        if isinstance(title, str):
                            # 检查是否包含无法编码的字符
                            try:
                                # 尝试编码为UTF-8，如果失败说明有问题
                                title_utf8 = title.encode('utf-8', errors='strict')
                                print(f"[编码调试] ✓ 链接文本可以正常编码为UTF-8")
                                title = title_utf8.decode('utf-8')
                            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                                print(f"[编码调试] ✗ 链接文本UTF-8编码失败: {type(e).__name__}: {e}")
                                # 如果UTF-8编码失败，说明文本可能包含GBK字符
                                # 尝试从GBK重新编码为UTF-8
                                try:
                                    # 先尝试按GBK编码，再按UTF-8解码（这可能不对，但先试试）
                                    # 更好的方法是：如果response是GBK，BeautifulSoup应该已经正确转换
                                    # 如果还有问题，使用replace模式
                                    title = title.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                                    print(f"[编码调试] 使用replace模式处理后的文本: {repr(title[:50])}")
                                except Exception as e2:
                                    print(f"[编码调试] ✗ 重新编码也失败: {e2}")
                                    # 最后尝试：只保留ASCII字符
                                    title = ''.join(c for c in title if ord(c) < 128)
                                    if not title:
                                        print(f"[编码调试] 文本变为空，跳过此链接")
                                        continue
                                    print(f"[编码调试] 使用ASCII安全文本: {repr(title[:50])}")
                    except Exception as e:
                        print(f"[编码调试] ✗ 提取链接文本失败: {type(e).__name__}: {e}")
                        import traceback
                        print(f"[编码调试] 错误堆栈:\n{traceback.format_exc()}")
                        continue
                    
                    if not title:
                        print(f"[编码调试] 链接文本为空，跳过")
                        continue
                    
                    # 获取href（BeautifulSoup会自动解码HTML实体，如&amp; -> &）
                    print(f"[编码调试] 提取链接href...")
                    href = link.get('href', '')
                    if not href:
                        print(f"[编码调试] href为空，跳过")
                        continue
                    
                    # 转换为绝对URL（虽然BeautifulSoup已经解码，但这里再确保一下）
                    detail_url = self.url_handler.make_absolute_url(href)
                    print(f"[编码调试] 详情页URL: {detail_url}")
                    
                    # 尝试从链接前后提取日期
                    # 查找链接前的日期文本（格式：YYYY-MM-DD）
                    date_str = None
                    try:
                        parent_text = link.parent.get_text() if link.parent else ""
                        # 在链接文本前查找日期
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', parent_text)
                        if date_match:
                            date_str = date_match.group(1)
                            print(f"[编码调试] 提取到日期: {date_str}")
                    except Exception as e:
                        print(f"[编码调试] 提取日期失败: {e}")
                    
                    # 提取年份（优先从标题，其次从日期）
                    print(f"[编码调试] 提取年份...")
                    year = extract_year(title)
                    if year is None and date_str:
                        # 从日期提取年份
                        year = int(date_str.split('-')[0])
                    print(f"[编码调试] 提取到年份: {year}")
                    
                    reports.append({
                        'date': date_str,
                        'title': title,
                        'detail_url': detail_url,
                        'year': year,
                        'stock_code': stock_code
                    })
                    print(f"[编码调试] ✓ 成功添加年报项: {title}")
                
                except Exception as e:
                    print(f"[编码调试] ✗ 解析年报项失败: {type(e).__name__}: {e}")
                    import traceback
                    print(f"[编码调试] 错误堆栈:\n{traceback.format_exc()}")
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
            print(f"[编码调试] 获取PDF链接 - 访问详情页: {detail_url}")
            response = requests.get(detail_url, headers=self.headers, timeout=self.timeout)
            
            print(f"[编码调试] 详情页HTTP状态码: {response.status_code}")
            print(f"[编码调试] 详情页Content-Type: {response.headers.get('content-type', '未找到')}")
            print(f"[编码调试] 详情页requests自动检测编码: {response.encoding}")
            
            # 尝试自动检测编码
            if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                content_type = response.headers.get('content-type', '').lower()
                if 'charset' in content_type:
                    charset = content_type.split('charset=')[-1].strip()
                    print(f"[编码调试] 详情页从响应头提取charset: {charset}")
                    response.encoding = charset
                else:
                    print(f"[编码调试] 详情页响应头无charset，尝试常见编码")
                    for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                        try:
                            response.text.encode(encoding)
                            print(f"[编码调试] 详情页使用编码: {encoding}")
                            response.encoding = encoding
                            break
                        except:
                            continue
                    else:
                        print(f"[编码调试] 详情页使用默认UTF-8")
                        response.encoding = 'utf-8'
            
            print(f"[编码调试] 详情页最终编码: {response.encoding}")
            
            if response.status_code != 200:
                safe_log_error("详情页访问失败 %s，状态码: %s", detail_url, response.status_code)
                return None
            
            print(f"[编码调试] 开始解析详情页HTML...")
            print(f"[编码调试] 详情页响应原始字节长度: {len(response.content)}")
            try:
                # 使用GBK解码后传给BeautifulSoup（使用html.parser避免lxml的编码问题）
                try:
                    print(f"[编码调试] 使用GBK编码解码详情页原始字节...")
                    html_text = response.content.decode('gbk', errors='replace')
                    print(f"[编码调试] 详情页解码成功，文本长度: {len(html_text)}")
                    print(f"[编码调试] 使用html.parser解析详情页（避免lxml的编码问题）...")
                    soup = BeautifulSoup(html_text, 'html.parser')
                    print(f"[编码调试] ✓ 详情页HTML解析成功（GBK解码+html.parser）")
                except Exception as e:
                    print(f"[编码调试] GBK解码失败: {e}")
                    # 备选方案
                    try:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        print(f"[编码调试] ✓ 详情页HTML解析成功（原始字节+html.parser）")
                    except Exception as e2:
                        print(f"[编码调试] 原始字节+html.parser失败: {e2}")
                        soup = BeautifulSoup(response.text, 'html.parser')
                        print(f"[编码调试] ✓ 详情页HTML解析成功（已解码文本+html.parser）")
            except Exception as e:
                print(f"[编码调试] ✗ 详情页HTML解析失败: {type(e).__name__}: {e}")
                raise
            
            # 查找下载链接
            # 格式: <a href="http://file.finance.sina.com.cn/.../xxx.PDF" target="_blank">下载公告</a>
            # BeautifulSoup会自动处理HTML实体，所以href已经是解码后的
            all_links = soup.find_all('a', href=True)
            
            # 方法1: 查找所有以.pdf结尾的链接（不区分大小写）
            print(f"[编码调试] 开始查找PDF链接，共有 {len(all_links)} 个链接")
            for link_idx, link in enumerate(all_links):
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    print(f"[编码调试] 检查链接 {link_idx + 1}: {repr(href)}")
                    
                    # BeautifulSoup已经自动解码了HTML实体，但为了保险再解码一次
                    href = html.unescape(href)
                    print(f"[编码调试] 解码后href: {repr(href)}")
                    
                    # 检查是否以.pdf结尾（不区分大小写）
                    if href.upper().endswith('.PDF') or href.lower().endswith('.pdf'):
                        print(f"[编码调试] ✓ 找到PDF链接: {href}")
                        return href
                except Exception as e:
                    print(f"[编码调试] ✗ 处理链接时出错: {type(e).__name__}: {e}")
                    import traceback
                    print(f"[编码调试] 错误堆栈:\n{traceback.format_exc()}")
                    continue
            
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

