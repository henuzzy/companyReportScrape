"""
GUI主窗口
使用tkinter实现可视化界面
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from pathlib import Path
from typing import Optional

from utils.config import get_config
from utils.logger import setup_logger, get_logger
from utils.file_handler import read_stock_codes
from core.scraper import ReportScraper
from core.downloader import ReportDownloader


class MainWindow:
    """主窗口类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("公司年报爬取工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 初始化配置和日志
        self.config = get_config()
        setup_logger(log_file=self.config.get_log_file(), log_level=40)  # 40 = ERROR
        
        # 变量
        self.file_path_var = tk.StringVar()
        self.start_year_var = tk.StringVar()
        self.end_year_var = tk.StringVar()
        # 下载路径默认留空：避免打包后的exe展示本机绝对路径（如 dist\downloads）
        # 实际下载时若留空，会自动回退到 config 中的 download_base_path
        self.download_path_var = tk.StringVar(value="")
        self.is_running = False
        
        # 创建界面
        self._create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # 文件选择
        ttk.Label(main_frame, text="股票代码文件:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.file_path_var, width=50, state='readonly').grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(main_frame, text="选择文件", command=self._select_file).grid(row=row, column=2, pady=5)
        row += 1
        
        # 年份范围
        year_frame = ttk.Frame(main_frame)
        year_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Label(year_frame, text="年份范围:").pack(side=tk.LEFT)
        ttk.Entry(year_frame, textvariable=self.start_year_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(year_frame, text="至").pack(side=tk.LEFT)
        ttk.Entry(year_frame, textvariable=self.end_year_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(year_frame, text="(留空表示下载所有年份)").pack(side=tk.LEFT, padx=10)
        row += 1
        
        # 下载路径
        ttk.Label(main_frame, text="下载路径:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.download_path_var, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(main_frame, text="选择路径", command=self._select_download_path).grid(row=row, column=2, pady=5)
        row += 1
        
        # 开始按钮
        self.start_button = ttk.Button(main_frame, text="开始下载", command=self._start_download)
        self.start_button.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1
        
        # 进度条
        ttk.Label(main_frame, text="下载进度:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.progress_var = tk.StringVar(value="0%")
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 日志显示区域
        ttk.Label(main_frame, text="日志信息:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=5)
        row += 1
        
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)
        
        # 日志文本框和滚动条
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=15, yscrollcommand=scrollbar.set, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.grid(row=row+1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
    
    def _select_file(self):
        """选择股票代码文件"""
        file_path = filedialog.askopenfilename(
            title="选择股票代码文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self._log(f"已选择文件: {file_path}")
    
    def _select_download_path(self):
        """选择下载路径"""
        initial_dir = self.download_path_var.get().strip()
        if not initial_dir:
            # 留空时，优先使用用户主目录；如果不可用则使用当前工作目录
            initial_dir = str(Path.home()) if str(Path.home()) else os.getcwd()
        path = filedialog.askdirectory(
            title="选择下载路径",
            initialdir=initial_dir
        )
        if path:
            self.download_path_var.set(path)
            self._log(f"下载路径: {path}")
    
    def _log(self, message):
        """添加日志信息（安全处理编码）"""
        try:
            # 确保消息是字符串
            if not isinstance(message, str):
                message = str(message)
            
            # 尝试确保消息可以安全显示（处理可能的编码问题）
            try:
                # 确保是有效的UTF-8字符串
                message.encode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 如果编码失败，尝试替换错误字符
                message = message.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.root.update_idletasks()
        except Exception:
            # 如果显示失败，忽略错误（避免程序崩溃）
            pass
    
    def _progress_callback(self, current, total, message):
        """进度回调函数"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_var.set(f"{percentage}% ({current}/{total})")
            self.progress_bar['maximum'] = total
            self.progress_bar['value'] = current
        else:
            self.progress_var.set("0%")
            self.progress_bar['value'] = 0
        
        if message:
            self._log(message)
    
    def _start_download(self):
        """开始下载"""
        if self.is_running:
            messagebox.showwarning("警告", "下载任务正在进行中，请稍候...")
            return
        
        # 验证输入
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showerror("错误", "请选择股票代码文件！")
            return
        
        if not Path(file_path).exists():
            messagebox.showerror("错误", "文件不存在！")
            return
        
        # 验证年份
        start_year = None
        end_year = None
        try:
            start_year_str = self.start_year_var.get().strip()
            end_year_str = self.end_year_var.get().strip()
            
            if start_year_str:
                start_year = int(start_year_str)
            if end_year_str:
                end_year = int(end_year_str)
            
            if start_year and end_year and start_year > end_year:
                messagebox.showerror("错误", "起始年份不能大于结束年份！")
                return
        except ValueError:
            messagebox.showerror("错误", "年份格式不正确，请输入数字！")
            return
        
        # 在新线程中运行下载任务
        self.is_running = True
        self.start_button.config(state='disabled')
        self.status_var.set("正在下载...")
        self.progress_bar['value'] = 0
        self.log_text.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self._download_task, args=(file_path, start_year, end_year), daemon=True)
        thread.start()
    
    def _download_task(self, file_path, start_year, end_year):
        """下载任务（在后台线程中运行）"""
        try:
            # 读取股票代码
            stock_codes = read_stock_codes(file_path)
            if not stock_codes:
                self.root.after(0, lambda: messagebox.showerror("错误", "未找到有效的股票代码！"))
                return
            
            self.root.after(0, lambda: self._log(f"共找到 {len(stock_codes)} 个股票代码"))
            
            # 初始化爬虫和下载器
            scraper = ReportScraper()
            downloader = ReportDownloader(progress_callback=self._progress_callback)
            
            # 收集所有需要下载的年报
            all_reports = []
            for stock_code in stock_codes:
                self.root.after(0, lambda code=stock_code: self._log(f"正在获取 {code} 的年报列表..."))
                
                reports = scraper.get_report_list(stock_code)
                if not reports:
                    self.root.after(0, lambda code=stock_code: self._log(f"{code} 未找到年报"))
                    continue
                
                # 年份筛选
                if start_year or end_year:
                    reports = scraper.filter_reports_by_year(reports, start_year, end_year)
                
                # 获取PDF下载链接
                for report in reports:
                    pdf_url = scraper.get_pdf_url(report['detail_url'])
                    if pdf_url:
                        report['pdf_url'] = pdf_url
                        all_reports.append(report)
                    else:
                        self.root.after(0, lambda title=report['title']: self._log(f"获取PDF链接失败: {title}"))
            
            if not all_reports:
                self.root.after(0, lambda: messagebox.showinfo("提示", "未找到需要下载的年报！"))
                return
            
            self.root.after(0, lambda: self._log(f"共找到 {len(all_reports)} 个年报需要下载"))
            
            # 开始下载
            download_path = self.download_path_var.get().strip()
            if not download_path:
                # GUI留空时回退到配置默认路径（打包后为 exe 同目录下的 ./downloads）
                download_path = str(self.config.get_download_base_path())
            success_count, failed_count = downloader.download_reports(
                all_reports,
                base_path=download_path
            )
            
            # 完成
            message = f"下载完成！成功: {success_count}, 失败: {failed_count}"
            self.root.after(0, lambda: self._log(message))
            self.root.after(0, lambda: messagebox.showinfo("完成", message))
            self.root.after(0, lambda: self.status_var.set("下载完成"))
        
        except Exception as e:
            error_msg = f"下载任务异常: {e}"
            self.root.after(0, lambda: self._log(error_msg))
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, lambda: self.status_var.set("下载失败"))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.start_button.config(state='normal'))
    
    def _on_closing(self):
        """关闭窗口时的处理"""
        if self.is_running:
            if not messagebox.askokcancel("退出", "下载任务正在进行中，确定要退出吗？"):
                return
        self.root.destroy()

