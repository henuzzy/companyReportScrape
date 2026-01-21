"""
配置管理模块
"""
import json
import os
import sys
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
    
    def _get_resource_path(self, relative_path):
        """
        获取资源文件的绝对路径
        支持PyInstaller打包后的资源路径
        
        Args:
            relative_path: 相对路径，如 'config/config.json'
        
        Returns:
            Path: 资源文件的绝对路径
        """
        try:
            # PyInstaller打包后会设置这个属性
            base_path = Path(sys._MEIPASS)
        except AttributeError:
            # 开发环境，使用脚本所在目录
            base_path = Path(__file__).parent.parent
        
        return base_path / relative_path
    
    def _load_config(self):
        """加载配置文件"""
        # 首先尝试从打包资源中加载
        config_path = self._get_resource_path(self.config_file)
        
        # 如果打包资源中不存在，尝试从当前目录加载（开发环境）
        if not config_path.exists():
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
            # 按市场划分的站点配置
            "markets": {
                "CN": {
                    "url_formats": [
                        "https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_Bulletin/stockid/{code}/page_type/ndbg.phtml",
                        "https://money.finance.sina.com.cn/corp/view/vCB_Bulletin.php?stockid={code}&type=list&page_type=ndbg"
                    ],
                    "base_url": "https://money.finance.sina.com.cn"
                },
                "HK": {
                    "search_url": "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh",
                    "prefix_url": "https://www1.hkexnews.hk/search/prefix.do",
                    "base_url": "https://www1.hkexnews.hk",
                    "default_params": {
                        "lang": "ZH",
                        "category": "0",
                        "market": "SEHK",
                        "searchType": "1",
                        "documentType": "-1",
                        "t1code": "40000",
                        "t2Gcode": "-2",
                        "t2code": "40100",
                        "MB-Daterange": "0",
                        "title": ""
                    }
                },
                "US": {
                    "url_formats": [],
                    "base_url": ""
                }
            },
            # 兼容旧字段，供现有代码使用（默认为 A股配置）
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
        
        # 如果是相对路径，转换为绝对路径
        path_obj = Path(path)
        if not path_obj.is_absolute():
            # 在打包后的exe中，使用exe所在目录作为基准
            try:
                # PyInstaller打包后会设置这个属性
                if hasattr(sys, '_MEIPASS'):
                    # 打包后的exe，使用exe所在目录（不是临时解压目录）
                    exe_dir = Path(sys.executable).parent
                    path_obj = exe_dir / path
                else:
                    # 开发环境，使用当前工作目录
                    path_obj = path_obj.absolute()
            except:
                # 如果出错，使用当前工作目录
                path_obj = path_obj.absolute()
        
        return path_obj
    
    def get_log_file(self):
        """获取日志文件路径"""
        return self.get('log_file', './logs/error.log')
    
    def get_url_formats(self):
        """获取URL格式列表"""
        # 目前 scraper 仍使用 A股逻辑，这里返回 A股的 url_formats
        markets = self.get('markets')
        if isinstance(markets, dict) and 'CN' in markets:
            cn_cfg = markets['CN']
            if isinstance(cn_cfg, dict) and 'url_formats' in cn_cfg:
                return cn_cfg['url_formats']
        return self.get('url_formats', [])
    
    def get_base_url(self):
        """获取基础URL"""
        markets = self.get('markets')
        if isinstance(markets, dict) and 'CN' in markets:
            cn_cfg = markets['CN']
            if isinstance(cn_cfg, dict) and 'base_url' in cn_cfg:
                return cn_cfg['base_url']
        return self.get('base_url', 'https://money.finance.sina.com.cn')

    # ---------------- 市场级配置访问方法 ----------------
    def get_market_config(self, market: str):
        """获取指定市场的完整配置字典，如 'CN' / 'HK' / 'US'"""
        markets = self.get('markets') or {}
        if isinstance(markets, dict):
            return markets.get(market, {})
        return {}

    def get_market_base_url(self, market: str):
        """获取指定市场的 base_url"""
        m_cfg = self.get_market_config(market)
        return m_cfg.get('base_url', '')

    def get_hk_search_url(self):
        """获取港股搜索页 URL"""
        m_cfg = self.get_market_config('HK')
        return m_cfg.get('search_url', 'https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh')

    def get_hk_prefix_url(self):
        """获取港股 prefix 查询 URL"""
        m_cfg = self.get_market_config('HK')
        return m_cfg.get('prefix_url', 'https://www1.hkexnews.hk/search/prefix.do')

    def get_hk_default_params(self):
        """获取港股搜索接口默认参数模板"""
        m_cfg = self.get_market_config('HK')
        default_params = {
            "lang": "ZH",
            "category": "0",
            "market": "SEHK",
            "searchType": "1",
            "documentType": "-1",
            "t1code": "40000",
            "t2Gcode": "-2",
            "t2code": "40100",
            "MB-Daterange": "0",
            "title": ""
        }
        cfg_params = m_cfg.get('default_params')
        if isinstance(cfg_params, dict):
            default_params.update(cfg_params)
        return default_params
    
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

