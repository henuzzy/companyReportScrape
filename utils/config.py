"""
配置管理模块
"""
import json
import os
from pathlib import Path


class Config:
    """配置管理类"""
    
    def __init__(self, config_file='config/config.json'):
        """
        初始化配置
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        config_path = Path(self.config_file)
        
        # 如果配置文件不存在，使用默认配置
        if not config_path.exists():
            return self._get_default_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            # 使用logger而不是print，避免控制台编码问题
            import logging
            logger = logging.getLogger('company_report_scraper')
            try:
                logger.error(f"加载配置文件失败: {e}，使用默认配置")
            except:
                pass  # 如果日志记录也失败，忽略错误
            return self._get_default_config()
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            "concurrent_downloads": 10,
            "download_base_path": "./downloads",
            "log_level": "ERROR",
            "log_file": "./logs/error.log",
            "url_formats": [
                "https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_Bulletin/stockid/{code}/page_type/ndbg.phtml",
                "https://money.finance.sina.com.cn/corp/view/vCB_Bulletin.php?stockid={code}&type=list&page_type=ndbg"
            ],
            "base_url": "https://money.finance.sina.com.cn",
            "request_timeout": 30
        }
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def get_concurrent_downloads(self):
        """获取并发下载数"""
        return self.get('concurrent_downloads', 10)
    
    def get_download_base_path(self):
        """获取下载基础路径"""
        path = self.get('download_base_path', './downloads')
        return Path(path).absolute()
    
    def get_log_file(self):
        """获取日志文件路径"""
        return self.get('log_file', './logs/error.log')
    
    def get_url_formats(self):
        """获取URL格式列表"""
        return self.get('url_formats', [])
    
    def get_base_url(self):
        """获取基础URL"""
        return self.get('base_url', 'https://money.finance.sina.com.cn')
    
    def get_request_timeout(self):
        """获取请求超时时间"""
        return self.get('request_timeout', 30)


# 全局配置实例
_config_instance = None


def get_config():
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

