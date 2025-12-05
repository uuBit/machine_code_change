#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import json
import uuid
import shutil
import platform
from datetime import datetime
import errno

try:
    # Python 3
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    # Python 2 回退（如果需要）
    import Tkinter as tk
    import tkMessageBox as messagebox


def get_storage_path():
    """获取配置文件路径"""
    system = platform.system().lower()
    home = os.path.expanduser('~')
    
    if system == 'windows':
        return os.path.join(os.getenv('APPDATA'), 'Cursor', 'User', 'globalStorage', 'storage.json')
    elif system == 'darwin':  # macOS
        return os.path.join(home, 'Library', 'Application Support', 'Cursor', 'User', 'globalStorage', 'storage.json')
    else:  # Linux
        return os.path.join(home, '.config', 'Cursor', 'User', 'globalStorage', 'storage.json')


def generate_random_id():
    """生成随机ID (64位十六进制)"""
    return uuid.uuid4().hex + uuid.uuid4().hex


def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4())


def backup_file(file_path):
    """创建配置文件备份"""
    if os.path.exists(file_path):
        backup_path = '{}.backup_{}'.format(
            file_path,
            datetime.now().strftime('%Y%m%d_%H%M%S')
        )
        shutil.copy2(file_path, backup_path)
        print('已创建备份文件:', backup_path)


def ensure_dir_exists(path):
    """确保目录存在（兼容 Python 2/3）"""
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


def update_storage_file(file_path):
    """更新存储文件中的ID"""
    # 生成新的ID
    new_machine_id = generate_random_id()
    new_mac_machine_id = generate_random_id()
    new_dev_device_id = generate_uuid()
    
    # 确保目录存在
    ensure_dir_exists(os.path.dirname(file_path))
    
    # 读取或创建配置文件
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except ValueError:
            data = {}
    else:
        data = {}
    
    # 更新ID
    data['telemetry.machineId'] = new_machine_id
    data['telemetry.macMachineId'] = new_mac_machine_id
    data['telemetry.devDeviceId'] = new_dev_device_id
    data['telemetry.sqmId'] = '{' + str(uuid.uuid4()).upper() + '}'
    
    # 写入文件
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    return new_machine_id, new_mac_machine_id, new_dev_device_id


def run_update_with_result():
    """执行更新逻辑并返回(成功标志, 消息字符串)"""
    try:
        storage_path = get_storage_path()
        # 更新 ID（不再创建备份）
        machine_id, mac_machine_id, dev_device_id = update_storage_file(storage_path)

        msg_lines = [
            u"配置文件路径: {}".format(storage_path),
            u"", 
            u"已成功修改 ID:",
            u"machineId: {}".format(machine_id),
            u"macMachineId: {}".format(mac_machine_id),
            u"devDeviceId: {}".format(dev_device_id),
        ]
        return True, "\n".join(msg_lines)
    except Exception as e:
        return False, u"错误: {}".format(e)


def create_gui():
    """创建并运行图形界面"""
    root = tk.Tk()
    root.title("Cursor Machine ID 工具")
    root.geometry("620x380")

    # 顶部说明
    label_desc = tk.Label(
        root,
        text=u"一键重置 Cursor 的机器 ID (machineId / macMachineId / devDeviceId)",
        anchor="w",
        justify="left"
    )
    label_desc.pack(fill="x", padx=10, pady=(10, 5))

    # 显示当前配置文件路径
    storage_path = get_storage_path()
    frame_path = tk.Frame(root)
    frame_path.pack(fill="x", padx=10, pady=5)

    tk.Label(frame_path, text=u"配置文件路径:").pack(side="left")

    entry_path = tk.Entry(frame_path)
    entry_path.insert(0, storage_path)
    entry_path.config(state="readonly")
    entry_path.pack(side="left", fill="x", expand=True, padx=(5, 0))

    # 结果显示区域
    text_result = tk.Text(root, height=12)
    text_result.pack(fill="both", expand=True, padx=10, pady=(5, 10))

    def append_result(text):
        text_result.config(state="normal")
        text_result.delete("1.0", "end")
        text_result.insert("end", text)
        text_result.see("end")
        text_result.config(state="disabled")

    def on_run_clicked():
        ok, msg = run_update_with_result()
        append_result(msg)
        if ok:
            messagebox.showinfo(u"完成", u"已成功重置 ID")
        else:
            messagebox.showerror(u"错误", msg)

    frame_btn = tk.Frame(root)
    frame_btn.pack(fill="x", padx=10, pady=(0, 10))

    btn_run = tk.Button(frame_btn, text=u"生成新 ID", command=on_run_clicked)
    btn_run.pack(side="left")

    root.mainloop()


def main():
    """主函数：启动图形界面"""
    try:
        create_gui()
    except Exception as e:
        print('错误:', str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()