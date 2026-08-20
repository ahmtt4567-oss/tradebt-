import json
from pathlib import Path

BASELINE_PATH = Path("data/short_filter_benchmark/baseline.json")
FILTERED_PATH = Path("data/short_filter_benchmark/filtered.json")
THRESHOLDS = (60, 65, 70, 75, 80, 85, 90)
SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")


def load_trades(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        {**trade, "coin": item["symbol"]}
        for item in payload["symbols"]
        for trade in item["response"]["trade_log"]
    ]


def net_pnl(trade: dict) -> float:
    return float(trade.get("net_pnl") or 0.0)


def gross_pnl(trade: dict) -> float:
    return float(trade.get("gross_pnl") or 0.0)


def metrics(trades: list[dict]) -> dict:
    ordered = sorted(trades, key=lambda item: item.get("entry_time") or 0)
    wins = sum(net_pnl(item) > 0 for item in ordered)
    gross_profit = sum(gross_pnl(item) for item in ordered if gross_pnl(item) > 0)
    gross_loss = abs(sum(gross_pnl(item) for item in ordered if gross_pnl(item) < 0))
    equity = peak = 10_000.0
    max_drawdown = 0.0
    for item in ordered:
        equity += net_pnl(item)
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
        "net_pnl": sum(net_pnl(item) for item in ordered),
        "max_drawdown": max_drawdown,
    }


def threshold_trades(baseline: list[dict], threshold: int) -> list[dict]:
    return [
        trade for trade in baseline
        if trade.get("direction") == "LONG"
        or float(trade.get("mtf_alignment") or 0) < threshold
    ]


def format_metric(value: float) -> str:
    return f"{value:.2f}"


def main() -> None:
    baseline = sorted(load_trades(BASELINE_PATH), key=lambda item: item.get("entry_time") or 0)
    saved_filtered = sorted(load_trades(FILTERED_PATH), key=lambda item: item.get("entry_time") or 0)
    common_start = max(baseline[0]["entry_time"], saved_filtered[0]["entry_time"])
    common_end = min(baseline[-1]["entry_time"], saved_filtered[-1]["entry_time"])
    common_baseline = [item for item in baseline if common_start <= item["entry_time"] <= common_end]
    baseline_result = metrics(common_baseline)

    span = common_end - common_start
    test_span = span * 0.25
    step = span * 0.10
    window_starts = []
    cursor = common_start + span * 0.50
    while cursor + test_span <= common_end + 1:
        window_starts.append((cursor, cursor + test_span))
        cursor += step

    results = {}
    print(f"DATA|baseline_trades={len(baseline)}|saved_filtered_trades={len(saved_filtered)}|common_start={common_start}|common_end={common_end}|windows={len(window_starts)}")
    print("BASELINE")
    print(baseline_result)

    print("THRESHOLD SUMMARY")
    for threshold in THRESHOLDS:
        filtered = threshold_trades(common_baseline, threshold)
        result = metrics(filtered)
        better_windows = 0
        window_rows = []
        for index, (start, end) in enumerate(window_starts, start=1):
            baseline_window = [item for item in common_baseline if start <= item["entry_time"] <= end]
            filtered_window = [item for item in filtered if start <= item["entry_time"] <= end]
            base_metrics = metrics(baseline_window)
            filtered_metrics = metrics(filtered_window)
            better = (
                filtered_metrics["profit_factor"] > base_metrics["profit_factor"]
                and filtered_metrics["net_pnl"] > base_metrics["net_pnl"]
                and filtered_metrics["max_drawdown"] > base_metrics["max_drawdown"]
            )
            better_windows += int(better)
            window_rows.append((index, start, end, base_metrics, filtered_metrics, better))
        eliminated = [
            item for item in common_baseline
            if item.get("direction") == "SHORT"
            and float(item.get("mtf_alignment") or 0) >= threshold
        ]
        result = {
            **result,
            "threshold": threshold,
            "net_delta": result["net_pnl"] - baseline_result["net_pnl"],
            "pf_delta": result["profit_factor"] - baseline_result["profit_factor"],
            "dd_improvement": result["max_drawdown"] - baseline_result["max_drawdown"],
            "better_windows": better_windows,
            "total_windows": len(window_starts),
            "eliminated_short": len(eliminated),
            "eliminated_short_pnl": sum(net_pnl(item) for item in eliminated),
            "windows": window_rows,
            "coin_breakdown": {},
        }
        for symbol in SYMBOLS:
            coin_base = metrics([item for item in common_baseline if item["coin"] == symbol])
            coin_filtered = metrics([item for item in filtered if item["coin"] == symbol])
            result["coin_breakdown"][symbol] = {
                "baseline": coin_base,
                "filtered": coin_filtered,
                "delta": coin_filtered["net_pnl"] - coin_base["net_pnl"],
            }
        results[threshold] = result
        print(
            f"{threshold}|trades={result['trades']}|W/L={result['wins']}/{result['losses']}|"
            f"WR={result['win_rate']:.2f}|PF={result['profit_factor']:.2f}|"
            f"NET={result['net_pnl']:.2f}|DD={result['max_drawdown']:.2f}|"
            f"PNL_DELTA={result['net_delta']:.2f}|PF_DELTA={result['pf_delta']:.2f}|"
            f"DD_IMPROVEMENT={result['dd_improvement']:.2f}|"
            f"BETTER={better_windows}/{len(window_starts)}|"
            f"ELIMINATED_SHORT={result['eliminated_short']}|"
            f"ELIMINATED_SHORT_PNL={result['eliminated_short_pnl']:.2f}"
        )

    print("WINDOWS")
    for threshold, result in results.items():
        print(f"threshold={threshold}")
        for index, start, end, base_metrics, filtered_metrics, better in result["windows"]:
            print(
                f"window={index}|start={int(start)}|end={int(end)}|"
                f"baseline_trades={base_metrics['trades']}|filtered_trades={filtered_metrics['trades']}|"
                f"baseline_net={base_metrics['net_pnl']:.2f}|filtered_net={filtered_metrics['net_pnl']:.2f}|"
                f"baseline_pf={base_metrics['profit_factor']:.2f}|filtered_pf={filtered_metrics['profit_factor']:.2f}|"
                f"baseline_dd={base_metrics['max_drawdown']:.2f}|filtered_dd={filtered_metrics['max_drawdown']:.2f}|"
                f"same_bounds=True|better={better}"
            )

    print("75_80_85")
    for threshold in (75, 80, 85):
        result = results[threshold]
        print(
            f"{threshold}|trades={result['trades']}|PF={result['profit_factor']:.2f}|"
            f"NET={result['net_pnl']:.2f}|DD={result['max_drawdown']:.2f}|"
            f"BETTER={result['better_windows']}/{result['total_windows']}|"
            f"ELIMINATED_SHORT={result['eliminated_short']}"
        )

    ranked = sorted(
        results.values(),
        key=lambda item: (
            item["better_windows"],
            item["profit_factor"],
            item["net_pnl"],
            item["max_drawdown"],
            item["trades"],
        ),
        reverse=True,
    )
    print(f"BEST_THRESHOLD_CANDIDATE=DATA-BASED CANDIDATE {ranked[0]['threshold']}")
    print(f"SECOND_BEST=DATA-BASED CANDIDATE {ranked[1]['threshold']}")
    print(f"THIRD_BEST=DATA-BASED CANDIDATE {ranked[2]['threshold']}")
    print("No threshold is a production recommendation.")


if __name__ == "__main__":
    main()
