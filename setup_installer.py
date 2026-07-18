# -*- coding: utf-8 -*-
"""
闻铎点名器 - 安装程序
带图形界面的安装器，包含：
- 安装目录选择
- 桌面 / 开始菜单快捷方式
- 注册表写入（便于卸载）
- 卸载程序创建
"""
import sys
import os
import zipfile
import shutil
import winreg

from pathlib import Path
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QLineEdit, QProgressBar, QMessageBox, QCheckBox,
        QFileDialog, QTextEdit, QFrame, QSizePolicy,
    )
    from PyQt6.QtGui import QIcon, QPixmap
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
except ImportError:
    print("PyQt6 not found - running in minimal mode")
    # fallback minimal installer
    import tkinter as tk
    from tkinter import messagebox, filedialog
    HAS_PYQT = False
else:
    HAS_PYQT = True


APP_NAME = "闻铎点名器"
APP_EXE = "闻铎点名器.exe"
UNINSTALL_EXE = "uninstall.exe"
APP_VERSION = "1.0.0"
APP_PUBLISHER = "Tix comin"
CONTACT_EMAIL = "dwlxjztz@qq.com"


# ---- 资源路径 ----
def _resolve_asset(rel):
    """PyInstaller onefile 兼容的资源定位"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), rel)


# ---- 快捷方式创建（使用 Windows COM pythoncom） ----
def create_shortcut(target_path, shortcut_path, icon_path=None, working_dir=None):
    """创建 .lnk 快捷方式"""
    try:
        from win32com.client import Dispatch
        shell = Dispatch("WScript.Shell")
        sc = shell.CreateShortcut(shortcut_path)
        sc.TargetPath = target_path
        if working_dir:
            sc.WorkingDirectory = working_dir
        else:
            sc.WorkingDirectory = os.path.dirname(target_path)
        if icon_path and os.path.exists(icon_path):
            sc.IconLocation = icon_path
        sc.WindowStyle = 3 if False else 1  # 正常窗口
        sc.Description = APP_NAME
        sc.Save()
        return True
    except Exception as e:
        print(f"[WARN] create_shortcut failed: {e}")
        return False


def get_desktop_dir():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        val, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        if val.startswith("%"):
            val = os.path.expandvars(val)
        return val
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Desktop")


def get_startmenu_dir():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        val, _ = winreg.QueryValueEx(key, "Programs")
        winreg.CloseKey(key)
        if val.startswith("%"):
            val = os.path.expandvars(val)
        return val
    except Exception:
        return os.path.join(os.path.expanduser("~"), "AppData", "Roaming",
                            "Microsoft", "Windows", "Start Menu", "Programs")


# ---- 写入 / 删除 注册表卸载项 ----
def write_uninstall_registry(install_dir, exe_size):
    """在 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall 下写卸载信息"""
    try:
        key_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
        winreg.SetValueEx(
            key, "UninstallString", 0, winreg.REG_SZ,
            f'"{os.path.join(install_dir, UNINSTALL_EXE)}"',
        )
        winreg.SetValueEx(
            key, "InstallLocation", 0, winreg.REG_SZ, install_dir,
        )
        winreg.SetValueEx(
            key, "DisplayIcon", 0, winreg.REG_SZ,
            os.path.join(install_dir, APP_EXE) + ",0",
        )
        winreg.SetValueEx(key, "Contact", 0, winreg.REG_SZ, CONTACT_EMAIL)
        winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ,
                          datetime.now().strftime("%Y%m%d"))
        try:
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD,
                              max(1, int(exe_size / 1024)))
        except Exception:
            pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[WARN] registry write failed: {e}")
        return False


# ---- 安装业务逻辑 ----
class InstallWorker:
    """实际安装逻辑（可在后台线程运行）"""

    def __init__(self, install_dir, create_desktop=True, create_startmenu=True):
        self.install_dir = install_dir
        self.create_desktop = create_desktop
        self.create_startmenu = create_startmenu

    def run(self, progress_callback=None, log_callback=None):
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        def prog(pct):
            if progress_callback:
                progress_callback(pct)

        log(f"开始安装到: {self.install_dir}")
        prog(5)

        # 1. 尝试创建目录，并测试写入权限（防止权限不足静默失败）
        try:
            os.makedirs(self.install_dir, exist_ok=True)
            # 测试写入权限
            test_file = os.path.join(self.install_dir, "_writetest.tmp")
            with open(test_file, "wb") as f:
                f.write(b"ok")
            os.remove(test_file)
        except PermissionError as e:
            raise RuntimeError(
                f"无法写入到安装目录：\n{self.install_dir}\n\n"
                f"原因：权限不足（{e}）。\n\n"
                f"建议：\n"
                f"  1) 选择其他目录，例如：C:\\Users\\{os.environ.get('USERNAME', '')}\\AppData\\Local\\Programs\\{APP_NAME}\n"
                f"  2) 或右键点击安装程序，选择「以管理员身份运行」"
            )
        except OSError as e:
            raise RuntimeError(
                f"无法创建安装目录：\n{self.install_dir}\n\n"
                f"错误信息：{e}\n\n"
                f"请检查路径是否合法、磁盘是否可写，并更换其他目录重试。"
            )

        log("✓ 已创建安装目录（权限正常）")
        prog(15)

        # 2. 从 payload.zip 解压
        payload = _resolve_asset("payload.zip")
        if not os.path.exists(payload):
            raise RuntimeError(f"找不到安装包资源: {payload}")

        log("正在解压程序文件...")
        with zipfile.ZipFile(payload, "r") as zf:
            names = zf.namelist()
            total = len(names)
            for i, name in enumerate(names):
                if name.endswith("/"):
                    continue
                out_path = os.path.join(self.install_dir, name)
                try:
                    out_dir = os.path.dirname(out_path)
                    if out_dir:
                        os.makedirs(out_dir, exist_ok=True)
                    with zf.open(name) as src, open(out_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                except PermissionError as e:
                    raise RuntimeError(
                        f"解压失败（权限不足）：无法写入 {out_path}\n"
                        f"请关闭可能占用该目录的程序后重试，或更换安装目录。"
                    )
                except OSError as e:
                    raise RuntimeError(f"解压失败：{out_path}\n错误：{e}")
                if i % 5 == 0 or i == total - 1:
                    pct = 15 + int((i / max(1, total)) * 55)  # 15~70
                    prog(pct)
        prog(70)
        log(f"✓ 已解压 {total} 个文件")

        # 计算主程序大小
        main_exe = os.path.join(self.install_dir, APP_EXE)
        exe_size = os.path.getsize(main_exe) if os.path.exists(main_exe) else 0
        prog(75)

        # 3. 创建桌面快捷方式
        if self.create_desktop:
            desktop = get_desktop_dir()
            os.makedirs(desktop, exist_ok=True)
            sc_path = os.path.join(desktop, f"{APP_NAME}.lnk")
            icon_path = main_exe
            if create_shortcut(main_exe, sc_path, icon_path=icon_path,
                               working_dir=self.install_dir):
                log(f"✓ 已创建桌面快捷方式")
            else:
                log("⚠ 桌面快捷方式创建失败")
        prog(85)

        # 4. 创建开始菜单快捷方式
        if self.create_startmenu:
            startmenu = get_startmenu_dir()
            app_menu = os.path.join(startmenu, APP_NAME)
            os.makedirs(app_menu, exist_ok=True)
            sc_app = os.path.join(app_menu, f"{APP_NAME}.lnk")
            sc_un = os.path.join(app_menu, f"卸载 {APP_NAME}.lnk")
            uninst_exe = os.path.join(self.install_dir, UNINSTALL_EXE)
            create_shortcut(main_exe, sc_app, icon_path=main_exe,
                            working_dir=self.install_dir)
            if os.path.exists(uninst_exe):
                create_shortcut(uninst_exe, sc_un, icon_path=uninst_exe,
                                working_dir=self.install_dir)
            log("✓ 已创建开始菜单快捷方式")
        prog(92)

        # 5. 写注册表
        if write_uninstall_registry(self.install_dir, exe_size):
            log("✓ 已写入系统卸载信息")
        else:
            log("⚠ 卸载信息写入失败（不影响使用）")
        prog(98)

        # 6. 写安装记录
        try:
            with open(os.path.join(self.install_dir, "install.log"), "w",
                      encoding="utf-8") as f:
                f.write(f"产品: {APP_NAME}\n")
                f.write(f"版本: {APP_VERSION}\n")
                f.write(f"开发者: {APP_PUBLISHER}\n")
                f.write(f"联系邮箱: {CONTACT_EMAIL}\n")
                f.write(f"安装时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"安装目录: {self.install_dir}\n")
        except Exception:
            pass
        prog(100)
        log(f"\n✓✓✓ 安装成功！\n安装目录: {self.install_dir}")
        return True


# ============================================================
#                    PyQt6 图形安装界面
# ============================================================
class InstallThread(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished_ok = pyqtSignal(bool, str)

    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def run(self):
        try:
            self.worker.run(
                progress_callback=lambda p: self.progress.emit(p),
                log_callback=lambda m: self.log.emit(m),
            )
            self.finished_ok.emit(True, "")
        except Exception as e:
            self.finished_ok.emit(False, str(e))


class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} 安装")
        self.setFixedSize(560, 480)

        # 应用图标
        icon_path = _resolve_asset("app_icon.ico")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._build_ui()
        self._set_default_dir()

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ---- 顶部标题 ----
        title = QLabel(f"{APP_NAME}")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #1e293b;"
        )
        sub = QLabel(f"版本 {APP_VERSION}   |   {APP_PUBLISHER}")
        sub.setStyleSheet("color: #64748b; font-size: 12px;")
        root.addWidget(title)
        root.addWidget(sub)

        # 分隔线
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #e2e8f0;")
        root.addWidget(line1)

        # ---- 安装目录 ----
        dir_label = QLabel("安装目录：")
        dir_label.setStyleSheet("color: #334155; font-size: 13px;")
        root.addWidget(dir_label)

        dir_row = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setStyleSheet(
            "padding: 8px 10px; border: 1px solid #cbd5e1;"
            "border-radius: 6px; background: #fff; font-size: 13px;"
        )
        btn_browse = QPushButton("浏览...")
        btn_browse.setStyleSheet(
            "padding: 8px 14px; background: #f1f5f9; border: 1px solid #cbd5e1;"
            "border-radius: 6px; color: #334155; font-size: 13px;"
        )
        btn_browse.clicked.connect(self._browse)
        dir_row.addWidget(self.dir_input, 1)
        dir_row.addWidget(btn_browse)
        root.addLayout(dir_row)

        # 推荐路径提示 + 快捷按钮
        tip_row = QHBoxLayout()
        self.dir_tip = QLabel("💡 推荐使用默认路径（无需管理员权限，任何电脑都可安装）")
        self.dir_tip.setStyleSheet(
            "color: #64748b; font-size: 11px; background: #f8fafc;"
            "padding: 6px 10px; border-radius: 4px;"
        )
        self.dir_tip.setWordWrap(True)
        tip_row.addWidget(self.dir_tip, 1)

        btn_rec = QPushButton("一键使用推荐路径")
        btn_rec.setStyleSheet(
            "padding: 4px 10px; background: #dbeafe; border: 1px solid #93c5fd;"
            "border-radius: 4px; color: #1e40af; font-size: 11px;"
        )
        btn_rec.clicked.connect(self._use_recommended)
        tip_row.addWidget(btn_rec)
        root.addLayout(tip_row)

        # ---- 快捷方式选项 ----
        self.cb_desktop = QCheckBox("创建桌面快捷方式")
        self.cb_desktop.setChecked(True)
        self.cb_startmenu = QCheckBox("创建开始菜单快捷方式")
        self.cb_startmenu.setChecked(True)
        for cb in (self.cb_desktop, self.cb_startmenu):
            cb.setStyleSheet(
                "color: #334155; font-size: 13px; padding: 4px 0;"
            )
        root.addWidget(self.cb_desktop)
        root.addWidget(self.cb_startmenu)

        # ---- 进度条 ----
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet(
            "QProgressBar { border: 1px solid #cbd5e1; border-radius: 6px;"
            "background: #f8fafc; height: 22px; text-align: center; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #3b82f6, stop:1 #06b6d4); border-radius: 6px; }"
        )
        root.addWidget(self.progress)

        # ---- 日志区 ----
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(
            "background: #0f172a; color: #e2e8f0; border: 1px solid #1e293b;"
            "border-radius: 6px; padding: 8px; font-family: Consolas, monospace;"
            "font-size: 12px;"
        )
        self.log_box.setFixedHeight(140)
        root.addWidget(self.log_box, 1)

        # ---- 底部按钮 ----
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_install = QPushButton("安装")
        self.btn_install.setFixedHeight(38)
        self.btn_install.setFixedWidth(110)
        self.btn_install.setStyleSheet(
            "QPushButton { background: #2563eb; color: #fff; border: none;"
            "border-radius: 6px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #1d4ed8; }"
            "QPushButton:disabled { background: #94a3b8; }"
        )
        self.btn_install.clicked.connect(self._do_install)

        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setFixedWidth(90)
        btn_cancel.setStyleSheet(
            "QPushButton { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;"
            "border-radius: 6px; font-size: 14px; }"
            "QPushButton:hover { background: #e2e8f0; }"
        )
        btn_cancel.clicked.connect(self.close)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_install)
        root.addLayout(btn_row)

        self.setLayout(root)

    def _set_default_dir(self):
        default = self._recommended_path()
        self.dir_input.setText(default)

    def _recommended_path(self):
        try:
            local_app = os.environ.get("LOCALAPPDATA") or \
                        os.path.join(os.path.expanduser("~"), "AppData", "Local")
            return os.path.join(local_app, "Programs", APP_NAME)
        except Exception:
            return os.path.join(os.path.expanduser("~"), APP_NAME)

    def _use_recommended(self):
        self.dir_input.setText(self._recommended_path())
        if hasattr(self, "dir_tip"):
            self.dir_tip.setText("✅ 已切换到推荐路径（无需管理员权限）")

    def _test_writable(self, path):
        """测试路径是否可写，返回 (ok, 说明)。"""
        try:
            os.makedirs(path, exist_ok=True)
            test = os.path.join(path, "_wtest_" + str(os.getpid()) + ".tmp")
            with open(test, "wb") as f:
                f.write(b"ok")
            os.remove(test)
            return True, ""
        except PermissionError as e:
            return False, f"权限不足：该目录需要管理员权限才能写入（{e}）"
        except OSError as e:
            return False, f"路径不可用：{e}"

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择安装目录",
                                             self.dir_input.text())
        if d:
            self.dir_input.setText(os.path.join(d, APP_NAME))

    def _log(self, msg):
        self.log_box.append(msg)

    def _do_install(self):
        install_dir = self.dir_input.text().strip()
        if not install_dir:
            QMessageBox.warning(self, "提示", "请选择安装目录")
            return

        # 检测路径合法性 & 写入权限
        ok, reason = self._test_writable(install_dir)
        if not ok:
            rec = self._recommended_path()
            reply = QMessageBox.warning(
                self, "安装目录不可用",
                f"{reason}\n\n"
                f"当前目录：{install_dir}\n\n"
                f"建议：\n"
                f"  • 切换到推荐目录：{rec}\n"
                f"  • 或关闭安装程序，右键选择「以管理员身份运行」后重试\n\n"
                f"是否立即切换到推荐目录？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.dir_input.setText(rec)
                self._use_recommended()
            return

        # 目录已存在且非空：提示（允许覆盖）
        if os.path.isdir(install_dir):
            try:
                has_files = any(os.scandir(install_dir))
            except Exception:
                has_files = False
            if has_files:
                reply = QMessageBox.question(
                    self, "目录已存在",
                    f"目录 {install_dir} 已有文件，是否继续安装？\n"
                    "（同名文件将被覆盖）",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        self.btn_install.setEnabled(False)
        self.progress.setValue(0)
        self.log_box.clear()

        worker = InstallWorker(
            install_dir=install_dir,
            create_desktop=self.cb_desktop.isChecked(),
            create_startmenu=self.cb_startmenu.isChecked(),
        )
        self._thread = InstallThread(worker)
        self._thread.progress.connect(self.progress.setValue)
        self._thread.log.connect(self._log)
        self._thread.finished_ok.connect(self._on_finish)
        self._thread.start()

    def _on_finish(self, ok, err_msg):
        self.btn_install.setEnabled(True)
        if ok:
            self.progress.setValue(100)
            reply = QMessageBox.information(
                self, "安装成功",
                f"{APP_NAME} 已成功安装！\n\n"
                f"安装目录：{self.dir_input.text()}\n\n"
                "是否立即运行程序？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    import subprocess
                    subprocess.Popen(
                        [os.path.join(self.dir_input.text(), APP_EXE)],
                        cwd=self.dir_input.text(),
                    )
                except Exception:
                    pass
            self.close()
        else:
            QMessageBox.critical(self, "安装失败",
                                 f"安装过程中出现错误：\n{err_msg}")


# ============================================================
#                        入口
# ============================================================
def main():
    if not HAS_PYQT:
        print("PyQt6 不可用，请在安装 PyQt6 后重新打包")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = InstallerWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
