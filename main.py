import argparse
import json
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
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
