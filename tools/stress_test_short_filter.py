import json
import random
from pathlib import Path

DATASET = Path("data/short_filter_benchmark/baseline.json")
THRESHOLDS = (75, 80, 85)
SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
PERMUTATIONS = 1000
SEED = 80


def load_trades() -> list[dict]:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    return [
        {**trade, "coin": item["symbol"]}
        for item in payload["symbols"]
        for trade in item["response"]["trade_log"]
    ]


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
        "net_pnl": sum(pnl(item) for item in ordered),
        "max_drawdown": max_drawdown,
    }


def select(trades: list[dict], threshold: int) -> list[dict]:
    return [
        trade for trade in trades
        if trade.get("direction") == "LONG"
        or float(trade.get("mtf_alignment") or 0) < threshold
    ]


def better(filtered: dict, baseline: dict) -> bool:
    return (
        filtered["profit_factor"] > baseline["profit_factor"]
        and filtered["net_pnl"] > baseline["net_pnl"]
        and filtered["max_drawdown"] > baseline["max_drawdown"]
    )


def permutation_metrics(trades: list[dict], rng: random.Random) -> list[dict]:
    values = [pnl(trade) for trade in trades]
    results = []
    for _ in range(PERMUTATIONS):
        rng.shuffle(values)
        equity = peak = 10_000.0
        max_drawdown = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            max_drawdown = min(max_drawdown, (equity / peak - 1) * 100)
        result = metrics(trades)
        result["permutation_net"] = equity - 10_000.0
        result["permutation_dd"] = max_drawdown
        results.append(result)
    return results


def score(result: dict, baseline: dict, time_count: int) -> float:
    window_score = result["better_time_segments"] / max(time_count, 1) * 25
    coin_score = result["better_coins"] / len(SYMBOLS) * 20
    pf_score = min(20.0, max(0.0, result["profit_factor"] / max(baseline["profit_factor"], 0.01) * 10))
    net_score = 15.0 if result["net_pnl"] > baseline["net_pnl"] else 0.0
    dd_score = 10.0 if result["max_drawdown"] > baseline["max_drawdown"] else 0.0
    sample_score = min(10.0, result["trades"] / max(baseline["trades"], 1) * 10)
    return round(min(100.0, window_score + coin_score + pf_score + net_score + dd_score + sample_score), 2)


def main() -> None:
    trades = sorted(load_trades(), key=lambda item: item.get("entry_time") or 0)
    common_start = trades[0]["entry_time"]
    common_end = trades[-1]["entry_time"]
    span = common_end - common_start
    segment_span = span / 5
    baseline = metrics(trades)
    print(f"DATA|trades={len(trades)}|common_start={common_start}|common_end={common_end}|segments=5|permutations={PERMUTATIONS}")
    print(f"BASELINE|{baseline}")

    time_segments = []
    for index in range(5):
        start = common_start + index * segment_span
        end = common_start + (index + 1) * segment_span
        segment = [trade for trade in trades if start <= trade["entry_time"] <= end]
        time_segments.append((start, end, segment))

    results = {}
    for threshold in THRESHOLDS:
        filtered = select(trades, threshold)
        filtered_result = metrics(filtered)
        better_segments = 0
        segment_rows = []
        for index, (start, end, baseline_segment) in enumerate(time_segments, start=1):
            filtered_segment = [trade for trade in filtered if start <= trade["entry_time"] <= end]
            base_metrics = metrics(baseline_segment)
            filtered_metrics = metrics(filtered_segment)
            is_better = better(filtered_metrics, base_metrics)
            better_segments += int(is_better)
            segment_rows.append((index, start, end, base_metrics, filtered_metrics, is_better))

        better_coins = 0
        coin_rows = []
        for symbol in SYMBOLS:
            base_coin = metrics([trade for trade in trades if trade["coin"] == symbol])
            filtered_coin = metrics([trade for trade in filtered if trade["coin"] == symbol])
            is_better = better(filtered_coin, base_coin)
            better_coins += int(is_better)
            coin_rows.append((symbol, base_coin, filtered_coin, is_better))

        results[threshold] = {
            **filtered_result,
            "threshold": threshold,
            "better_time_segments": better_segments,
            "better_coins": better_coins,
            "segments": segment_rows,
            "coins": coin_rows,
        }

    print("THRESHOLD SUMMARY")
    for threshold, result in results.items():
        result["robustness_score"] = score(result, baseline, len(time_segments))
        print(
            f"{threshold}|trades={result['trades']}|WR={result['win_rate']:.2f}|"
            f"PF={result['profit_factor']:.2f}|net={result['net_pnl']:.2f}|"
            f"DD={result['max_drawdown']:.2f}|better_segments={result['better_time_segments']}/5|"
            f"better_coins={result['better_coins']}/6|score={result['robustness_score']:.2f}"
        )

    print("LEAVE ONE OUT")
    for threshold in THRESHOLDS:
        result = results[threshold]
        for symbol in SYMBOLS:
            base_items = [trade for trade in trades if trade["coin"] != symbol]
            filtered_items = [trade for trade in select(trades, threshold) if trade["coin"] != symbol]
            base_metrics = metrics(base_items)
            filtered_metrics = metrics(filtered_items)
            print(
                f"threshold={threshold}|excluded={symbol}|"
                f"baseline_net={base_metrics['net_pnl']:.2f}|filtered_net={filtered_metrics['net_pnl']:.2f}|"
                f"baseline_pf={base_metrics['profit_factor']:.2f}|filtered_pf={filtered_metrics['profit_factor']:.2f}|"
                f"baseline_dd={base_metrics['max_drawdown']:.2f}|filtered_dd={filtered_metrics['max_drawdown']:.2f}|"
                f"better={better(filtered_metrics, base_metrics)}"
            )

    print("TIME SEGMENTS")
    for threshold, result in results.items():
        for index, start, end, base_metrics, filtered_metrics, is_better in result["segments"]:
            print(
                f"threshold={threshold}|segment={index}|start={int(start)}|end={int(end)}|"
                f"baseline_net={base_metrics['net_pnl']:.2f}|filtered_net={filtered_metrics['net_pnl']:.2f}|"
                f"baseline_pf={base_metrics['profit_factor']:.2f}|filtered_pf={filtered_metrics['profit_factor']:.2f}|"
                f"baseline_dd={base_metrics['max_drawdown']:.2f}|filtered_dd={filtered_metrics['max_drawdown']:.2f}|better={is_better}"
            )

    print("MONTE CARLO")
    for threshold, result in results.items():
        filtered = select(trades, threshold)
        base_permutations = permutation_metrics(trades, random.Random(SEED + threshold))
        filtered_permutations = permutation_metrics(filtered, random.Random(SEED + threshold + 1_000))
        dd_advantage = sum(
            filtered_permutations[index]["permutation_dd"] > base_permutations[index]["permutation_dd"]
            for index in range(PERMUTATIONS)
        ) / PERMUTATIONS * 100
        result["random_dd_advantage"] = dd_advantage
        print(
            f"threshold={threshold}|baseline_final_pnl={base_permutations[0]['permutation_net']:.2f}|"
            f"filtered_final_pnl={filtered_permutations[0]['permutation_net']:.2f}|"
            f"baseline_dd_avg={sum(item['permutation_dd'] for item in base_permutations)/PERMUTATIONS:.2f}|"
            f"filtered_dd_avg={sum(item['permutation_dd'] for item in filtered_permutations)/PERMUTATIONS:.2f}|"
            f"filtered_dd_advantage_pct={dd_advantage:.2f}"
        )

    ranked = sorted(results.values(), key=lambda item: item["robustness_score"], reverse=True)
    print("FINAL")
    print(f"ROBUSTNESS_SCORE={ranked[0]['robustness_score']:.2f}")
    print(f"BEST_THRESHOLD={ranked[0]['threshold']}")
    print("CONFIDENCE_LEVEL=LOW_TO_MEDIUM; limited historical sample and five segments")
    print("DATA-BASED CANDIDATE ONLY; no production recommendation")


if __name__ == "__main__":
    main()
