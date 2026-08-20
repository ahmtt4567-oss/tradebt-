import json
from pathlib import Path

BASE = Path("data/short_filter_benchmark/baseline.json")
FILTERED = Path("data/short_filter_benchmark/filtered.json")


def load(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [dict(trade, coin=item["symbol"]) for item in payload["symbols"] for trade in item["response"]["trade_log"]]


def pnl(trade: dict) -> float:
    return float(trade.get("net_pnl") or 0.0)


def gross(trade: dict) -> float:
    return float(trade.get("gross_pnl") or 0.0)


def metrics(trades: list[dict]) -> dict:
    ordered = sorted(trades, key=lambda item: item.get("entry_time") or 0)
    wins = sum(pnl(item) > 0 for item in ordered)
    gross_profit = sum(gross(item) for item in ordered if gross(item) > 0)
    gross_loss = abs(sum(gross(item) for item in ordered if gross(item) < 0))
    equity = peak = 10_000.0
    max_drawdown = 0.0
    for item in ordered:
        equity += pnl(item)
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, (equity / peak - 1) * 100)
    return {
        "trades": len(ordered),
        "wins": wins,
        "losses": len(ordered) - wins,
        "win_rate": wins / len(ordered) * 100 if ordered else 0.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": gross_profit / gross_loss if gross_loss else 0.0,
        "fees": sum(float(item.get("fee") or 0) for item in ordered),
        "net_pnl": sum(pnl(item) for item in ordered),
        "max_drawdown": max_drawdown,
    }


def show(label: str, result: dict) -> None:
    print(
        f"{label}|trades={result['trades']}|W/L={result['wins']}/{result['losses']}|"
        f"WR={result['win_rate']:.2f}|PF={result['profit_factor']:.2f}|"
        f"fees={result['fees']:.2f}|net={result['net_pnl']:.2f}|DD={result['max_drawdown']:.2f}"
    )


def filtered(trades: list[dict]) -> list[dict]:
    return [
        trade for trade in trades
        if trade.get("direction") == "LONG"
        or float(trade.get("mtf_alignment") or 0) < 80
    ]


def main() -> None:
    baseline = sorted(load(BASE), key=lambda item: item.get("entry_time") or 0)
    filtered_trades = sorted(load(FILTERED), key=lambda item: item.get("entry_time") or 0)
    common_start = max(baseline[0]["entry_time"], filtered_trades[0]["entry_time"])
    common_end = min(baseline[-1]["entry_time"], filtered_trades[-1]["entry_time"])
    baseline_common = [item for item in baseline if common_start <= item["entry_time"] <= common_end]
    filtered_common = [item for item in filtered_trades if common_start <= item["entry_time"] <= common_end]

    assert not [
        item for item in filtered_common
        if item.get("direction") == "SHORT" and float(item.get("mtf_alignment") or 0) >= 80
    ]
    baseline_high_alignment = [
        item for item in baseline_common
        if item.get("direction") == "SHORT" and float(item.get("mtf_alignment") or 0) >= 80
    ]

    print("BASELINE")
    show("common", metrics(baseline_common))
    print("FILTERED")
    show("common", metrics(filtered_common))
    print(f"common_start={common_start}|common_end={common_end}")

    span = common_end - common_start
    test_span = span * 0.25
    step = span * 0.10
    cursor = common_start + span * 0.50
    better_windows = 0
    window_count = 0
    while cursor + test_span <= common_end + 1:
        window_count += 1
        test_start = cursor
        test_end = cursor + test_span
        baseline_window = [item for item in baseline_common if test_start <= item["entry_time"] <= test_end]
        filtered_window = [item for item in filtered_common if test_start <= item["entry_time"] <= test_end]
        baseline_result = metrics(baseline_window)
        filtered_result = metrics(filtered_window)
        better = (
            filtered_result["profit_factor"] > baseline_result["profit_factor"]
            and filtered_result["net_pnl"] > baseline_result["net_pnl"]
            and filtered_result["max_drawdown"] > baseline_result["max_drawdown"]
        )
        better_windows += int(better)
        print(
            f"window={window_count}|start={int(test_start)}|end={int(test_end)}|"
            f"baseline_trades={baseline_result['trades']}|filtered_trades={filtered_result['trades']}|"
            f"baseline_net={baseline_result['net_pnl']:.2f}|filtered_net={filtered_result['net_pnl']:.2f}|"
            f"baseline_pf={baseline_result['profit_factor']:.2f}|filtered_pf={filtered_result['profit_factor']:.2f}|"
            f"baseline_dd={baseline_result['max_drawdown']:.2f}|filtered_dd={filtered_result['max_drawdown']:.2f}|"
            f"same_bounds=True|better={better}"
        )
        cursor += step

    short_baseline = [item for item in baseline_common if item.get("direction") == "SHORT"]
    short_low = [item for item in short_baseline if float(item.get("mtf_alignment") or 0) < 80]
    short_high = [item for item in short_baseline if float(item.get("mtf_alignment") or 0) >= 80]
    print("ROLLING WINDOWS")
    print(f"count={window_count}|better={better_windows}/{window_count}|same_bounds=True")
    print("SHORT IMPACT")
    show("short_baseline", metrics(short_baseline))
    show("short_alignment_lt80", metrics(short_low))
    show("short_alignment_ge80", metrics(short_high))
    print(f"baseline_high_alignment_short_count={len(baseline_high_alignment)}|blocked_short_net={sum(pnl(item) for item in short_high):.2f}")
    print("COIN IMPACT")
    for coin in sorted({item["coin"] for item in baseline_common}):
        coin_baseline = metrics([item for item in baseline_common if item["coin"] == coin])
        coin_filtered = metrics([item for item in filtered_common if item["coin"] == coin])
        print(
            f"{coin}|baseline_net={coin_baseline['net_pnl']:.2f}|baseline_pf={coin_baseline['profit_factor']:.2f}|"
            f"filtered_net={coin_filtered['net_pnl']:.2f}|filtered_pf={coin_filtered['profit_factor']:.2f}|"
            f"delta={coin_filtered['net_pnl'] - coin_baseline['net_pnl']:.2f}"
        )
    baseline_result = metrics(baseline_common)
    filtered_result = metrics(filtered_common)
    print("FILTER DELTA")
    print(
        f"net_delta={filtered_result['net_pnl'] - baseline_result['net_pnl']:.2f}|"
        f"pf_delta={filtered_result['profit_factor'] - baseline_result['profit_factor']:.2f}|"
        f"dd_delta={filtered_result['max_drawdown'] - baseline_result['max_drawdown']:.2f}"
    )
    print("VERDICT")
    print("POSITIVE" if better_windows >= 2 and filtered_result["net_pnl"] > baseline_result["net_pnl"] else "INCONCLUSIVE")


if __name__ == "__main__":
    main()
