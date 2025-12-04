import argparse
import json
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
from typing import Dict, List

DATA_FILE = Path("records.json")


@dataclass
class Record:
    name: str
    amount: float
    category: str
    usage_frequency: str
    usage_minutes: int
    created_at: str


def load_records() -> List[Record]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Record(**item) for item in raw]


def save_records(records: List[Record]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)


def add_record(args: argparse.Namespace) -> None:
    records = load_records()
    new_record = Record(
        name=args.name,
        amount=args.amount,
        category=args.category,
        usage_frequency=args.frequency,
        usage_minutes=args.usage_minutes,
        created_at=args.date or date.today().isoformat(),
    )
    records.append(new_record)
    save_records(records)
    print("已添加记录：")
    print_record(new_record)


def print_record(record: Record) -> None:
    print(
        f"- {record.created_at} | {record.name} | ￥{record.amount:.2f} | "
        f"类别: {record.category} | 频率/时长: {record.usage_frequency} / {record.usage_minutes}分钟"
    )


def list_records(_: argparse.Namespace) -> None:
    records = load_records()
    if not records:
        print("暂无记录，可使用 add 子命令添加。")
        return
    print("所有记录：")
    for record in records:
        print_record(record)


def stats_panel(_: argparse.Namespace) -> None:
    records = load_records()
    if not records:
        print("暂无记录，无法生成统计面板。")
        return

    print("=== 统计面板（类似屏幕使用时间）===")
    summarize_by_frequency(records)
    summarize_by_day(records)


def summarize_by_frequency(records: List[Record]) -> None:
    summary: Dict[str, Dict[str, float]] = {}
    for record in records:
        freq = record.usage_frequency
        if freq not in summary:
            summary[freq] = {"amount": 0.0, "count": 0, "minutes": 0}
        summary[freq]["amount"] += record.amount
        summary[freq]["count"] += 1
        summary[freq]["minutes"] += record.usage_minutes

    print("\n按使用频率/时长统计：")
    for freq, stats in summary.items():
        print(
            f"- {freq}: {stats['count']} 笔 | 总支出 ￥{stats['amount']:.2f} | 总使用 {stats['minutes']} 分钟"
        )


def summarize_by_day(records: List[Record]) -> None:
    today = date.today()
    window = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    per_day: Dict[str, int] = {d.isoformat(): 0 for d in window}

    for record in records:
        created = record.created_at
        if created in per_day:
            per_day[created] += record.usage_minutes

    max_minutes = max(per_day.values()) if per_day else 0
    bar_width = 24

    print("\n近7天使用时间（分钟）柱状图：")
    for day in window:
        minutes = per_day[day.isoformat()]
        bar_length = int((minutes / max_minutes) * bar_width) if max_minutes else 0
        bar = "█" * bar_length
        print(f"{day.isoformat()} | {bar:<{bar_width}} {minutes:>4} 分钟")


def launch_ui(_: argparse.Namespace) -> None:
    records = load_records()

    def refresh_tree() -> None:
        for row in tree.get_children():
            tree.delete(row)
        for idx, record in enumerate(records):
            tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    record.created_at,
                    record.name,
                    f"￥{record.amount:.2f}",
                    record.category,
                    record.usage_frequency,
                    f"{record.usage_minutes} 分钟",
                ),
            )
        stats_text.set(build_summary_text(records))

    def submit_record() -> None:
        name = name_var.get().strip()
        amount_raw = amount_var.get().strip()
        category = category_var.get().strip()
        frequency = frequency_var.get().strip() or "未填写"
        minutes_raw = minutes_var.get().strip()
        created_at = date_var.get().strip() or date.today().isoformat()

        if not name or not amount_raw or not category or not minutes_raw:
            messagebox.showwarning("提示", "请完整填写必填项（名称、金额、类别、时长）。")
            return

        try:
            amount_value = float(amount_raw)
            minutes_value = int(minutes_raw)
        except ValueError:
            messagebox.showerror("错误", "金额需为数字，时长需为整数。")
            return

        new_record = Record(
            name=name,
            amount=amount_value,
            category=category,
            usage_frequency=frequency,
            usage_minutes=minutes_value,
            created_at=created_at,
        )
        records.append(new_record)
        save_records(records)
        refresh_tree()
        name_var.set("")
        amount_var.set("")
        category_var.set("")
        frequency_var.set("")
        minutes_var.set("")
        date_var.set("")
        messagebox.showinfo("成功", "记录已保存并更新列表。")

    root = tk.Tk()
    root.title("小钱宝 - 记账 UI")
    root.geometry("760x520")

    content = ttk.Frame(root, padding=12)
    content.pack(fill=tk.BOTH, expand=True)

    list_frame = ttk.Labelframe(content, text="记录列表", padding=10)
    list_frame.pack(fill=tk.BOTH, expand=True)

    columns = ("日期", "名称", "金额", "类别", "频率", "使用时长")
    tree = ttk.Treeview(list_frame, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor=tk.W, width=110)
    tree.pack(fill=tk.BOTH, expand=True)

    stats_text = tk.StringVar(value=build_summary_text(records))
    stats_label = ttk.Label(list_frame, textvariable=stats_text, padding=(0, 8, 0, 0))
    stats_label.pack(fill=tk.X)

    form = ttk.Labelframe(content, text="新增记录", padding=10)
    form.pack(fill=tk.X, pady=(10, 0))

    name_var = tk.StringVar()
    amount_var = tk.StringVar()
    category_var = tk.StringVar()
    frequency_var = tk.StringVar()
    minutes_var = tk.StringVar()
    date_var = tk.StringVar(value=date.today().isoformat())

    ttk.Label(form, text="名称*").grid(row=0, column=0, sticky=tk.W, pady=2)
    ttk.Entry(form, textvariable=name_var, width=20).grid(row=0, column=1, sticky=tk.W)

    ttk.Label(form, text="金额*￥").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
    ttk.Entry(form, textvariable=amount_var, width=12).grid(row=0, column=3, sticky=tk.W)

    ttk.Label(form, text="类别*").grid(row=1, column=0, sticky=tk.W, pady=2)
    ttk.Entry(form, textvariable=category_var, width=20).grid(row=1, column=1, sticky=tk.W)

    ttk.Label(form, text="使用频率").grid(row=1, column=2, sticky=tk.W, padx=(10, 0))
    ttk.Combobox(
        form,
        textvariable=frequency_var,
        values=["每天", "每周", "偶尔", "一次性"],
        width=10,
    ).grid(row=1, column=3, sticky=tk.W)

    ttk.Label(form, text="使用时长*（分钟）").grid(row=2, column=0, sticky=tk.W, pady=2)
    ttk.Entry(form, textvariable=minutes_var, width=12).grid(row=2, column=1, sticky=tk.W)

    ttk.Label(form, text="日期 (YYYY-MM-DD)").grid(row=2, column=2, sticky=tk.W, padx=(10, 0))
    ttk.Entry(form, textvariable=date_var, width=12).grid(row=2, column=3, sticky=tk.W)

    ttk.Button(form, text="保存记录", command=submit_record).grid(
        row=3, column=0, columnspan=4, sticky=tk.EW, pady=(8, 0)
    )

    for child in form.winfo_children():
        child.grid_configure(padx=4, pady=2)

    refresh_tree()
    root.mainloop()


def build_summary_text(records: List[Record]) -> str:
    if not records:
        return "暂无记录，添加后可自动汇总。"
    total_amount = sum(r.amount for r in records)
    total_minutes = sum(r.usage_minutes for r in records)
    return f"共 {len(records)} 条记录 | 总支出 ￥{total_amount:.2f} | 总使用 {total_minutes} 分钟"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="简易记账应用，支持频率/使用时间统计。")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="添加一笔记录")
    add_parser.add_argument("name", help="项目名称")
    add_parser.add_argument("amount", type=float, help="金额")
    add_parser.add_argument("category", help="类别，如餐饮、交通")
    add_parser.add_argument("frequency", help="使用频率，如每天、每周、偶尔")
    add_parser.add_argument(
        "usage_minutes",
        type=int,
        help="本次使用时长（分钟），类似屏幕使用时间记录",
    )
    add_parser.add_argument(
        "--date",
        help="记录日期，ISO格式(YYYY-MM-DD)，默认为今天",
    )
    add_parser.set_defaults(func=add_record)

    list_parser = subparsers.add_parser("list", help="查看所有记录")
    list_parser.set_defaults(func=list_records)

    stats_parser = subparsers.add_parser("stats", help="查看统计面板")
    stats_parser.set_defaults(func=stats_panel)

    ui_parser = subparsers.add_parser("ui", help="启动图形界面")
    ui_parser.set_defaults(func=launch_ui)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
