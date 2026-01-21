"""
下载模块
实现并发下载、临时文件处理、断点续传等功能
"""
import os
import sys
import random
import time
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional
from utils.config import get_config
from utils.logger import get_logger, safe_log_error
from utils.file_handler import sanitize_filename, is_file_downloaded, get_download_path

logger = get_logger()


class ReportDownloader:
    """年报下载器"""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        初始化下载器
        
        Args:
            progress_callback: 进度回调函数，参数为 (current, total, message)
        """
        self.config = get_config()
        self.progress_callback = progress_callback
        self.timeout = self.config.get_request_timeout()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36'
        }
        self.downloaded_count = 0
        self.failed_count = 0
    
    def download_reports(self, reports, base_path=None, concurrent_downloads=None, market: str = 'CN'):
        """
        并发下载年报
        
        Args:
            reports: 年报信息列表，每个元素包含 title, pdf_url, stock_code
            base_path: 下载基础路径，如果为None则使用配置文件中的路径
            concurrent_downloads: 并发数，如果为None则使用配置文件中的值
        
        Returns:
            tuple: (成功数量, 失败数量)
        """
        if not reports:
            return 0, 0
        
        self.downloaded_count = 0
        self.failed_count = 0
        
        if base_path is None:
            base_path = self.config.get_download_base_path()
        else:
            base_path = Path(base_path)
        
        if concurrent_downloads is None:
            concurrent_downloads = self.config.get_concurrent_downloads()
        
        total = len(reports)
        
        # 准备下载任务（过滤已下载的）
        download_tasks = []
        for report in reports:
            stock_code = report.get('stock_code', 'unknown')
            title = report.get('title', 'unnamed')
            pdf_url = report.get('pdf_url')
            
            if not pdf_url:
                safe_log_error("年报缺少PDF链接: %s", title)
                self.failed_count += 1
                continue
            
            # 文件名清理（确保UTF-8编码）
            filename = sanitize_filename(title)
            if not filename.endswith('.pdf'):
                filename = filename + '.pdf'
            
            # 确保文件名是有效的UTF-8字符串
            try:
                filename.encode('utf-8')
            except UnicodeEncodeError:
                # 如果编码失败，使用ASCII安全名称
                filename = f"report_{stock_code}.pdf"
            
            # 获取下载目录（按市场划分子目录，如 A股年报/、港股年报/、美股年报/）
            download_dir = get_download_path(base_path, stock_code, market=market)
            
            # 检查是否已下载（去重）
            if is_file_downloaded(download_dir, filename):
                if self.progress_callback:
                    self.progress_callback(
                        self.downloaded_count + self.failed_count,
                        total,
                        f"{stock_code} - {title} 已存在，跳过"
                    )
                self.downloaded_count += 1
                continue
            
            download_tasks.append({
                'stock_code': stock_code,
                'title': title,
                'filename': filename,
                'pdf_url': pdf_url,
                'download_dir': download_dir
            })
        
        # 实际需要下载的任务数
        actual_total = len(download_tasks) + self.downloaded_count
        remaining_count = len(download_tasks)
        
        if remaining_count == 0:
            if self.progress_callback:
                self.progress_callback(actual_total, actual_total, "所有文件已存在，无需下载")
            return self.downloaded_count, self.failed_count
        
        # 为了添加随机延迟防止反爬，使用串行下载（并发数设为1）
        # 如果用户需要并发，可以在配置中设置，但建议保持为1以确保延迟生效
        if concurrent_downloads > 1:
            # 如果并发数大于1，建议改为1以确保延迟生效
            concurrent_downloads = 1
        
        # 串行下载，每次下载前添加随机延迟（第一个文件立即下载）
        for index, task in enumerate(download_tasks):
            try:
                # 如果不是第一个文件，在下载前添加随机延迟（10-60秒）
                if index > 0:
                    delay = random.uniform(5, 10)
                    if self.progress_callback:
                        current = self.downloaded_count + self.failed_count + (actual_total - remaining_count)
                        self.progress_callback(
                            current,
                            actual_total,
                            f"等待 {delay:.1f} 秒后下载下一个文件..."
                        )
                    time.sleep(delay)
                
                success = self._download_single_report(task)
                if success:
                    self.downloaded_count += 1
                else:
                    self.failed_count += 1
                
                # 更新进度
                if self.progress_callback:
                    current = self.downloaded_count + self.failed_count + (actual_total - remaining_count)
                    self.progress_callback(
                        current,
                        actual_total,
                        f"{'成功' if success else '失败'}: {task['stock_code']} - {task['title']}"
                    )
                    
            except Exception as e:
                safe_log_error("下载任务异常 %s: %s", task.get('title', 'unknown'), str(e))
                self.failed_count += 1
        
        return self.downloaded_count, self.failed_count
    
    def _download_single_report(self, task):
        """
        下载单个年报
        
        Args:
            task: 下载任务，包含 stock_code, title, filename, pdf_url, download_dir
        
        Returns:
            bool: 下载成功返回True，失败返回False
        """
        stock_code = task['stock_code']
        title = task['title']
        filename = task['filename']
        pdf_url = task['pdf_url']
        download_dir = task['download_dir']
        
        # 临时文件名
        temp_filename = filename + '.tmp'
        # 使用字符串路径，避免Path对象的编码问题
        temp_path_str = os.path.join(str(download_dir), temp_filename)
        final_path_str = os.path.join(str(download_dir), filename)
        
        try:
            # 下载文件（延迟已在download_reports方法中处理）
            response = requests.get(pdf_url, headers=self.headers, timeout=self.timeout, stream=True)
            
            if response.status_code != 200:
                safe_log_error("下载失败 %s: HTTP %s", title, response.status_code)
                return False
            
            # 写入临时文件
            with open(temp_path_str, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 检查文件大小（至少应该大于1KB）
            if os.path.getsize(temp_path_str) < 1024:
                safe_log_error("下载文件异常小 %s: %s bytes", title, os.path.getsize(temp_path_str))
                try:
                    os.remove(temp_path_str)
                except:
                    pass
                return False
            
            # 重命名为正式文件（使用os.rename避免Path对象的编码转换问题）
            try:
                os.rename(temp_path_str, final_path_str)
            except (OSError, UnicodeEncodeError, UnicodeDecodeError):
                # 如果重命名失败，尝试使用shutil
                try:
                    import shutil
                    shutil.move(temp_path_str, final_path_str)
                except Exception as e2:
                    safe_log_error("重命名文件失败 %s: %s", title, str(e2))
                    return False
            
            return True
        
        except Exception as e:
            safe_log_error("下载失败 %s: %s", title, str(e))
            # 清理临时文件
            if os.path.exists(temp_path_str):
                try:
                    os.remove(temp_path_str)
                except:
                    pass
            return False

