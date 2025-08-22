#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import tempfile
from filelock import FileLock
from PyQt5.QtWidgets import QApplication, QMessageBox
from zmathboard.app import ZMathJBoardApp


def check_single_instance(app):
    lock_file_name = "ZMathJBoardF_SingleInstance.lock"
    lock_file_path = tempfile.gettempdir() + "/" + lock_file_name
    lock = FileLock(lock_file_path)

    try:
        lock.acquire(timeout=1)
    except Exception:
        QMessageBox.critical(
            None,
            "启动失败",
            "ZMathJBoardF 已在运行中，请勿重复启动！\n若确认无程序运行，可重启电脑后再尝试。"
        )
        sys.exit(0)  # 退出当前进程
    else:
        # 保留锁对象，避免被垃圾回收
        global app_lock
        app_lock = lock


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("ZMathJBoardF")
    app.setApplicationVersion("1.1")
    check_single_instance(app)
    window = ZMathJBoardApp()
    window.show()
    
    sys.exit(app.exec_())