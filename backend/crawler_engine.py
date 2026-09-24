import time
import os
import threading
from datetime import datetime, date
from typing import Dict, List, Optional, Callable

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
import pymsgbox

try:
    from storage import get_logs_dir
except ImportError:
    from backend.storage import get_logs_dir

class CrawlerEngine:
    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        """
        log_callback: function receiving (message, log_level)
        """
        self.log_callback = log_callback
        self._stop_requested = False
        self._is_running = False
        self._current_step = "IDLE"
        self._progress = 0
        self._total_items = 0
        self._completed_items = 0
        self._current_item = ""
        self._driver: Optional[webdriver.Chrome] = None
        self.pin_code_event = threading.Event()
        self.provided_pin_code: Optional[str] = None
        self.log_dir = get_logs_dir()

    def log(self, message: str, level: str = "INFO", log_path: Optional[str] = None):
        """Emit log to callback and write to file."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        print(formatted)
        
        # Write to daily file
        try:
            target_log_dir = log_path if (log_path and log_path not in [".\\", ".", "./"]) else (getattr(self, "log_dir", None) or get_logs_dir())
            if not target_log_dir or target_log_dir in [".\\", ".", "./"]:
                target_log_dir = get_logs_dir()
            
            os.makedirs(target_log_dir, exist_ok=True)
            d = str(date.today())
            file_name = f"{d}_FAQ_log.txt"
            full_path = os.path.join(target_log_dir, file_name)
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} {message}\n")
        except Exception as e:
            print(f"Error writing log file: {e}")

        # Frontend Callback
        if self.log_callback:
            try:
                self.log_callback(message, level)
            except Exception as e:
                print(f"Error in log callback: {e}")

    def set_pin_code(self, pin: str):
        """Receive PIN code from frontend API."""
        self.provided_pin_code = pin
        self.pin_code_event.set()

    def request_stop(self):
        self._stop_requested = True
        self.log("收到使用者停止要求，正在中斷任務...", "WARN")

    def is_running(self) -> bool:
        return self._is_running

    def get_status(self) -> Dict:
        return {
            "is_running": self._is_running,
            "current_step": self._current_step,
            "progress": self._progress,
            "completed_items": self._completed_items,
            "total_items": self._total_items,
            "current_item": self._current_item,
            "stop_requested": self._stop_requested
        }

    def safe_find(self, driver, by, value, timeout=10):
        if self._stop_requested:
            raise InterruptedError("Stopped by user")
        try:
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.presence_of_element_located((by, value)))
            wait.until(EC.visibility_of_element_located((by, value)))
            element = wait.until(EC.element_to_be_clickable((by, value)))
            return element
        except InterruptedError:
            raise
        except Exception as e:
            self.log(f"搜尋元素 [{value}] 時出現了錯誤: {e}", "ERROR")
            return None

    def safe_click(self, driver, by, value, timeout=20):
        if self._stop_requested:
            raise InterruptedError("Stopped by user")
        for _ in range(3):
            if self._stop_requested:
                raise InterruptedError("Stopped by user")
            try:
                wait = WebDriverWait(driver, timeout)
                wait.until(EC.presence_of_element_located((by, value)))
                wait.until(EC.visibility_of_element_located((by, value)))
                element = wait.until(EC.element_to_be_clickable((by, value)))
                element.click()
                return element
            except (StaleElementReferenceException, ElementClickInterceptedException):
                time.sleep(0.5)
            except InterruptedError:
                raise
            except Exception:
                pass
        self.log(f"點選元素 [{value}] 時出現了錯誤", "ERROR")
        return None

    def login(self, driver, timeout=10, pin_code_override: Optional[str] = None):
        self._current_step = "LOGIN"
        for attempt in range(3):
            if self._stop_requested:
                raise InterruptedError("Stopped by user")
            try:
                cert_button = self.safe_click(driver, By.ID, "certLogin")
                cert_pin_code_input = self.safe_find(driver, By.ID, "cert_pin_code")
                if not cert_pin_code_input:
                    continue

                pincode = pin_code_override
                if not pincode:
                    if self.provided_pin_code:
                        # Already provided (e.g. from previous run or pre-set)
                        pincode = self.provided_pin_code
                        self.provided_pin_code = None  # consume after use
                    elif self.log_callback:
                        # ── GUI 模式：透過 log 訊號觸發前端輸入框，等待事件 ──
                        self.pin_code_event.clear()
                        self.log("等待使用者輸入自然人憑證 PIN 碼...", "WARN")
                        # 最多等待 30 秒讓使用者輸入
                        got = self.pin_code_event.wait(timeout=30)
                        if got and self.provided_pin_code:
                            pincode = self.provided_pin_code
                            self.provided_pin_code = None
                        else:
                            self.log("等待 PIN 碼逾時或使用者取消", "ERROR")
                            return False
                    else:
                        # ── CLI 備援模式：使用 pymsgbox ──
                        self.log("等待使用者輸入自然人憑證 PIN 碼...", "WARN")
                        pincode = pymsgbox.prompt(
                            '請輸入自然人憑證pin碼（一次性使用，程式不會紀錄）',
                            title='登入'
                        )

                if not pincode:
                    self.log("未輸入 PIN 碼，無法完成登入", "ERROR")
                    return False

                cert_pin_code_input.send_keys(pincode)

                login_btn = driver.find_element(By.ID, "certLoginBtn")
                login_btn.click()
                self.log("登入認證系統", "SUCCESS")
                return True
            except InterruptedError:
                raise
            except Exception as e:
                self.log(f"第 {attempt+1} 次嘗試登入失敗: {e}", "WARN")
        self.log("無法完成登入", "ERROR")
        return False

    def open_and_switch_new_tab(self, driver, click_func, timeout=10):
        try:
            current = driver.current_window_handle
            click_func()

            WebDriverWait(driver, timeout).until(
                lambda d: len(d.window_handles) > 1
            )

            for handle in driver.window_handles:
                if handle != current:
                    driver.switch_to.window(handle)
                    self.log("切換至新分頁（網站整合平台）", "SUCCESS")
                    return handle
        except Exception as e:
            self.log(f"切換至新分頁（網站整合平台）: {e}", "ERROR")

    def expand_web_directory(self, driver, directory: List[str]):
        try:
            for route in directory[:-1]:
                if self._stop_requested:
                    raise InterruptedError("Stopped by user")
                value = f"//a[@title='{route}']/preceding-sibling::span"
                switch_span = self.safe_find(driver, By.XPATH, value)
                if switch_span:
                    classes = switch_span.get_attribute("class") or ""
                    if ("root_close" in classes) or ("center_close" in classes):
                        switch_span.click()

            node = directory[-1]
            value = f"//a[@title='{node}']/following-sibling::a"
            self.safe_click(driver, By.XPATH, value)

            value = "//a[contains(text(),'內容維護')]"
            self.safe_click(driver, By.XPATH, value)
            self.log(f"展開網頁目錄 [{ ' > '.join(directory) }]", "SUCCESS")
            return True
        except InterruptedError:
            raise
        except Exception as e:
            self.log(f"展開網頁目錄 [{ ' > '.join(directory) }]: {e}", "ERROR")
            return False

    def system_node_search(self, driver, keyword: str):
        try:
            input_ID = "ContentPlaceHolder1_txtKeyWord"
            system_input = self.safe_find(driver, By.ID, input_ID)
            if not system_input:
                return False

            system_input.send_keys(Keys.CONTROL, 'a')
            system_input.send_keys(Keys.DELETE)
            system_input.send_keys(keyword)

            button_ID = "ContentPlaceHolder1_btnSearch"
            self.safe_click(driver, By.ID, button_ID)
            self.log(f"搜尋系統節點關鍵字: {keyword}", "INFO")
            return True
        except InterruptedError:
            raise
        except Exception as e:
            self.log(f"搜尋系統節點: {e}", "ERROR")
            return False

    def update_review_date(self, driver):
        try:
            wait = WebDriverWait(driver, 10)
            checkbox_ID = "ContentPlaceHolder1_gvIndex_chkSelect_0"
            self.safe_click(driver, By.ID, checkbox_ID)

            button_ID = "ContentPlaceHolder1_btnReviewDate"
            self.safe_click(driver, By.ID, button_ID)

            button_value = '//button[contains(@class,"jqibutton") and contains(., "確定")]'
            self.safe_click(driver, By.XPATH, button_value)

            wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "jqiform")))
            self.log("更新檢閱日期", "COMPLETE")
            return True
        except InterruptedError:
            raise
        except Exception as e:
            self.log(f"無法更新檢閱日期: {e}", "ERROR")
            return False

    def run(self, paths_and_checklists: Dict[str, List[str]], settings: Dict):
        self._is_running = True
        self._stop_requested = False
        self._completed_items = 0
        self._current_step = "STARTING"

        configured_log_dir = settings.get("log_dir")
        if configured_log_dir and configured_log_dir not in [".\\", ".", "./"]:
            self.log_dir = configured_log_dir
        else:
            self.log_dir = get_logs_dir()
        os.makedirs(self.log_dir, exist_ok=True)

        # Calculate total keywords count
        self._total_items = sum(len(keywords) for keywords in paths_and_checklists.values())
        self._progress = 0

        self.log("================================================", "INFO")
        self.log("開始執行 FAQ 自動檢閱爬蟲任務", "INFO")
        self.log(f"總計需要檢閱 {len(paths_and_checklists)} 個目錄，共 {self._total_items} 個問答項目", "INFO")

        options = Options()
        if settings.get("headless", False):
            options.add_argument("--headless=new")
        options.add_argument("--start-maximized")

        # ── 自動允許 HID（讀卡機）權限，避免彈窗出現 ──────────────────────
        target_origin = settings.get("target_url", "https://login.gov.taipei/login.php")
        from urllib.parse import urlparse
        parsed = urlparse(target_origin)
        # Chrome 的 content_settings key 必須包含明確 port，例如 https://host:443,*
        _port = parsed.port or (443 if parsed.scheme == "https" else 80)
        hid_key = f"{parsed.scheme}://{parsed.hostname}:{_port},*"

        options.add_experimental_option("prefs", {
            # hid_guard: 1=Allow, 2=Block
            "profile.content_settings.exceptions.hid_guard": {
                hid_key: {"last_modified": "13370000000000000", "setting": 1}
            },
            # hid_chooser_data: 預先記住允許所有 HID 設備
            "profile.content_settings.exceptions.hid_chooser_data": {
                hid_key: {"last_modified": "13370000000000000", "setting": 1}
            },
            # 額外：同時允許 USB 存取（部分讀卡機走 USB HID）
            "profile.content_settings.exceptions.usb_guard": {
                hid_key: {"last_modified": "13370000000000000", "setting": 1}
            },
            "profile.default_content_setting_values.notifications": 1
        })
        
        # ─────────────────────────────────────────────────────────────────

        try:
            self._current_step = "INITIALIZING_DRIVER"
            self.log("初始化 Chrome WebDriver...", "INFO")
            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)

            target_url = target_origin
            self._driver.get(target_url)

            # 1. Login
            if not self.login(self._driver):
                self.log("登入程序未完成，任務終止", "ERROR")
                return

            # 2. Search EIP System
            self._current_step = "SITEMAP_SEARCH"
            sitemap_search_value = "a[title='系統搜尋'][href='/Sitemap/Search']"
            self.safe_click(self._driver, By.CSS_SELECTOR, sitemap_search_value)

            search_input_value = "SeachText"
            search_input = self.safe_find(self._driver, By.ID, search_input_value)
            if search_input:
                search_input.send_keys(settings.get("search_system_name", "網站整合平臺"))

            search_button_value = "EIPSeachBtn"
            self.safe_click(self._driver, By.ID, search_button_value)

            # 3. Switch to platform tab
            self._current_step = "SWITCH_TAB"
            self.open_and_switch_new_tab(
                self._driver,
                lambda: self.safe_click(self._driver, By.CSS_SELECTOR, ".is-root > li:first-of-type > a")
            )

            # 4. Enter Data Management
            self._current_step = "DATA_MANAGEMENT"
            link_value = "//a[contains(normalize-space(.), '資料管理')]"
            self.safe_click(self._driver, By.XPATH, link_value)

            # 5. Loop paths & keywords
            self._current_step = "CHECKING_ITEMS"
            for path_str, keywords in paths_and_checklists.items():
                if self._stop_requested:
                    raise InterruptedError("Stopped by user")

                directory = path_str.split(">")
                self.expand_web_directory(self._driver, directory)

                for keyword in keywords:
                    if self._stop_requested:
                        raise InterruptedError("Stopped by user")

                    self._current_item = f"{path_str} > {keyword}"
                    self.log(f"檢視「{self._current_item}」節點", "INFO")
                    
                    self.system_node_search(self._driver, keyword)
                    self.update_review_date(self._driver)

                    self._completed_items += 1
                    if self._total_items > 0:
                        self._progress = int((self._completed_items / self._total_items) * 100)

            self.log("所有 FAQ 節點檢閱完成！任務順利結束。", "SUCCESS")
            self._current_step = "FINISHED"
            self._progress = 100

        except InterruptedError:
            self.log("任務已被使用者強制中斷。", "WARN")
            self._current_step = "STOPPED"
        except Exception as e:
            self.log(f"執行過程中發生意外錯誤: {e}", "ERROR")
            self._current_step = "ERROR"
        finally:
            if self._driver:
                try:
                    self.log("關閉瀏覽器...", "INFO")
                    self._driver.quit()
                except Exception:
                    pass
                self._driver = None
            self._is_running = False
