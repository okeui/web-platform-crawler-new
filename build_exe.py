import sys
import os
import subprocess

def build():
    print("=========================================")
    print("  FAQ Checker Desktop App PyInstaller Builder")
    print("=========================================")
    
    # 1. Ensure PyInstaller and CustomTkinter are installed
    try:
        import PyInstaller
        import customtkinter
        print("[1/2] PyInstaller and CustomTkinter are ready.")
    except ImportError:
        print("[1/2] Installing required build dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "customtkinter"])

    # 2. Run PyInstaller command
    print("[2/2] Packaging main_gui.py into standalone .exe file...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name=FAQchecker_GUI",
        "--collect-all=customtkinter",
        "--hidden-import=selenium",
        "--hidden-import=webdriver_manager",
        "--hidden-import=pymsgbox",
        "--clean",
        "main_gui.py"
    ]

    print(f"Executing: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    print("\n=========================================")
    print(" BUILD SUCCESSFUL!")
    print(" Executable file generated at: dist/FAQchecker_GUI.exe")
    print("=========================================")

if __name__ == "__main__":
    build()
