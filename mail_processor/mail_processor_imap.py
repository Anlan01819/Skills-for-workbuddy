# -*- coding: utf-8 -*-
"""
阿里云企业邮箱邮件处理工具 - IMAP版
使用IMAP协议连接阿里云企业邮箱
"""

import os
import sys
import re
import email
from datetime import datetime
from pathlib import Path
from imap_tools import MailBox, AND
from email.header import decode_header
import base64

# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ==================== 配置项 ====================
try:
    from config import EMAIL_ACCOUNT, EMAIL_PASSWORD, BASE_SAVE_PATH, IMAP_SERVER, IMAP_PORT
except ImportError:
    # 默认配置
    EMAIL_ACCOUNT = ""  # 请在config.py中设置
    EMAIL_PASSWORD = ""  # 请在config.py中设置
    BASE_SAVE_PATH = r"D:\许志文\文秘\日常\业务通告"
    IMAP_SERVER = "imap.qiye.aliyun.com"
    IMAP_PORT = 993
# ==================== 配置结束 ====================


def safe_print(text):
    """安全打印，处理编码问题"""
    try:
        print(text)
    except:
        print(str(text).encode('utf-8', errors='ignore').decode('utf-8'))


def get_today_folder_name() -> str:
    now = datetime.now()
    return f"{now.year}年{now.month}月{now.day}日"


def sanitize_filename(filename: str) -> str:
    illegal_chars = r'[\/\\:*?"<>|\n\r\t]'
    filename = re.sub(illegal_chars, '_', filename)
    filename = filename.strip()
    if len(filename) > 100:
        filename = filename[:100]
    return filename


def decode_email_header(header_value: str) -> str:
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            if encoding:
                result += part.decode(encoding)
            else:
                result += part.decode('utf-8', errors='ignore')
        else:
            result += str(part)
    return result


def extract_company_name(mail_subject: str, attachment_names: list) -> str:
    patterns = [
        r'^(.+?公司)',
        r'^(.+?股份)',
        r'^(.+?集团)',
        r'^(.+?有限)',
    ]

    for pattern in patterns:
        match = re.search(pattern, mail_subject)
        if match:
            return match.group(1)

    for attach_name in attachment_names:
        for pattern in patterns:
            match = re.search(pattern, attach_name)
            if match:
                return match.group(1)

    return ""


def get_attachments(msg_obj, folder_path: Path):
    """下载邮件附件"""
    attachment_files = []
    
    # msg_obj 是原始的email.message对象
    for part in msg_obj.walk():
        if part.get_content_disposition() == 'attachment':
            filename = part.get_filename()
            if filename:
                filename = decode_email_header(filename)
                filename = sanitize_filename(filename)
                
                file_path = folder_path / filename
                
                try:
                    data = part.get_payload(decode=True)
                    if data:
                        with open(file_path, 'wb') as f:
                            f.write(data)
                        attachment_files.append(filename)
                        safe_print(f"  已下载附件: {filename}")
                except Exception as e:
                    safe_print(f"  下载附件失败: {filename}, 错误: {e}")
    
    return attachment_files


def clean_html_content(html_text: str) -> str:
    """清理HTML内容，提取纯文本"""
    import html
    
    if not html_text:
        return ""
    
    text = html_text
    
    # 1. 首先解码所有HTML实体（对纯文本和HTML都适用）
    text = html.unescape(text)
    
    # 2. 检查是否包含HTML标签
    has_html = '<html' in text.lower() or '<div' in text.lower() or '<p' in text.lower() or '<br' in text.lower()
    
    if has_html:
        # 移除HTML标签
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除CSS和样式属性残留
        text = re.sub(r'[\w-]+:\s*[^;]+;?', '', text)
        
        # 转换<br>和<p>为换行
        text = text.replace('<br>', '\n')
        text = text.replace('<br/>', '\n')
        text = text.replace('<br />', '\n')
        text = text.replace('</p>', '\n')
        text = text.replace('</div>', '\n')
    
    # 3. 再次解码HTML实体（处理可能遗漏的）
    text = html.unescape(text)
    
    # 4. 移除多余空白但保留段落
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = re.sub(r'\s+', ' ', line).strip()
        if line:
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # 5. 移除邮件签名标记
    text = re.sub(r'[-_]{3,}\s*(Sent|from|发自)?.*$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'本邮件由.*发送', '', text)
    
    return text.strip()


def get_email_body(msg_obj) -> str:
    """获取邮件正文"""
    body = ""
    
    if msg_obj.is_multipart():
        for part in msg_obj.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))
            
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                        break
                except:
                    pass
            elif content_type == 'text/html' and 'attachment' not in content_disposition and not body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                except:
                    pass
    else:
        try:
            payload = msg_obj.get_payload(decode=True)
            if payload:
                charset = msg_obj.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
        except:
            pass
    
    return body


def process_emails():
    """处理邮件主函数"""
    safe_print("=" * 50)
    safe_print("邮件处理工具 - IMAP版")
    safe_print("=" * 50)
    
    account = EMAIL_ACCOUNT
    password = EMAIL_PASSWORD
    
    if not account:
        account = input("请输入邮箱账号: ").strip()
    if not password:
        password = input("请输入密码或授权码: ").strip()
    
    # 创建今天日期的文件夹
    today_folder_name = get_today_folder_name()
    today_folder = Path(BASE_SAVE_PATH) / today_folder_name
    today_folder.mkdir(parents=True, exist_ok=True)
    safe_print(f"保存目录: {today_folder}")
    
    # 连接邮箱
    safe_print(f"\n正在连接邮箱 ({IMAP_SERVER})...")
    
    try:
        with MailBox(IMAP_SERVER, IMAP_PORT).login(account, password) as mailbox:
            safe_print("登录成功!")
            
            # 获取文件夹列表
            folders = mailbox.folder.list()
            safe_print(f"邮箱文件夹: {[f.name for f in folders[:5]]}...")
            
            # 搜索所有未读邮件（不限制日期）
            safe_print(f"\n正在搜索所有未读邮件...")
            
            # 只获取未读邮件
            messages = mailbox.fetch(
                AND(seen=False), 
                limit=50, 
                reverse=True
            )
            
            messages_list = list(messages)
            safe_print(f"找到 {len(messages_list)} 封未读邮件")
            
            if not messages_list:
                safe_print("没有未读邮件，获取最近10封...")
                messages_list = list(mailbox.fetch(limit=10, reverse=True))
            
            if not messages_list:
                safe_print("没有邮件")
                return
            
            safe_print(f"\n将处理 {len(messages_list)} 封邮件...")
            
            success_count = 0
            for i, msg in enumerate(messages_list):
                safe_print(f"\n--- 处理第 {i+1}/{len(messages_list)} 封邮件 ---")
                
                try:
                    # 获取邮件信息
                    subject = decode_email_header(msg.subject)
                    from_addr = decode_email_header(msg.from_)
                    
                    safe_print(f"标题: {subject}")
                    safe_print(f"发件人: {from_addr}")
                    
                    # 获取原始email对象
                    msg_obj = msg.obj
                    
                    # 获取附件列表
                    attachment_names = []
                    for part in msg_obj.walk():
                        if part.get_content_disposition() == 'attachment':
                            filename = part.get_filename()
                            if filename:
                                filename = decode_email_header(filename)
                                attachment_names.append(filename)
                    
                    safe_print(f"附件: {attachment_names}")
                    
                    # 提取公司名
                    company_name = extract_company_name(subject, attachment_names)
                    safe_print(f"公司名: {company_name}")
                    
                    # 创建邮件文件夹
                    folder_name = f"{company_name}_{subject}" if company_name else subject
                    folder_name = sanitize_filename(folder_name)
                    
                    if len(folder_name) > 150:
                        folder_name = folder_name[:150]
                    
                    # 保存到今天运行的日期目录
                    mail_folder = today_folder / folder_name
                    mail_folder.mkdir(parents=True, exist_ok=True)
                    safe_print(f"创建文件夹: {mail_folder}")
                    
                    # 保存附件
                    downloaded_files = get_attachments(msg_obj, mail_folder)
                    
                    # 保存邮件正文（过滤HTML后）
                    body = get_email_body(msg_obj)
                    if body:
                        # 清理HTML内容
                        body = clean_html_content(body)
                        body_file = mail_folder / "邮件正文.txt"
                        try:
                            with open(body_file, 'w', encoding='utf-8') as f:
                                f.write(f"发件人: {from_addr}\n")
                                f.write(f"主题: {subject}\n")
                                f.write(f"日期: {msg.date}\n")
                                f.write("-" * 50 + "\n")
                                f.write(body)
                            safe_print(f"  已保存邮件正文（已过滤HTML）")
                        except Exception as e:
                            safe_print(f"  保存邮件正文失败: {e}")
                    
                    # 标记邮件为已读
                    try:
                        # 使用 uid 标记为已读
                        if hasattr(msg, 'uid') and msg.uid:
                            mailbox.flag(msg.uid, ['\\Seen'], True)
                            safe_print(f"  已标记为已读")
                    except Exception as e:
                        safe_print(f"  标记已读失败: {e}")
                    
                    success_count += 1
                    safe_print(f"  处理完成!")
                    
                except Exception as e:
                    safe_print(f"处理邮件失败: {e}")
            
            safe_print("\n" + "=" * 50)
            safe_print(f"处理完成! 成功处理 {success_count}/{len(messages_list)} 封邮件")
            safe_print("=" * 50)
            
    except Exception as e:
        safe_print(f"连接邮箱失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    process_emails()
