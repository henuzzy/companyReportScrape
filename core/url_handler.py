"""
URL处理模块
支持多种URL格式，按顺序尝试
"""
import html
import requests
from utils.config import get_config
from utils.logger import get_logger, safe_log_error

logger = get_logger()


class URLHandler:
    """URL处理器"""
    
    def __init__(self):
        self.config = get_config()
        # A股列表页 URL 格式和基础域名统一从配置文件读取
        self.url_formats = self.config.get_url_formats()
        self.base_url = self.config.get_base_url()
        self.timeout = self.config.get_request_timeout()
    
    def get_list_url(self, stock_code):
        """
        获取年报列表页URL
        
        Args:
            stock_code: 股票代码
        
        Returns:
            str or None: 可用的URL，如果都失败返回None
        """
        for url_format in self.url_formats:
            url = url_format.format(code=stock_code)
            if self._test_url(url):
                return url
        
        safe_log_error("股票代码 %s 的所有URL格式都失败", stock_code)
        return None
    
    def _test_url(self, url):
        """
        测试URL是否可用
        
        Args:
            url: 要测试的URL
        
        Returns:
            bool: 如果URL可用返回True
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            # 状态码200-399都认为可用
            if 200 <= response.status_code < 400:
                return True
        except Exception as e:
            safe_log_error("测试URL失败 %s: %s", url, str(e))
        
        return False
    
    def make_absolute_url(self, relative_url):
        """
        将相对URL转换为绝对URL，并解码HTML实体
        
        Args:
            relative_url: 相对URL，如 "/corp/view/vCB_AllBulletinDetail.php?stockid=002202&id=10829488"
        
        Returns:
            str: 绝对URL
        """
        # 解码HTML实体（如 &amp; -> &）
        relative_url = html.unescape(relative_url)
        
        if relative_url.startswith('http://') or relative_url.startswith('https://'):
            return relative_url
        
        if relative_url.startswith('/'):
            return self.base_url + relative_url
        else:
            return self.base_url + '/' + relative_url

