#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import json
import uuid
import shutil
import platform
from datetime import datetime, timedelta
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


def clean_backup_files(days=3):
    """生成备份清理计划（不实际删除），返回 (ok, 消息文本, 待删除文件列表)。

    规则：
    - 只考虑当前 storage.json 同目录下、以 "storage.json.backup_" 开头的文件；
    - 解析文件名中的时间戳 YYYYMMDD_HHMMSS；
    - 早于指定天数 (days) 的备份才有资格被删除；
    - 始终保留最新的一份备份（即使它早于 days 天也不删）。
    """
    try:
        storage_path = get_storage_path()
        directory = os.path.dirname(storage_path)
        if not directory or not os.path.isdir(directory):
            return False, u"未找到配置目录: {}".format(directory), []

        base_name = os.path.basename(storage_path)
        prefix = base_name + ".backup_"

        backups = []  # [(full_path, dt)]
        for name in os.listdir(directory):
            if not name.startswith(prefix):
                continue
            full_path = os.path.join(directory, name)
            if not os.path.isfile(full_path):
                continue

            ts_str = name[len(prefix):]
            dt = None
            try:
                dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            except ValueError:
                # 时间戳解析失败的备份，不参与自动删除
                pass
            backups.append((full_path, dt))

        if not backups:
            return True, u"未找到任何备份文件。", []

        # 按时间排序，无法解析时间戳的放在最后（不自动删除）
        backups_sorted = sorted(backups, key=lambda x: x[1] or datetime.max)
        newest_path, newest_dt = backups_sorted[-1]

        # 根据传入的天数计算阈值
        cutoff = datetime.now() - timedelta(days=days)

        to_delete = []
        for path, dt in backups_sorted:
            # 始终保留最新一份
            if path == newest_path:
                continue
            # 没有有效时间戳的不自动删除
            if dt is None:
                continue
            # 只删除早于 days 天的
            if dt < cutoff:
                to_delete.append((path, dt))

        # 生成预览信息
        lines = []
        if not to_delete:
            lines.append(u"找到 {} 个备份文件，但没有符合清理条件的备份。".format(len(backups)))
            lines.append(u"（规则：早于 {} 天，且不是最新一份；最新一份始终保留。）".format(days))
            return True, "\n".join(lines), []

        lines.append(u"总共找到 {} 个备份文件。".format(len(backups)))
        lines.append(u"将删除以下备份（早于 {} 天，且不是最新一份）：".format(days))
        for path, dt in to_delete:
            if dt is not None:
                dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                dt_str = u"时间未知"
            lines.append(u"{}    时间: {}".format(path, dt_str))

        if newest_dt is not None:
            newest_str = newest_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            newest_str = u"时间未知"
        lines.append("")
        lines.append(u"将保留最新的一份备份:")
        lines.append(u"{}    时间: {}".format(newest_path, newest_str))

        preview_text = "\n".join(lines)
        # 返回待删除的路径列表（仅路径，不含时间）
        return True, preview_text, [p for p, _ in to_delete]

    except Exception as e:
        return False, u"生成备份清理计划时出错: {}".format(e), []


def delete_all_backups():
    """生成“删除所有备份”的计划，返回 (ok, 消息文本, 待删除文件列表)。"""
    try:
        storage_path = get_storage_path()
        directory = os.path.dirname(storage_path)
        if not directory or not os.path.isdir(directory):
            return False, u"未找到配置目录: {}".format(directory), []

        base_name = os.path.basename(storage_path)
        prefix = base_name + ".backup_"

        to_delete = []
        for name in os.listdir(directory):
            if not name.startswith(prefix):
                continue
            full_path = os.path.join(directory, name)
            if os.path.isfile(full_path):
                to_delete.append(full_path)

        if not to_delete:
            return True, u"未找到任何备份文件。", []

        lines = [u"将删除以下所有备份文件:"]
        lines.extend(to_delete)
        preview_text = "\n".join(lines)
        return True, preview_text, to_delete
    except Exception as e:
        return False, u"生成删除所有备份计划时出错: {}".format(e), []


def create_gui():
    """创建并运行图形界面"""
    root = tk.Tk()
    root.title("XMachineID")
    root.geometry("620x380")
    root.configure(bg="#dbe2ef")

    # 顶部说明
    label_desc = tk.Label(
        root,
        text=u"重置设备的机器 ID (machineId（设备 ID） / macMachineId（Mac 设备 ID） / devDeviceId（开发设备 ID）)",
        anchor="w",
        justify="left",
        bg="#dbe2ef"
    )

    label_desc.pack(fill="x", padx=10, pady=(10, 5))

    # 显示当前配置文件路径
    storage_path = get_storage_path()
    frame_path = tk.Frame(root, bg="#dbe2ef")

    frame_path.pack(fill="x", padx=10, pady=5)

    tk.Label(frame_path, text=u"配置文件路径:", bg="#dbe2ef").pack(side="left")

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

    def on_clean_clicked():
        # 从输入框获取天数，非法输入则回退到默认 3 天
        raw_days = entry_days.get().strip()
        try:
            days = int(raw_days)
            if days <= 0:
                raise ValueError
        except Exception:
            days = 3

        ok, msg, to_delete = clean_backup_files(days)

        # 先在文本区域展示清理计划
        append_result(msg)

        if not ok:
            messagebox.showerror(u"错误", msg)
            return

        if not to_delete:
            messagebox.showinfo(u"完成", u"没有符合条件的备份可清理。")
            return

        # 弹窗确认
        if not messagebox.askyesno(
            u"确认删除",
            u"共找到 {} 个符合条件的备份将被删除（最新一份会保留）。\n\n是否继续删除？".format(len(to_delete))
        ):
            return

        # 实际执行删除
        removed = []
        errors = []
        for path in to_delete:
            try:
                os.remove(path)
                removed.append(path)
            except Exception as e:
                errors.append((path, e))

        result_lines = [msg, "", u"实际已删除 {} 个备份。".format(len(removed))]
        if errors:
            result_lines.append(u"以下备份删除失败：")
            for path, err in errors:
                result_lines.append(u"{}    错误: {}".format(path, err))

        final_msg = "\n".join(result_lines)
        append_result(final_msg)

        if errors:
            messagebox.showerror(u"部分失败", final_msg)
        else:
            messagebox.showinfo(u"完成", u"备份清理完成")

    def on_clean_all_clicked():
        ok, msg, to_delete = delete_all_backups()

        # 先在文本区域展示将要删除的所有备份
        append_result(msg)

        if not ok:
            messagebox.showerror(u"错误", msg)
            return

        if not to_delete:
            messagebox.showinfo(u"完成", u"没有任何备份文件。")
            return

        if not messagebox.askyesno(
            u"确认删除所有备份",
            u"共找到 {} 个备份文件，将全部删除（不保留最新一份）。\n\n是否继续删除？".format(len(to_delete))
        ):
            return

        removed = []
        errors = []
        for path in to_delete:
            try:
                os.remove(path)
                removed.append(path)
            except Exception as e:
                errors.append((path, e))

        result_lines = [msg, "", u"实际已删除 {} 个备份。".format(len(removed))]
        if errors:
            result_lines.append(u"以下备份删除失败：")
            for path, err in errors:
                result_lines.append(u"{}    错误: {}".format(path, err))

        final_msg = "\n".join(result_lines)
        append_result(final_msg)

        if errors:
            messagebox.showerror(u"部分失败", final_msg)
        else:
            messagebox.showinfo(u"完成", u"所有备份已删除")

    frame_btn = tk.Frame(root, bg="#dbe2ef")
    frame_btn.pack(fill="x", padx=10, pady=(0, 10))

    # 统一按钮样式
    btn_font = ("Microsoft YaHei", 10, "bold")
    btn_kwargs = {
        "bg": "#112d4e",
        "fg": "white",
        "activebackground": "#112d4e",
        "activeforeground": "white",
        "font": btn_font,
    }

    btn_run = tk.Button(frame_btn, text=u"生成新 ID", command=on_run_clicked, **btn_kwargs)
    btn_run.pack(side="left", padx=(0, 10))

    # 清理备份相关控件
    tk.Label(frame_btn, text=u"保留最近天数:", bg="#dbe2ef").pack(side="left", padx=(5, 0))
    entry_days = tk.Entry(frame_btn, width=5)
    entry_days.insert(0, "3")
    entry_days.pack(side="left", padx=(5, 10))

    btn_clean = tk.Button(frame_btn, text=u"清理备份", command=on_clean_clicked, **btn_kwargs)
    btn_clean.pack(side="left", padx=(0, 10))

    btn_clean_all = tk.Button(frame_btn, text=u"全部删除备份", command=on_clean_all_clicked, **btn_kwargs)
    btn_clean_all.pack(side="left", padx=(0, 0))

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