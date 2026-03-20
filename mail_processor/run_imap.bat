@echo off
chcp 65001 >nul
title 邮件处理工具
echo ========================================
echo    邮件处理工具 - IMAP版
echo ========================================
echo.
echo 正在启动...
cd /d "%~dp0"
python mail_processor_imap.py
pause
