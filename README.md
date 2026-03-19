# LoRa Simulation Toolkit

`lora-sim` is a deterministic LoRa network simulation toolkit for repeatable scenario runs, collision analysis, ADR behavior, and structured reporting. The original repository was a single demo script; it is now organized as a real package with a simulation engine, scenario files, results export, and automated tests.

## What it does

- Runs event-driven LoRa simulations with fixed seeds
- Models nodes, radios, channels, retries, airtime, and ADR behavior
- Supports multi-node scenarios and collision pressure
- Tracks per-node radio energy for transmit, receive, and idle phases
- Supports Monte Carlo runs for repeatable benchmark aggregates
- Supports multi-gateway reception and gateway-level accounting
- Models confirmed uplinks with RX1 ACK timing
- Produces structured JSON or CSV outputs for analysis pipelines
- Generates lightweight HTML reports for sharing run results

## Project layout

```text
src/lora_sim/
  app/          CLI, runner, report rendering
  domain/       packets, nodes, radios, metrics, channel model
  io/           result writers
  models/       propagation, ADR, corruption, interference, retry policy
  simulation/   scenario loading, event queue, engine
scenarios/      example scenario definitions
tests/          regression and unit tests
```

## Quick start

```bash
python3 -m pip install -e .
lora-sim run scenarios/simple_link.json
```

Compatibility entrypoint:

```bash
python3 simulator.py run scenarios/simple_link.json
```

## Example commands

Run a scenario and print a text report:

```bash
lora-sim run scenarios/simple_link.json
```

Override the seed and save structured results:

```bash
lora-sim run scenarios/multi_node_collision.json --seed 99 --out results.json
```

Write a CSV packet log:

```bash
lora-sim run scenarios/multi_node_collision.json --out results.csv
```

Generate an HTML report during a run:

```bash
lora-sim run scenarios/simple_link.json --report report.html
```

Generate a report from saved results:

```bash
lora-sim report results.json --out report.html
```

Run a parameter sweep:

```bash
lora-sim sweep scenarios/simple_link.json --param nodes.gateway.x_m --range 500:3000:500
```

Compare two scenarios with the same seed:

```bash
lora-sim compare scenarios/simple_link.json scenarios/multi_node_collision.json --seed 42
```

Run a Monte Carlo batch:

```bash
lora-sim monte-carlo scenarios/multi_node_collision.json --iterations 20 --seed 100
```

Run a multi-gateway confirmed-uplink scenario:

```bash
lora-sim run scenarios/multi_gateway_ack.json
```

## Scenario format

Scenario files are JSON documents that define:

- simulation metadata such as `name`, `duration_seconds`, and `seed`
- channel behavior such as `noise_floor_dbm`, `path_loss_exponent`, interference settings, and gateway demodulation capacity
- ACK behavior through `ack_model`, including RX1 delay and downlink interference probability
- retry policy with `max_attempts` and `backoff_seconds`
- nodes with coordinates, role, radio settings, power profile, and optional traffic profiles
  `traffic.confirmed_messages` controls whether a node waits for gateway ACKs before the uplink attempt is considered successful

See [simple_link.json](/home/alex/Projects/lora-sim/scenarios/simple_link.json) and [multi_node_collision.json](/home/alex/Projects/lora-sim/scenarios/multi_node_collision.json) for working examples.
Use [gateway_capacity.json](/home/alex/Projects/lora-sim/scenarios/gateway_capacity.json) to stress-test the gateway demodulation path limit with overlapping uplinks.
Use [multi_gateway_ack.json](/home/alex/Projects/lora-sim/scenarios/multi_gateway_ack.json) to exercise gateway diversity with confirmed uplinks and ACK timing.

## Development

Run the test suite:

```bash
python3 -m pytest
```
