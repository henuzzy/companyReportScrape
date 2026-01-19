"""
主程序入口
启动GUI界面
"""
import tkinter as tk
from gui.main_window import MainWindow


def main():
    """主函数"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

