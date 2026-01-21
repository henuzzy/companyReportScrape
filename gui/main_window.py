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
from core.scraper import ReportScraper, HKReportScraper
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
        
        # 日志
        self.logger = get_logger()

        # 变量
        # 不同市场的股票代码文件（可分别选择，也可只选其中一部分）
        self.a_file_path_var = tk.StringVar()
        self.hk_file_path_var = tk.StringVar()
        self.us_file_path_var = tk.StringVar()
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

        # A股代码文件
        ttk.Label(main_frame, text="A股代码文件:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.a_file_path_var, width=50, state='readonly').grid(
            row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5
        )
        ttk.Button(main_frame, text="选择文件", command=lambda: self._select_file('CN')).grid(row=row, column=2, pady=5)
        row += 1

        # 港股代码文件
        ttk.Label(main_frame, text="港股代码文件:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.hk_file_path_var, width=50, state='readonly').grid(
            row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5
        )
        ttk.Button(main_frame, text="选择文件", command=lambda: self._select_file('HK')).grid(row=row, column=2, pady=5)
        row += 1

        # 美股代码文件
        ttk.Label(main_frame, text="美股代码文件:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.us_file_path_var, width=50, state='readonly').grid(
            row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5
        )
        ttk.Button(main_frame, text="选择文件", command=lambda: self._select_file('US')).grid(row=row, column=2, pady=5)
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
    
    def _select_file(self, market: str):
        """选择股票代码文件
        
        Args:
            market: 市场标识，'CN' / 'HK' / 'US'
        """
        file_path = filedialog.askopenfilename(
            title="选择股票代码文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            if market == 'CN':
                self.a_file_path_var.set(file_path)
                prefix = "[A股]"
            elif market == 'HK':
                self.hk_file_path_var.set(file_path)
                prefix = "[港股]"
            else:
                self.us_file_path_var.set(file_path)
                prefix = "[美股]"
            self._log(f"{prefix} 已选择文件: {file_path}")
    
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
        
        # 验证至少选择了一个市场的股票代码文件
        market_files = {
            'CN': self.a_file_path_var.get().strip(),
            'HK': self.hk_file_path_var.get().strip(),
            'US': self.us_file_path_var.get().strip(),
        }
        # 过滤为空的
        market_files = {m: p for m, p in market_files.items() if p}
        if not market_files:
            messagebox.showerror("错误", "请至少选择一个股票代码文件！（A股 / 港股 / 美股）")
            return

        # 校验文件是否存在
        for market, path_str in market_files.items():
            if not Path(path_str).exists():
                market_name = {'CN': 'A股', 'HK': '港股', 'US': '美股'}.get(market, market)
                messagebox.showerror("错误", f"{market_name} 代码文件不存在！")
                return
        
        # 验证年份（A股使用年份，港股使用日期格式 YYYYMMDD，在具体市场处理中再细分校验）
        start_year = None
        end_year = None
        start_year_str = self.start_year_var.get().strip()
        end_year_str = self.end_year_var.get().strip()

        # A股仍采用“年份数字”校验；港股在 _download_task 中单独做 YYYYMMDD 校验
        try:
            if start_year_str:
                start_year = int(start_year_str)
            if end_year_str:
                end_year = int(end_year_str)
            if start_year and end_year and start_year > end_year:
                messagebox.showerror("错误", "起始年份不能大于结束年份！")
                return
        except ValueError:
            messagebox.showerror("错误", "年份格式不正确，请输入数字！（例如：2020）")
            return
        
        # 在新线程中运行下载任务
        self.is_running = True
        self.start_button.config(state='disabled')
        self.status_var.set("正在下载...")
        self.progress_bar['value'] = 0
        self.log_text.delete(1.0, tk.END)
        
        thread = threading.Thread(
            target=self._download_task,
            args=(market_files, start_year, end_year),
            daemon=True
        )
        thread.start()

    def _download_task(self, market_files, start_year, end_year):
        """下载任务（在后台线程中运行）"""
        try:
            total_success = 0
            total_failed = 0

            # 目前仅实现 A股网站逻辑；港股/美股在你提供站点规则后再补充
            for market, file_path in market_files.items():
                market_name = {'CN': 'A股', 'HK': '港股', 'US': '美股'}.get(market, market)

                # 读取股票代码
                stock_codes = read_stock_codes(file_path)
                if not stock_codes:
                    self.root.after(0, lambda mn=market_name: messagebox.showerror("错误", f"{mn} 代码文件中未找到有效的股票代码！"))
                    continue

                self.root.after(0, lambda mn=market_name, cnt=len(stock_codes): self._log(f"[{mn}] 共找到 {cnt} 个股票代码"))

                # 初始化下载器
                downloader = ReportDownloader(progress_callback=self._progress_callback)

                # 收集所有需要下载的年报
                all_reports = []

                # ---------------- A股逻辑（原有新浪财经） ----------------
                if market == 'CN':
                    scraper = ReportScraper()
                    for stock_code in stock_codes:
                        self.root.after(0, lambda code=stock_code, mn=market_name: self._log(f"[{mn}] 正在获取 {code} 的年报列表..."))

                        reports = scraper.get_report_list(stock_code)
                        if not reports:
                            self.root.after(0, lambda code=stock_code, mn=market_name: self._log(f"[{mn}] {code} 未找到年报"))
                            continue

                        # 年份筛选（A股：使用整数年份）
                        if start_year or end_year:
                            reports = scraper.filter_reports_by_year(reports, start_year, end_year)

                        # 获取PDF下载链接
                        for report in reports:
                            pdf_url = scraper.get_pdf_url(report['detail_url'])
                            if pdf_url:
                                report['pdf_url'] = pdf_url
                                all_reports.append(report)
                            else:
                                self.root.after(0, lambda title=report['title'], mn=market_name: self._log(f"[{mn}] 获取PDF链接失败: {title}"))

                # ---------------- 港股逻辑（HKEX） ----------------
                elif market == 'HK':
                    hk_scraper = HKReportScraper()

                    # 港股日期格式：YYYYMMDD，如果用户未填写，则默认最近10年
                    start_date_str = self.start_year_var.get().strip()
                    end_date_str = self.end_year_var.get().strip()

                    years_for_search = []
                    if not start_date_str and not end_date_str:
                        # 默认最近10年
                        import datetime
                        current_year = datetime.datetime.now().year
                        years_for_search = list(range(current_year - 9, current_year + 1))
                        self.root.after(0, lambda mn=market_name: self._log(f"[{mn}] 未填写日期，默认搜索最近10年: {years_for_search[0]}-{years_for_search[-1]}"))
                    else:
                        # 检查 YYYYMMDD 格式
                        def _is_valid_yyyymmdd(s: str) -> bool:
                            return len(s) == 8 and s.isdigit()

                        if start_date_str and not _is_valid_yyyymmdd(start_date_str):
                            msg = f"[{market_name}] 起始日期格式错误（应为YYYYMMDD）：{start_date_str}"
                            self.root.after(0, lambda m=msg: self._log(m))
                            try:
                                self.logger.error(msg)
                            except Exception:
                                pass
                            continue
                        if end_date_str and not _is_valid_yyyymmdd(end_date_str):
                            msg = f"[{market_name}] 结束日期格式错误（应为YYYYMMDD）：{end_date_str}"
                            self.root.after(0, lambda m=msg: self._log(m))
                            try:
                                self.logger.error(msg)
                            except Exception:
                                pass
                            continue

                        # 将 YYYYMMDD 转换为年份区间，供 HK 抓取使用
                        start_year_hk = int(start_date_str[:4]) if start_date_str else None
                        end_year_hk = int(end_date_str[:4]) if end_date_str else None
                        if start_year_hk and end_year_hk and start_year_hk > end_year_hk:
                            msg = f"[{market_name}] 起始日期不能晚于结束日期！"
                            self.root.after(0, lambda m=msg: self._log(m))
                            try:
                                self.logger.error(msg)
                            except Exception:
                                pass
                            continue
                        if start_year_hk and end_year_hk:
                            years_for_search = list(range(start_year_hk, end_year_hk + 1))
                        elif start_year_hk and not end_year_hk:
                            years_for_search = [start_year_hk]
                        elif end_year_hk and not start_year_hk:
                            years_for_search = [end_year_hk]

                        if years_for_search:
                            self.root.after(0, lambda mn=market_name, ys=years_for_search: self._log(f"[{mn}] 港股按年份区间搜索: {ys[0]}-{ys[-1]}"))

                    for stock_code in stock_codes:
                        # 校验港股代码样式：5位数字
                        if not (len(stock_code) == 5 and stock_code.isdigit()):
                            msg = f"[{market_name}] 股票代码样式不符合规范（应为5位数字，例如00700）：{stock_code}"
                            self.root.after(0, lambda m=msg: self._log(m))
                            try:
                                self.logger.error(msg)
                            except Exception:
                                pass
                            continue

                        self.root.after(0, lambda code=stock_code, mn=market_name: self._log(f"[{mn}] 正在获取 {code} 的港股年报列表..."))

                        if not years_for_search:
                            # 若由于日期错误导致 years_for_search 为空，直接跳过
                            continue

                        reports = hk_scraper.get_reports_by_years(stock_code, years_for_search)
                        if not reports:
                            self.root.after(0, lambda code=stock_code, mn=market_name: self._log(f"[{mn}] {code} 未找到年报"))
                            continue

                        all_reports.extend(reports)

                # ---------------- 美股逻辑（预留） ----------------
                else:
                    self.root.after(0, lambda mn=market_name: self._log(f"[{mn}] 暂未实现该市场的爬取逻辑"))

                if not all_reports:
                    continue

                self.root.after(0, lambda mn=market_name, cnt=len(all_reports): self._log(f"[{mn}] 共找到 {cnt} 个年报需要下载"))

                # 开始下载
                download_path = self.download_path_var.get().strip()
                if not download_path:
                    # GUI留空时回退到配置默认路径（打包后为 exe 同目录下的 ./downloads）
                    download_path = str(self.config.get_download_base_path())
                success_count, failed_count = downloader.download_reports(
                    all_reports,
                    base_path=download_path,
                    market=market
                )

                total_success += success_count
                total_failed += failed_count
            
            # 完成
            message = f"下载完成！成功: {total_success}, 失败: {total_failed}"
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

