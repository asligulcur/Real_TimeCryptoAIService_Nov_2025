#!/usr/bin/env python3
"""
Resilient Kafka Consumer - Enhanced Version
============================================
Production-ready Kafka consumer with:
- Automatic reconnection
- Commit retry logic
- Graceful shutdown
- Health monitoring
- Error handling and recovery

Author: Crypto Volatility Team
Date: November 26, 2025
"""

import json
import logging
import os
import signal
import sys
import time
from typing import Optional
from kafka import KafkaConsumer
from kafka.errors import KafkaError, CommitFailedError

# ============================================================================
# CONFIGURATION
# ============================================================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "ticks.raw")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "crypto-volatility-consumer")

# Retry configuration
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5  # seconds
COMMIT_RETRY_ATTEMPTS = 3
COMMIT_RETRY_DELAY = 1  # seconds

# Consumer configuration
SESSION_TIMEOUT_MS = 30000  # 30 seconds
HEARTBEAT_INTERVAL_MS = 10000  # 10 seconds
MAX_POLL_RECORDS = 100  # Process in batches
AUTO_COMMIT_INTERVAL_MS = 5000  # 5 seconds

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# RESILIENT KAFKA CONSUMER
# ============================================================================


class ResilientKafkaConsumer:
    """
    Production-ready Kafka consumer with resilience patterns.
    """

    def __init__(self):
        self.consumer: Optional[KafkaConsumer] = None
        self.shutdown_requested = False
        self.reconnect_count = 0
        self.message_count = 0
        self.error_count = 0
        self.last_commit_time = time.time()

        # Metrics
        self.metrics = {
            "messages_processed": 0,
            "messages_failed": 0,
            "commit_successes": 0,
            "commit_failures": 0,
            "reconnections": 0,
        }

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self.handle_shutdown_signal)

    def handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"\n🛑 Received shutdown signal ({signum})")
        self.shutdown_requested = True
        self.graceful_shutdown()

    def graceful_shutdown(self):
        """Perform graceful shutdown."""
        logger.info("🛑 Initiating graceful shutdown...")

        if self.consumer:
            try:
                # Commit final offsets
                logger.info("💾 Committing final offsets...")
                self.consumer.commit()
                self.metrics["commit_successes"] += 1
                logger.info("✅ Final offsets committed")
            except Exception as e:
                logger.error(f"Error committing final offsets: {e}")

            try:
                # Close consumer
                self.consumer.close()
                logger.info("✅ Kafka consumer closed")
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")

        # Print final metrics
        self.print_metrics()
        logger.info("✅ Graceful shutdown complete")
        sys.exit(0)

    def print_metrics(self):
        """Print current metrics."""
        logger.info("=" * 70)
        logger.info("📊 Session Metrics:")
        logger.info("=" * 70)
        logger.info(f"  Messages Processed:  {self.metrics['messages_processed']}")
        logger.info(f"  Messages Failed:     {self.metrics['messages_failed']}")
        logger.info(f"  Commit Successes:    {self.metrics['commit_successes']}")
        logger.info(f"  Commit Failures:     {self.metrics['commit_failures']}")
        logger.info(f"  Reconnections:       {self.metrics['reconnections']}")
        logger.info("=" * 70)

    def create_consumer(self):
        """Create Kafka consumer with retry logic."""
        for attempt in range(MAX_RECONNECT_ATTEMPTS):
            try:
                consumer = KafkaConsumer(
                    KAFKA_TOPIC,
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    group_id=CONSUMER_GROUP,
                    auto_offset_reset="earliest",
                    enable_auto_commit=False,  # Manual commit for better control
                    session_timeout_ms=SESSION_TIMEOUT_MS,
                    heartbeat_interval_ms=HEARTBEAT_INTERVAL_MS,
                    max_poll_records=MAX_POLL_RECORDS,
                    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                    # Consumer coordination settings
                    max_poll_interval_ms=300000,  # 5 minutes max processing time
                    request_timeout_ms=40000,  # 40 seconds
                    retry_backoff_ms=100,
                )

                logger.info(f"✅ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
                logger.info(f"📖 Subscribed to topic: {KAFKA_TOPIC}")
                logger.info(f"👥 Consumer group: {CONSUMER_GROUP}")

                self.reconnect_count = 0
                return consumer

            except Exception as e:
                logger.error(
                    f"❌ Connection attempt {attempt + 1}/{MAX_RECONNECT_ATTEMPTS} failed: {e}"
                )
                if attempt < MAX_RECONNECT_ATTEMPTS - 1:
                    logger.info(f"⏳ Retrying in {RECONNECT_DELAY} seconds...")
                    time.sleep(RECONNECT_DELAY)
                else:
                    logger.error("❌ All connection attempts failed")
                    return None

    def commit_with_retry(self):
        """Commit offsets with retry logic."""
        for attempt in range(COMMIT_RETRY_ATTEMPTS):
            try:
                self.consumer.commit()
                self.metrics["commit_successes"] += 1
                self.last_commit_time = time.time()
                logger.debug("✅ Offsets committed successfully")
                return True

            except CommitFailedError as e:
                self.metrics["commit_failures"] += 1
                logger.error(
                    f"❌ Commit failed (attempt {attempt + 1}/{COMMIT_RETRY_ATTEMPTS}): {e}"
                )

                if attempt < COMMIT_RETRY_ATTEMPTS - 1:
                    time.sleep(COMMIT_RETRY_DELAY)
                else:
                    logger.error("❌ All commit attempts failed")
                    return False

            except Exception as e:
                logger.error(f"❌ Unexpected commit error: {e}")
                return False

        return False

    def process_message(self, message):
        """
        Process a single message.
        Override this method for custom processing logic.

        Args:
            message: Kafka message

        Returns:
            bool: True if processing succeeded, False otherwise
        """
        try:
            data = message.value

            # Extract relevant fields
            product_id = data.get("product_id", "N/A")
            price = data.get("price", "N/A")
            time_str = data.get("time", "N/A")

            # Display message (example processing)
            self.message_count += 1

            if self.message_count % 10 == 0:
                logger.info(
                    f"📊 Processed {self.message_count} messages | "
                    f"{product_id}: ${price} @ {time_str}"
                )

            self.metrics["messages_processed"] += 1
            return True

        except Exception as e:
            self.error_count += 1
            self.metrics["messages_failed"] += 1
            logger.error(f"❌ Error processing message: {e}")
            return False

    def consume(self):
        """Main consumption loop with resilience."""
        logger.info("=" * 70)
        logger.info("📥 Starting Resilient Kafka Consumer")
        logger.info("=" * 70)
        logger.info(f"🔧 Kafka Server: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"📊 Topic: {KAFKA_TOPIC}")
        logger.info(f"👥 Consumer Group: {CONSUMER_GROUP}")
        logger.info(f"⏳ Waiting for messages... (Press Ctrl+C to stop)")
        logger.info("=" * 70)

        # Create consumer
        self.consumer = self.create_consumer()
        if not self.consumer:
            logger.error("❌ Failed to create consumer. Exiting.")
            sys.exit(1)

        messages_since_commit = 0
        commit_interval = 100  # Commit every 100 messages

        try:
            while not self.shutdown_requested:
                try:
                    # Poll for messages with timeout
                    messages = self.consumer.poll(timeout_ms=1000, max_records=MAX_POLL_RECORDS)

                    if not messages:
                        continue

                    # Process messages
                    for topic_partition, records in messages.items():
                        for message in records:
                            success = self.process_message(message)

                            if success:
                                messages_since_commit += 1

                            # Commit periodically
                            if messages_since_commit >= commit_interval:
                                self.commit_with_retry()
                                messages_since_commit = 0

                    # Also commit based on time (every 5 seconds)
                    if time.time() - self.last_commit_time >= 5:
                        if messages_since_commit > 0:
                            self.commit_with_retry()
                            messages_since_commit = 0

                except KafkaError as e:
                    logger.error(f"❌ Kafka error: {e}")
                    self.error_count += 1

                    # Try to reconnect
                    logger.info("🔄 Attempting to reconnect...")
                    self.metrics["reconnections"] += 1

                    if self.consumer:
                        try:
                            self.consumer.close()
                        except:
                            pass

                    self.consumer = self.create_consumer()
                    if not self.consumer:
                        logger.error("❌ Reconnection failed. Exiting.")
                        break

                    messages_since_commit = 0

                except Exception as e:
                    logger.error(f"❌ Unexpected error: {e}")
                    self.error_count += 1
                    time.sleep(1)  # Brief pause before continuing

        except KeyboardInterrupt:
            logger.info("\n⏹️  Stopped by user")
        finally:
            self.graceful_shutdown()


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main():
    """Main entry point."""
    try:
        consumer = ResilientKafkaConsumer()
        consumer.consume()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
