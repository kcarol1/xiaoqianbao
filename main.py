import argparse
import json
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

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


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()


def month_boundaries(today: date) -> Tuple[date, date]:
    start = date(today.year, today.month, 1)
    if today.month == 12:
        end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(today.year, today.month + 1, 1) - timedelta(days=1)
    return start, end


def build_dashboard(records: List[Record]) -> Dict[str, object]:
    today = date.today()
    start_of_month, end_of_month = month_boundaries(today)

    month_records = [
        r
        for r in records
        if start_of_month <= parse_iso_date(r.created_at) <= end_of_month
    ]
    month_minutes = sum(r.usage_minutes for r in month_records)
    month_amount = sum(r.amount for r in month_records)
    total_minutes = sum(r.usage_minutes for r in records)
    total_amount = sum(r.amount for r in records)

    elapsed_days = max((today - start_of_month).days + 1, 1)
    average_per_day = month_minutes / elapsed_days if month_minutes else 0
    progress = min(int((month_minutes / 60) * 100), 100) if month_minutes else 0

    usage_by_project: Dict[str, int] = {}
    for record in records:
        usage_by_project[record.name] = (
            usage_by_project.get(record.name, 0) + record.usage_minutes
        )

    sorted_usage = sorted(usage_by_project.items(), key=lambda item: item[1], reverse=True)
    chart_labels = [item[0] for item in sorted_usage]
    chart_minutes = [item[1] for item in sorted_usage]

    indexed_records = list(enumerate(records))
    sorted_records = sorted(
        indexed_records, key=lambda pair: parse_iso_date(pair[1].created_at), reverse=True
    )
    recent_records = sorted_records[:5]

    return {
        "today": today,
        "start_of_month": start_of_month,
        "end_of_month": end_of_month,
        "month_minutes": month_minutes,
        "month_amount": month_amount,
        "total_minutes": total_minutes,
        "total_amount": total_amount,
        "average_per_day": average_per_day,
        "progress": progress,
        "recent_records": recent_records,
        "chart_labels": chart_labels,
        "chart_minutes": chart_minutes,
    }


def create_app():
    from flask import Flask, flash, redirect, render_template_string, request, url_for

    app = Flask(__name__)
    app.secret_key = "xiaoqianbao-demo-key"

    TEMPLATE = """
    <!doctype html>
    <html lang=\"zh-CN\">
      <head>
        <meta charset=\"utf-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
        <title>消费时长 - 小钱宝</title>
        <style>
          :root {
            --bg: #f3f5ff;
            --card: #ffffff;
            --primary: #5c6bfe;
            --text: #1f2940;
            --muted: #6c7693;
            --border: #e0e4f5;
          }
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: 'Inter', 'PingFang SC', system-ui, -apple-system, sans-serif;
            background: linear-gradient(180deg, #f2f3ff 0%, #f9faff 100%);
            color: var(--text);
          }
          .page { max-width: 1024px; margin: 0 auto; padding: 32px 16px 64px; }
          header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
          .title { font-weight: 700; font-size: 20px; }
          .subtitle { color: var(--muted); font-size: 14px; }
          .card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; box-shadow: 0 10px 40px rgba(92,107,254,0.12); padding: 24px; }
          .stack { display: grid; gap: 16px; margin-bottom: 16px; }
          .row { display: flex; gap: 12px; align-items: center; justify-content: space-between; }
          .meta { display: flex; flex-direction: column; gap: 4px; }
          .muted { color: var(--muted); font-size: 13px; }
          .value { font-size: 24px; font-weight: 700; }
          .pill { padding: 6px 10px; background: #eff1ff; color: var(--primary); border-radius: 10px; font-size: 12px; font-weight: 600; }
          .progress { position: relative; height: 18px; background: #edf0ff; border-radius: 10px; overflow: hidden; }
          .progress span { display: block; height: 100%; background: linear-gradient(90deg, #5c6bfe, #8191ff); width: {{ progress }}%; }
          .section-title { font-weight: 700; margin: 4px 0 8px; }
          form { display: grid; gap: 12px; margin-top: 8px; }
          label { font-size: 13px; color: var(--muted); margin-bottom: 4px; display: block; }
          input, select, textarea { width: 100%; border-radius: 12px; border: 1px solid var(--border); padding: 12px 14px; font-size: 14px; background: #f9faff; outline: none; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
          input:focus, select:focus, textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(92,107,254,0.15); }
          textarea { min-height: 72px; resize: vertical; }
          .chips { display: flex; gap: 8px; flex-wrap: wrap; }
          .chip { background: #eef2ff; color: #4b5be5; border-radius: 12px; padding: 8px 12px; font-size: 13px; border: none; cursor: pointer; transition: transform 0.1s ease, box-shadow 0.2s ease; }
          .chip:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(75,91,229,0.15); }
          button.submit { width: 100%; border: none; background: linear-gradient(90deg, #5c6bfe, #8191ff); color: #fff; font-weight: 700; padding: 14px; border-radius: 14px; cursor: pointer; font-size: 16px; box-shadow: 0 10px 25px rgba(92,107,254,0.35); transition: transform 0.1s ease, box-shadow 0.2s ease; }
          button.submit:hover { transform: translateY(-1px); box-shadow: 0 14px 28px rgba(92,107,254,0.45); }
          .divider { border: none; border-top: 1px dashed var(--border); margin: 12px 0; }
          .empty { text-align: center; color: var(--muted); padding: 16px 0 4px; font-size: 13px; }
          .flash { background: #f1f5ff; border: 1px solid #dbe3ff; padding: 10px 12px; border-radius: 10px; color: #3d4fb2; margin-bottom: 8px; }
          .recent { display: grid; gap: 10px; }
          .recent-item { display: flex; justify-content: space-between; align-items: center; background: #f7f8ff; border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; }
          .recent-main { display: flex; gap: 10px; align-items: center; }
          .circle { width: 10px; height: 10px; border-radius: 50%; background: #5c6bfe; }
          .footer { text-align: center; margin-top: 16px; color: var(--muted); font-size: 12px; }
          .chart-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
          .chart-card { background: #f7f8ff; border: 1px solid var(--border); border-radius: 12px; padding: 12px; }
          canvas { width: 100% !important; height: 260px !important; }
        </style>
      </head>
      <body>
        <div class=\"page\">
          <header>
            <div>
              <div class=\"title\">消费时长</div>
              <div class=\"subtitle\">{{ today.strftime('%m月%d日 %A') }}</div>
            </div>
            <a href=\"#add\" style=\"color: var(--primary); font-weight: 600; text-decoration: none;\">查看统计</a>
          </header>

          <section class=\"card stack\">
            <div class=\"row\">
              <div class=\"meta\">
                <div class=\"muted\">本周屏幕使用</div>
                <div class=\"value\">{{ month_minutes }} 分钟</div>
              </div>
              <div class=\"meta\" style=\"text-align:right;\">
                <div class=\"value\">￥{{ '%.2f' % month_amount }}</div>
                <div class=\"muted\">总支出</div>
              </div>
            </div>
            <div class=\"row\">
              <div class=\"meta\">
                <div class=\"muted\">按周设置</div>
                <div class=\"value\">{{ average_per_day|round(1) if average_per_day else 0 }} 分钟/天</div>
              </div>
              <div class=\"meta\" style=\"text-align:right;\">
                <div class=\"value\">￥{{ '%.2f' % total_amount }}</div>
                <div class=\"muted\">总支出</div>
              </div>
            </div>
            <div>
              <div class=\"muted\">每日目标 60 分钟</div>
              <div class=\"progress\"><span></span></div>
              <div class=\"muted\" style=\"margin-top:6px;\">当前进度 {{ progress }}%</div>
            </div>
          </section>

          <section class=\"card stack\" id=\"add\">
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                {% for msg in messages %}
                  <div class=\"flash\">{{ msg }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}
            <div class=\"section-title\">记一笔</div>
            <form method=\"post\" action=\"{{ url_for('add_record') }}\">
              <div>
                <label for=\"name\">记录名称</label>
                <textarea id=\"name\" name=\"name\" placeholder=\"例如：健身环、Netflix会员\" required></textarea>
              </div>
              <div class=\"chips\">
                {% for option in ['电影', '习惯养成', '运动健身', '会员订阅', '社交娱乐', '阅读学习'] %}
                  <button class=\"chip\" type=\"button\" onclick=\"document.getElementById('name').value=this.innerText;\">{{ option }}</button>
                {% endfor %}
              </div>
              <div class=\"row\">
                <div style=\"flex:1;\">
                  <label for=\"category\">使用类别</label>
                  <select id=\"category\" name=\"category\" required>
                    {% for option in ['健身', '娱乐', '学习', '订阅', '社交'] %}
                      <option value=\"{{ option }}\">{{ option }}</option>
                    {% endfor %}
                  </select>
                </div>
                <div style=\"flex:1;\">
                  <label for=\"frequency\">使用频率</label>
                  <select id=\"frequency\" name=\"frequency\">\n                    <option value=\"每周1天\">每周1天</option>
                    <option value=\"每周2天\">每周2天</option>
                    <option value=\"每天\">每天</option>
                    <option value=\"偶尔\">偶尔</option>
                  </select>
                </div>
              </div>
              <div class=\"row\">
                <div style=\"flex:1;\">
                  <label for=\"minutes\">时长 (分钟)</label>
                  <input id=\"minutes\" name=\"usage_minutes\" type=\"number\" min=\"0\" placeholder=\"60\" required>
                </div>
                <div style=\"flex:1;\">
                  <label for=\"amount\">金额 (¥)</label>
                  <input id=\"amount\" name=\"amount\" type=\"number\" step=\"0.01\" min=\"0\" placeholder=\"50\" required>
                </div>
                <div style=\"flex:1;\">
                  <label for=\"created_at\">日期</label>
                  <input id=\"created_at\" name=\"created_at\" type=\"date\" value=\"{{ today.isoformat() }}\">
                </div>
              </div>
              <button class=\"submit\" type=\"submit\">添加记录</button>
            </form>
          </section>

          <section class=\"card stack\">
            <div class=\"section-title\">最近记录</div>
            {% if recent_records %}
              <div class=\"recent\">
                {% for record_id, item in recent_records %}
                  <div class=\"recent-item\">
                    <div class=\"recent-main\">
                      <span class=\"circle\"></span>
                      <div>
                        <div style=\"font-weight:600;\">{{ item.name }}</div>
                        <div class=\"muted\">{{ item.created_at }} · {{ item.category }} · {{ item.usage_frequency }}</div>
                        <form method=\"post\" action=\"{{ url_for('update_record', record_id=record_id) }}\" style=\"display:grid;gap:6px;margin-top:8px;grid-template-columns:1fr 1fr auto;align-items:center;\">
                          <select name=\"frequency\" style=\"padding:6px 10px;border-radius:10px;border:1px solid var(--border);background:#f9faff;\">
                            {% for option in ['每周1天', '每周2天', '每天', '偶尔'] %}
                              <option value=\"{{ option }}\" {% if option == item.usage_frequency %}selected{% endif %}>{{ option }}</option>
                            {% endfor %}
                          </select>
                          <input type=\"number\" name=\"usage_minutes\" value=\"{{ item.usage_minutes }}\" min=\"0\" style=\"padding:6px 10px;border-radius:10px;border:1px solid var(--border);background:#f9faff;\" required>
                          <button type=\"submit\" class=\"chip\" style=\"margin:0;\">更新</button>
                        </form>
                      </div>
                    </div>
                    <div style=\"text-align:right;\">
                      <div style=\"font-weight:700;\">{{ item.usage_minutes }} 分钟</div>
                      <div class=\"muted\">¥{{ '%.2f' % item.amount }}</div>
                    </div>
                  </div>
                {% endfor %}
              </div>
            {% else %}
              <div class=\"empty\">还没有记录，试着记一笔消费记录吧。</div>
            {% endif %}
          </section>

          <section class=\"card stack\">
            <div class=\"section-title\">项目使用时长</div>
            {% if chart_labels %}
              <div class=\"chart-grid\">
                <div class=\"chart-card\">
                  <div class=\"muted\" style=\"margin-bottom:8px;\">按项目的使用时长（分钟）</div>
                  <canvas id=\"barChart\"></canvas>
                </div>
                <div class=\"chart-card\">
                  <div class=\"muted\" style=\"margin-bottom:8px;\">项目占比</div>
                  <canvas id=\"pieChart\"></canvas>
                </div>
              </div>
            {% else %}
              <div class=\"empty\">暂无数据，添加记录后可查看柱状图和饼图。</div>
            {% endif %}
          </section>

          <div class=\"footer\">本月 {{ start_of_month.strftime('%m/%d') }} - {{ end_of_month.strftime('%m/%d') }} · 共 {{ month_minutes }} 分钟 · 总支出 ¥{{ '%.2f' % total_amount }}</div>
        </div>
        <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
        <script>
          const labels = {{ chart_labels | tojson }};
          const minutes = {{ chart_minutes | tojson }};

          function withAlpha(hex, alpha) {
            const bigint = parseInt(hex.replace('#', ''), 16);
            const r = (bigint >> 16) & 255;
            const g = (bigint >> 8) & 255;
            const b = bigint & 255;
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
          }

          if (labels.length) {
            const palette = ['#5c6bfe', '#7b8cff', '#a2b1ff', '#c6d0ff', '#8996ff', '#3f4de3'];
            const barCtx = document.getElementById('barChart');
            new Chart(barCtx, {
              type: 'bar',
              data: {
                labels,
                datasets: [{
                  label: '分钟',
                  data: minutes,
                  backgroundColor: labels.map((_, i) => withAlpha(palette[i % palette.length], 0.8)),
                  borderRadius: 8,
                }],
              },
              options: {
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 30 } } },
              },
            });

            const pieCtx = document.getElementById('pieChart');
            new Chart(pieCtx, {
              type: 'pie',
              data: {
                labels,
                datasets: [{
                  data: minutes,
                  backgroundColor: labels.map((_, i) => withAlpha(palette[i % palette.length], 0.85)),
                  borderColor: '#fff',
                  borderWidth: 2,
                }],
              },
              options: {
                plugins: { legend: { position: 'bottom' } },
              },
            });
          }
        </script>
      </body>
    </html>
    """

    @app.route("/", methods=["GET"])
    def index():
        records = load_records()
        dashboard = build_dashboard(records)
        return render_template_string(TEMPLATE, **dashboard)

    @app.route("/records", methods=["POST"], endpoint="add_record")
    def add_record_route():
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip() or "未分类"
        frequency = request.form.get("frequency", "").strip() or "未填写"
        minutes_raw = request.form.get("usage_minutes", "").strip()
        amount_raw = request.form.get("amount", "").strip()
        created_at = request.form.get("created_at") or date.today().isoformat()

        if not name or not minutes_raw or not amount_raw:
            flash("请填写名称、时长和金额。")
            return redirect(url_for("index"))

        try:
            minutes_value = int(minutes_raw)
            amount_value = float(amount_raw)
        except ValueError:
            flash("金额需为数字，时长需为整数。")
            return redirect(url_for("index"))

        new_record = Record(
            name=name,
            amount=amount_value,
            category=category,
            usage_frequency=frequency,
            usage_minutes=minutes_value,
            created_at=created_at,
        )

        records = load_records()
        records.append(new_record)
        save_records(records)
        flash("记录已保存！")
        return redirect(url_for("index"))

    @app.route("/records/<int:record_id>", methods=["POST"], endpoint="update_record")
    def update_record_route(record_id: int):
        records = load_records()
        if record_id < 0 or record_id >= len(records):
            flash("未找到要更新的记录。")
            return redirect(url_for("index"))

        frequency = request.form.get("frequency", "").strip() or records[record_id].usage_frequency
        minutes_raw = request.form.get("usage_minutes", "").strip()

        try:
            minutes_value = int(minutes_raw)
        except ValueError:
            flash("时长需为整数。")
            return redirect(url_for("index"))

        records[record_id].usage_frequency = frequency
        records[record_id].usage_minutes = minutes_value
        save_records(records)
        flash("使用时间和频率已更新！")
        return redirect(url_for("index"))

    return app


def run_web(args: argparse.Namespace) -> None:
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="简易记账应用，支持频率/使用时间统计与 Web 看板。")
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

    web_parser = subparsers.add_parser("web", help="启动 Web 应用")
    web_parser.add_argument("--host", default="0.0.0.0", help="监听地址，默认 0.0.0.0")
    web_parser.add_argument("--port", type=int, default=5000, help="端口，默认 5000")
    web_parser.add_argument("--debug", action="store_true", help="启用 Flask 调试模式")
    web_parser.set_defaults(func=run_web)

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
