from __future__ import annotations

from html import escape

from lora_sim.domain.metrics import SimulationMetrics


def render_text_report(metrics: SimulationMetrics) -> str:
    lines = [
        f"Scenario: {metrics.scenario_name}",
        f"Seed: {metrics.seed}",
        f"Packets Sent: {metrics.packets_sent}",
        f"Packets Delivered: {metrics.packets_delivered}",
        f"Packets Lost: {metrics.packets_lost}",
        f"Uplinks Delivered: {metrics.uplinks_delivered}",
        f"Delivery Rate: {metrics.delivery_rate * 100:.2f}%",
        f"Collisions: {metrics.collisions}",
        f"Corruptions: {metrics.corruptions}",
        f"Interference Losses: {metrics.interference_losses}",
        f"Retries: {metrics.retries}",
        f"ACK Requests: {metrics.ack_requests}",
        f"ACK Successes: {metrics.ack_successes}",
        f"ACK Failures: {metrics.ack_failures}",
        f"Average Latency: {metrics.average_latency_seconds:.4f}s",
        f"Total Airtime: {metrics.total_airtime_seconds:.4f}s",
        f"Total Energy: {metrics.total_energy_joules:.6f}J",
        "",
        "Per Gateway:",
    ]
    for gateway_id, data in sorted(metrics.gateway_receptions.items()):
        lines.append(f"  {gateway_id}: uplinks={data['uplinks']} acks={data['acks']}")

    lines.extend(["", "Per Node:"])
    all_node_ids = sorted(set(metrics.node_delivery) | set(metrics.node_energy))
    for node_id in all_node_ids:
        data = metrics.node_delivery.get(node_id, {"sent": 0, "delivered": 0, "lost": 0})
        energy = metrics.node_energy.get(node_id)
        energy_text = ""
        if energy is not None:
            energy_text = f" energy={energy.total_energy_joules:.6f}J"
        lines.append(
            f"  {node_id}: sent={data['sent']} delivered={data['delivered']} lost={data['lost']}{energy_text}"
        )
    return "\n".join(lines)


def render_html_report(metrics: SimulationMetrics) -> str:
    body = render_text_report(metrics).splitlines()
    rows = "".join(f"<li>{escape(line)}</li>" for line in body if line)
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{escape(metrics.scenario_name)} report</title>
    <style>
      body {{
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        margin: 2rem auto;
        max-width: 56rem;
        background: linear-gradient(135deg, #f6fbff, #eef2f7);
        color: #112235;
      }}
      .card {{
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 60px rgba(17, 34, 53, 0.12);
      }}
      h1 {{
        margin-top: 0;
      }}
      li {{
        margin-bottom: 0.5rem;
      }}
    </style>
  </head>
  <body>
    <section class="card">
      <h1>{escape(metrics.scenario_name)}</h1>
      <ul>{rows}</ul>
    </section>
  </body>
</html>
"""
