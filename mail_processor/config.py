# -*- coding: utf-8 -*-
"""
配置文件 - 邮件处理工具通用配置
请根据你的邮箱类型修改以下配置
"""

# ==================== 邮箱账号配置（必填）====================
# 你的邮箱账号
EMAIL_ACCOUNT = ""

# 邮箱密码或授权码（必填）
# QQ邮箱：使用授权码
# 阿里云企业邮箱：使用授权码
# Gmail：使用应用专用密码
# 163邮箱：使用授权码
EMAIL_PASSWORD = ""

# ==================== 保存路径配置（必填）====================
# 文件保存根目录
BASE_SAVE_PATH = r"D:\业务通告"

# ==================== 邮箱服务器配置 ====================
# 根据你的邮箱类型修改以下配置：

# 常用邮箱IMAP服务器地址：
#   QQ邮箱:     imap.qq.com
#   阿里云:     imap.qiye.aliyun.com
#   Gmail:     imap.gmail.com
#   163邮箱:   imap.163.com
#   Outlook:   outlook.office365.com

IMAP_SERVER = "imap.qq.com"  # 修改为你的邮箱IMAP服务器地址

IMAP_PORT = 993  # 一般不需要修改，993是IMAP的默认SSL端口
