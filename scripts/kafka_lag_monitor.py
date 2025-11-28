#!/usr/bin/env python3
"""
Kafka Consumer Lag Monitor for Prometheus

This script monitors Kafka consumer lag and exposes metrics via Prometheus.
It runs as a separate service and updates the consumer_lag_gauge metric.

Author: CMU Heinz Team
Date: November 2025
"""

import time
from typing import Dict, List

from kafka import KafkaConsumer, KafkaAdminClient, TopicPartition
from kafka.structs import OffsetAndMetadata
from prometheus_client import Gauge, start_http_server
import yaml

# ============================================================================
# Configuration
# ============================================================================

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

KAFKA_BOOTSTRAP_SERVERS = config["kafka"]["bootstrap_servers"]
CONSUMER_GROUP = config["kafka"]["consumer_group"]
TOPICS = [
    config["kafka"]["topics"]["raw"],
    config["kafka"]["topics"]["features"],
]

# Prometheus metrics port (separate from API)
METRICS_PORT = 9091

# Monitoring interval
MONITOR_INTERVAL = 15  # seconds

# ============================================================================
# Prometheus Metrics
# ============================================================================

consumer_lag_gauge = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag in messages",
    ["topic", "partition", "consumer_group"],
)

consumer_offset_gauge = Gauge(
    "kafka_consumer_offset",
    "Current consumer offset",
    ["topic", "partition", "consumer_group"],
)

log_end_offset_gauge = Gauge(
    "kafka_log_end_offset",
    "Current log end offset (latest message)",
    ["topic", "partition"],
)

consumer_group_lag_total = Gauge(
    "kafka_consumer_group_lag_total",
    "Total lag across all partitions for a consumer group",
    ["consumer_group", "topic"],
)

# ============================================================================
# Lag Monitoring
# ============================================================================


class KafkaLagMonitor:
    """Monitor Kafka consumer lag and update Prometheus metrics."""

    def __init__(
        self,
        bootstrap_servers: str,
        consumer_group: str,
        topics: List[str],
    ):
        self.bootstrap_servers = bootstrap_servers
        self.consumer_group = consumer_group
        self.topics = topics

        # Initialize Kafka admin client
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=self.bootstrap_servers,
            client_id="lag-monitor",
        )

        # Initialize consumer for offset management
        self.consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"{self.consumer_group}-monitor",
            enable_auto_commit=False,
        )

        print(f"✅ Kafka Lag Monitor initialized")
        print(f"   Bootstrap servers: {self.bootstrap_servers}")
        print(f"   Consumer group: {self.consumer_group}")
        print(f"   Topics: {', '.join(self.topics)}")

    def get_consumer_offsets(
        self, topic: str, partitions: List[int]
    ) -> Dict[int, int]:
        """Get current consumer offsets for a topic."""
        offsets = {}

        for partition in partitions:
            tp = TopicPartition(topic, partition)

            # Get committed offset
            committed = self.consumer.committed(tp)
            offsets[partition] = committed if committed is not None else 0

        return offsets

    def get_log_end_offsets(self, topic: str, partitions: List[int]) -> Dict[int, int]:
        """Get log end offsets (latest message) for a topic."""
        offsets = {}

        for partition in partitions:
            tp = TopicPartition(topic, partition)

            # Get end offset
            end_offsets = self.consumer.end_offsets([tp])
            offsets[partition] = end_offsets[tp]

        return offsets

    def calculate_lag(self, topic: str) -> Dict[int, Dict[str, int]]:
        """Calculate lag for all partitions of a topic."""
        # Get topic metadata
        topic_partitions = self.consumer.partitions_for_topic(topic)

        if not topic_partitions:
            print(f"⚠️  No partitions found for topic: {topic}")
            return {}

        partitions = sorted(list(topic_partitions))

        # Get consumer offsets
        consumer_offsets = self.get_consumer_offsets(topic, partitions)

        # Get log end offsets
        log_end_offsets = self.get_log_end_offsets(topic, partitions)

        # Calculate lag
        lag_info = {}
        for partition in partitions:
            consumer_offset = consumer_offsets.get(partition, 0)
            log_end_offset = log_end_offsets.get(partition, 0)
            lag = log_end_offset - consumer_offset

            lag_info[partition] = {
                "consumer_offset": consumer_offset,
                "log_end_offset": log_end_offset,
                "lag": lag,
            }

        return lag_info

    def update_metrics(self):
        """Update Prometheus metrics with current lag."""
        for topic in self.topics:
            try:
                lag_info = self.calculate_lag(topic)

                total_lag = 0

                for partition, info in lag_info.items():
                    # Update per-partition metrics
                    consumer_lag_gauge.labels(
                        topic=topic,
                        partition=str(partition),
                        consumer_group=self.consumer_group,
                    ).set(info["lag"])

                    consumer_offset_gauge.labels(
                        topic=topic,
                        partition=str(partition),
                        consumer_group=self.consumer_group,
                    ).set(info["consumer_offset"])

                    log_end_offset_gauge.labels(
                        topic=topic, partition=str(partition)
                    ).set(info["log_end_offset"])

                    total_lag += info["lag"]

                # Update total lag for consumer group
                consumer_group_lag_total.labels(
                    consumer_group=self.consumer_group, topic=topic
                ).set(total_lag)

                print(
                    f"📊 {topic}: Total lag = {total_lag} messages across {len(lag_info)} partitions"
                )

            except Exception as e:
                print(f"❌ Error monitoring topic {topic}: {e}")

    def run(self, interval: int = MONITOR_INTERVAL):
        """Run continuous monitoring loop."""
        print(f"🚀 Starting Kafka lag monitoring (interval: {interval}s)")
        print(f"📊 Metrics available at http://localhost:{METRICS_PORT}/metrics")

        while True:
            try:
                self.update_metrics()
                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n⚠️  Shutting down Kafka lag monitor...")
                break

            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(interval)

        # Cleanup
        self.consumer.close()
        self.admin_client.close()
        print("✅ Kafka lag monitor stopped")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point."""
    # Start Prometheus metrics server
    start_http_server(METRICS_PORT)
    print(f"✅ Prometheus metrics server started on port {METRICS_PORT}")

    # Initialize and run monitor
    monitor = KafkaLagMonitor(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        consumer_group=CONSUMER_GROUP,
        topics=TOPICS,
    )

    monitor.run(interval=MONITOR_INTERVAL)


if __name__ == "__main__":
    main()
