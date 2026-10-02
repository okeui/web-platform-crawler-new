import sys
import os
import io
import traceback
import tkinter as tk
from tkinter import messagebox

# PyInstaller --noconsole 模式下 sys.stdout 與 sys.stderr 為 None
# 重導向至 NullWriter 防止 customtkinter/darkdetect/print 拋出 'NoneType' object has no attribute 'write'
class NullWriter:
    def write(self, text):
        pass
    def flush(self):
        pass
    def isatty(self):
        return False

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

def main():
    try:
        from desktop_gui import FAQCheckerGUI
        app = FAQCheckerGUI()
        app.mainloop()
    except Exception as e:
        error_msg = traceback.format_exc()
        try:
            exe_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
            log_path = os.path.join(exe_dir, "startup_error.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(error_msg)
        except Exception:
            pass

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("程式啟動失敗 (Startup Error)", f"應用程式啟動時發生未預期的錯誤：\n\n{e}\n\n詳細追蹤訊息：\n{error_msg[:1000]}")

if __name__ == "__main__":
    main()


