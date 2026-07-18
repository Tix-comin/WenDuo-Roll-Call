# -*- coding: utf-8 -*-
"""
闻铎点名器 - 卸载程序
在安装目录下运行，删除自身所在目录、快捷方式和注册表项。
"""
import sys
import os
import time
import shutil
import winreg

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
        QProgressBar, QMessageBox, QTextEdit, QFrame, QCheckBox,
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QIcon
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False


APP_NAME = "闻铎点名器"
APP_EXE = "闻铎点名器.exe"


def _resolve_asset(rel):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), rel)


def get_desktop_dir():
    try:
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


def get_install_dir():
    """卸载器所在目录就是安装目录（PyInstaller 打包时返回 exe 目录）"""
    # 注意：若用 PyInstaller 打包为 onefile，sys.executable 才是 uninstall.exe 的位置
    # 但 sys.argv[0] / os.path.abspath(__file__) 也能识别
    frozen = getattr(sys, "frozen", False)
    if frozen:
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def delete_if_exists(path, is_dir=False):
    try:
        if os.path.exists(path):
            if is_dir:
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
            return True
    except Exception:
        pass
    return False


class UninstallWorker:
    def __init__(self, install_dir, remove_userdata=True):
        self.install_dir = install_dir
        self.remove_userdata = remove_userdata

    def run(self, progress_cb=None, log_cb=None):
        def log(m):
            if log_cb:
                log_cb(m)
            else:
                print(m)

        def prog(p):
            if progress_cb:
                progress_cb(p)

        log(f"安装目录: {self.install_dir}")
        prog(10)

        # 1. 删除桌面快捷方式
        desktop = get_desktop_dir()
        sc = os.path.join(desktop, f"{APP_NAME}.lnk")
        if delete_if_exists(sc):
            log("✓ 已删除桌面快捷方式")
        else:
            log("- 未找到桌面快捷方式")
        prog(25)

        # 2. 删除开始菜单快捷方式文件夹
        startmenu = get_startmenu_dir()
        app_menu = os.path.join(startmenu, APP_NAME)
        if delete_if_exists(app_menu, is_dir=True):
            log("✓ 已删除开始菜单快捷方式")
        else:
            log("- 未找到开始菜单快捷方式")
        prog(45)

        # 3. 删除注册表卸载信息
        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            log("✓ 已删除系统卸载信息")
        except FileNotFoundError:
            log("- 未找到注册表信息")
        except Exception as e:
            log(f"⚠ 注册表删除失败: {e}")
        prog(65)

        # 4. 删除用户数据（可选）
        if self.remove_userdata:
            data_dir = os.path.join(os.path.expanduser("~"), ".wenduo_picker")
            if os.path.exists(data_dir):
                try:
                    shutil.rmtree(data_dir, ignore_errors=True)
                    log("✓ 已删除用户数据目录")
                except Exception:
                    log("⚠ 用户数据目录未完全清除")
            else:
                log("- 未发现用户数据目录")
        prog(80)

        # 5. 自身目录删除 —— 由于 uninstall.exe 正在运行，无法直接删除自己
        #    做法：在系统临时目录放一个 bat，延迟删除 install_dir 和自身
        try:
            import tempfile
            bat_content = (
                "@echo off\r\n"
                f"timeout /t 1 /nobreak >nul\r\n"
                f'rmdir /s /q "{self.install_dir}"\r\n'
                'del "%~f0"\r\n'
            )
            bat_path = os.path.join(tempfile.gettempdir(),
                                    f"_uninst_{int(time.time()*1000)}.bat")
            with open(bat_path, "w", encoding="gbk") as f:
                f.write(bat_content)
            # 不立即启动 bat，避免安装目录里还有正在运行的 exe
            self._bat_path = bat_path
            log("✓ 已准备延迟清理程序目录（退出后自动执行）")
        except Exception as e:
            log(f"⚠ 无法创建清理脚本: {e}")
        prog(100)
        log(f"\n✓✓✓ 卸载完成！")
        return True

    def launch_cleanup_bat(self):
        """启动延迟删除的 bat（用于卸载窗口关闭后）"""
        if hasattr(self, "_bat_path") and self._bat_path:
            try:
                import subprocess
                subprocess.Popen(
                    ["cmd.exe", "/c", self._bat_path],
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                )
            except Exception:
                pass


# ---------- PyQt 界面 ----------
class UninstallThread(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished_ok = pyqtSignal(bool)

    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def run(self):
        try:
            self.worker.run(
                progress_cb=lambda p: self.progress.emit(p),
                log_cb=lambda m: self.log.emit(m),
            )
            self.finished_ok.emit(True)
        except Exception as e:
            self.log.emit(f"错误: {e}")
            self.finished_ok.emit(False)


class UninstallWindow(QWidget):
    def __init__(self, install_dir):
        super().__init__()
        self.install_dir = install_dir
        self.setWindowTitle(f"卸载 {APP_NAME}")
        self.setFixedSize(480, 360)

        icon_path = _resolve_asset("app_icon.ico")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        root = QVBoxLayout()
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        title = QLabel(f"卸载 {APP_NAME}")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1e293b;")
        root.addWidget(title)

        info = QLabel(f"将从以下位置移除程序：\n{self.install_dir}")
        info.setStyleSheet("color: #64748b; font-size: 12px;")
        info.setWordWrap(True)
        root.addWidget(info)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #e2e8f0;")
        root.addWidget(line1)

        self.cb_data = QCheckBox("同时删除用户数据和历史记录")
        self.cb_data.setChecked(True)
        self.cb_data.setStyleSheet("color: #334155; font-size: 13px; padding: 4px 0;")
        root.addWidget(self.cb_data)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet(
            "QProgressBar { border: 1px solid #cbd5e1; border-radius: 6px;"
            "background: #f8fafc; height: 22px; text-align: center; }"
            "QProgressBar::chunk { background: #ef4444; border-radius: 6px; }"
        )
        root.addWidget(self.progress)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(
            "background: #0f172a; color: #e2e8f0; border: 1px solid #1e293b;"
            "border-radius: 6px; padding: 8px; font-family: Consolas, monospace;"
            "font-size: 12px;"
        )
        root.addWidget(self.log_box, 1)

        btn_row = QVBoxLayout()
        btn_row_h = QVBoxLayout()
        # just use vertical to keep simple
        h = QVBoxLayout()

        h2 = QVBoxLayout()
        # simple: one big button "卸载" + cancel
        self.btn_uninst = QPushButton("开始卸载")
        self.btn_uninst.setFixedHeight(40)
        self.btn_uninst.setStyleSheet(
            "QPushButton { background: #ef4444; color: #fff; border: none;"
            "border-radius: 6px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #dc2626; }"
            "QPushButton:disabled { background: #94a3b8; }"
        )
        self.btn_uninst.clicked.connect(self._do_uninstall)
        root.addWidget(self.btn_uninst)

        self.setLayout(root)
        self._worker = None

    def _log(self, m):
        self.log_box.append(m)

    def _do_uninstall(self):
        reply = QMessageBox.question(
            self, "确认",
            f"确定要卸载 {APP_NAME} 吗？\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.btn_uninst.setEnabled(False)
        self.progress.setValue(0)
        self.log_box.clear()

        self._worker = UninstallWorker(
            self.install_dir,
            remove_userdata=self.cb_data.isChecked(),
        )
        self._thread = UninstallThread(self._worker)
        self._thread.progress.connect(self.progress.setValue)
        self._thread.log.connect(self._log)
        self._thread.finished_ok.connect(self._on_finish)
        self._thread.start()

    def _on_finish(self, ok):
        self.btn_uninst.setEnabled(True)
        if ok:
            QMessageBox.information(
                self, "卸载完成",
                f"{APP_NAME} 已成功卸载。\n程序目录将在关闭本窗口后清除。"
            )
            # 关闭后启动延迟清理
            if self._worker:
                self._worker.launch_cleanup_bat()
            self.close()
        else:
            QMessageBox.warning(self, "卸载未完成",
                                "卸载过程中出现错误，请手动检查。")


def main_gui():
    install_dir = get_install_dir()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = UninstallWindow(install_dir)
    w.show()
    sys.exit(app.exec())


def main_cli():
    """无 GUI 兜底模式"""
    install_dir = get_install_dir()
    print(f"卸载 {APP_NAME}")
    print(f"安装目录: {install_dir}")
    worker = UninstallWorker(install_dir, remove_userdata=True)
    try:
        worker.run()
    except Exception as e:
        print(f"错误: {e}")
    worker.launch_cleanup_bat()
    input("按回车退出...")


def main():
    if HAS_PYQT:
        try:
            main_gui()
        except Exception:
            main_cli()
    else:
        main_cli()


if __name__ == "__main__":
    main()
