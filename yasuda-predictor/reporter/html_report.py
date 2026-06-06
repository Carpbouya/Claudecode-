"""HTML レポート生成（Jinja2）+ ターミナルサマリー。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from buyer.ticket_generator import TicketProposal
from config import RaceProfile
from models import RaceData
from reporter.summary import build_summaries

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def render_html(race: RaceData, profile: RaceProfile, proposal: TicketProposal) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")
    return template.render(
        race=race,
        profile=profile,
        proposal=proposal,
        summaries=build_summaries(race, profile, proposal.marks),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


def write_html(race: RaceData, profile: RaceProfile, proposal: TicketProposal,
               output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    html = render_html(race, profile, proposal)
    fname = f"{race.name}_{race.year}.html"
    path = output_dir / fname
    path.write_text(html, encoding="utf-8")
    return path


def terminal_summary(race: RaceData, profile: RaceProfile, proposal: TicketProposal) -> str:
    """ターミナル表示用のテキストサマリーを生成する。"""
    lines: list[str] = []
    lines.append("=" * 56)
    lines.append(f"  {race.name} {race.year}  "
                 f"（{race.course}{race.surface}{race.distance}m / データ:{race.source}）")
    lines.append("=" * 56)

    # スコア上位一覧
    lines.append("")
    lines.append(f"{'印':<2}{'馬番':>3} {'馬名':<16}{'騎手':<8}{'単勝':>6}{'総合':>7}{'勝率':>7}")
    lines.append("-" * 56)
    for h in race.horses:
        lines.append(
            f"{h.mark or '  ':<2}{h.number:>3} {h.name:<16}{h.jockey:<8}"
            f"{h.win_odds:>6.1f}{h.total_score:>7.1f}{h.estimated_win_prob*100:>6.1f}%"
        )

    # 買い目
    lines.append("")
    lines.append("【買い目提案】")
    lines.append(f"馬券種      : {proposal.bet_type}")
    combos = " / ".join("-".join(str(n) for n in c) for c in proposal.combos)
    lines.append(f"買い目      : {combos}")
    lines.append(f"金額配分    : 各{proposal.per_amount:,}円"
                 f"（合計{proposal.total_amount:,}円・{len(proposal.combos)}点）")
    lines.append(f"推定的中配当: 約{proposal.payout_low:,}〜{proposal.payout_high:,}円"
                 f"（推定期待値: {proposal.expected_value}倍）")
    lines.append(f"            → {proposal.rationale}")

    # 根拠
    lines.append("")
    lines.append("【根拠サマリー】")
    for r in build_summaries(race, profile, proposal.marks):
        lines.append(f"{r['mark']} {r['number']}番 {r['name']}（スコア: {r['total']}点）")
        lines.append(f"   → {r['text']}")

    return "\n".join(lines)
