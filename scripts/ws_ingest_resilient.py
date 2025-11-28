#!/usr/bin/env python3
"""
Resilient Coinbase WebSocket Ingestor - Enhanced Version
=========================================================
Production-ready WebSocket ingestor with:
- Exponential backoff retry
- Circuit breaker pattern
- Graceful shutdown with signal handling
- Kafka producer retry logic
- Health monitoring
- Metrics tracking

Author: Crypto Volatility Team
Date: November 26, 2025
"""

import json
import time
import logging
import ssl
import os
import signal
import sys
from datetime import datetime
from typing import Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
from websocket import WebSocketApp

# ============================================================================
# CONFIGURATION
# ============================================================================

# Coinbase WebSocket URL
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# Trading pairs to subscribe to
TRADING_PAIRS = ["BTC-USD"]

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = "ticks.raw"

# Retry configuration (exponential backoff)
MIN_RECONNECT_DELAY = 1  # Start with 1 second
MAX_RECONNECT_DELAY = 60  # Cap at 60 seconds
MAX_RECONNECT_ATTEMPTS = 10  # More attempts with backoff
BACKOFF_MULTIPLIER = 2  # Double delay each time

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = 5  # Open circuit after 5 consecutive failures
CIRCUIT_BREAKER_TIMEOUT = 60  # Try again after 60 seconds

# Heartbeat settings
HEARTBEAT_INTERVAL = 30  # seconds
KAFKA_RETRY_ATTEMPTS = 3  # Retry sending to Kafka
KAFKA_RETRY_DELAY = 1  # seconds between retries

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# CIRCUIT BREAKER
# ============================================================================


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    States: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
    """

    def __init__(self, threshold=5, timeout=60):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        """Reset circuit breaker on success."""
        self.failure_count = 0
        self.state = "CLOSED"
        logger.debug("Circuit breaker: SUCCESS recorded, state=CLOSED")

    def record_failure(self):
        """Record a failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.threshold:
            self.state = "OPEN"
            logger.warning(
                f"⚠️  Circuit breaker OPEN after {self.failure_count} failures"
            )

    def can_attempt(self):
        """Check if we can attempt an operation."""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Check if timeout has passed
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = "HALF_OPEN"
                logger.info("🔧 Circuit breaker entering HALF_OPEN state")
                return True
            return False

        # HALF_OPEN state - allow one attempt
        return True

    def get_status(self):
        """Get current circuit breaker status."""
        return {
            "state": self.state,
            "failures": self.failure_count,
            "threshold": self.threshold,
        }


# ============================================================================
# KAFKA PRODUCER WITH RETRY
# ============================================================================


def create_kafka_producer_with_retry(max_retries=3):
    """
    Create Kafka producer with retry logic.

    Returns:
        KafkaProducer or None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=5,  # Kafka client-level retries
                retry_backoff_ms=100,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                acks="all",  # Wait for all replicas
            )
            logger.info(f"✅ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except Exception as e:
            logger.error(
                f"❌ Kafka connection attempt {attempt + 1}/{max_retries} failed: {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(KAFKA_RETRY_DELAY * (attempt + 1))  # Incremental backoff
            else:
                logger.error("❌ All Kafka connection attempts failed")
                return None


# ============================================================================
# RESILIENT WEBSOCKET INGESTOR
# ============================================================================


class ResilientCoinbaseIngestor:
    """
    Production-ready WebSocket ingestor with full resilience patterns.
    """

    def __init__(self):
        self.producer = None
        self.ws = None
        self.reconnect_count = 0
        self.message_count = 0
        self.error_count = 0
        self.last_heartbeat = time.time()
        self.shutdown_requested = False
        self.circuit_breaker = CircuitBreaker(
            threshold=CIRCUIT_BREAKER_THRESHOLD, timeout=CIRCUIT_BREAKER_TIMEOUT
        )

        # Metrics
        self.metrics = {
            "messages_sent": 0,
            "messages_failed": 0,
            "reconnections": 0,
            "kafka_errors": 0,
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

        # Close WebSocket
        if self.ws:
            try:
                self.ws.close()
                logger.info("✅ WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

        # Flush and close Kafka producer
        if self.producer:
            try:
                self.producer.flush(timeout=10)
                self.producer.close()
                logger.info("✅ Kafka producer flushed and closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")

        # Print final metrics
        self.print_metrics()
        logger.info("✅ Graceful shutdown complete")
        sys.exit(0)

    def print_metrics(self):
        """Print current metrics."""
        logger.info("=" * 70)
        logger.info("📊 Session Metrics:")
        logger.info("=" * 70)
        logger.info(f"  Messages Sent:      {self.metrics['messages_sent']}")
        logger.info(f"  Messages Failed:    {self.metrics['messages_failed']}")
        logger.info(f"  Reconnections:      {self.metrics['reconnections']}")
        logger.info(f"  Kafka Errors:       {self.metrics['kafka_errors']}")
        logger.info(f"  Circuit Breaker:    {self.circuit_breaker.state}")
        logger.info("=" * 70)

    def send_to_kafka_with_retry(self, data):
        """
        Send message to Kafka with retry logic.

        Args:
            data: Message data to send

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.producer:
            logger.error("❌ Kafka producer not initialized")
            return False

        for attempt in range(KAFKA_RETRY_ATTEMPTS):
            try:
                future = self.producer.send(KAFKA_TOPIC, value=data)
                # Block until message is sent (with timeout)
                future.get(timeout=5)
                self.metrics["messages_sent"] += 1
                self.circuit_breaker.record_success()
                return True

            except KafkaError as e:
                self.metrics["kafka_errors"] += 1
                self.circuit_breaker.record_failure()
                logger.error(
                    f"❌ Kafka error (attempt {attempt + 1}/{KAFKA_RETRY_ATTEMPTS}): {e}"
                )

                if attempt < KAFKA_RETRY_ATTEMPTS - 1:
                    time.sleep(KAFKA_RETRY_DELAY)
                else:
                    self.metrics["messages_failed"] += 1
                    return False

            except Exception as e:
                logger.error(f"❌ Unexpected error sending to Kafka: {e}")
                self.metrics["messages_failed"] += 1
                return False

        return False

    def on_open(self, ws):
        """Called when WebSocket connection is established."""
        logger.info("🔗 WebSocket connection opened!")

        # Create subscription message
        subscribe_message = {
            "type": "subscribe",
            "product_ids": TRADING_PAIRS,
            "channels": ["ticker"],
        }

        ws.send(json.dumps(subscribe_message))
        logger.info(f"📡 Subscribed to ticker data for: {', '.join(TRADING_PAIRS)}")

        # Reset reconnect counter and circuit breaker on successful connection
        self.reconnect_count = 0
        self.circuit_breaker.record_success()

    def on_message(self, ws, message):
        """Called when receiving a message from Coinbase."""
        try:
            data = json.loads(message)

            if data.get("type") == "ticker":
                # Add ingestion timestamp
                data["ingestion_timestamp"] = datetime.utcnow().isoformat()

                # Send to Kafka with retry
                success = self.send_to_kafka_with_retry(data)

                if success:
                    self.message_count += 1
                    if self.message_count % 10 == 0:
                        price = data.get("price", "N/A")
                        product = data.get("product_id", "N/A")
                        logger.info(
                            f"📊 Message #{self.message_count} | {product}: ${price}"
                        )

            # Update heartbeat
            self.last_heartbeat = time.time()

        except json.JSONDecodeError as e:
            self.error_count += 1
            logger.error(f"❌ Failed to parse message: {e}")
        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Error processing message: {e}")

    def on_error(self, ws, error):
        """Called when WebSocket error occurs."""
        self.error_count += 1
        logger.error(f"❌ WebSocket error: {error}")
        self.circuit_breaker.record_failure()

    def on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket connection closes."""
        logger.warning(
            f"🔌 WebSocket closed: {close_msg} (code: {close_status_code})"
        )

        if self.shutdown_requested:
            return

        # Exponential backoff reconnection
        self.reconnect_with_backoff()

    def reconnect_with_backoff(self):
        """Reconnect with exponential backoff."""
        if not self.circuit_breaker.can_attempt():
            logger.error(
                "❌ Circuit breaker OPEN - waiting before retry..."
            )
            time.sleep(CIRCUIT_BREAKER_TIMEOUT)
            return

        if self.reconnect_count >= MAX_RECONNECT_ATTEMPTS:
            logger.error("❌ Max reconnection attempts reached. Shutting down.")
            self.graceful_shutdown()
            return

        # Calculate backoff delay
        delay = min(
            MIN_RECONNECT_DELAY * (BACKOFF_MULTIPLIER**self.reconnect_count),
            MAX_RECONNECT_DELAY,
        )

        self.reconnect_count += 1
        self.metrics["reconnections"] += 1

        logger.info(
            f"🔄 Reconnecting in {delay}s... (Attempt {self.reconnect_count}/{MAX_RECONNECT_ATTEMPTS})"
        )
        time.sleep(delay)

        # Recreate Kafka producer if needed
        if not self.producer:
            self.producer = create_kafka_producer_with_retry()
            if not self.producer:
                logger.error("❌ Failed to reconnect to Kafka")
                return

        self.connect()

    def connect(self):
        """Establish WebSocket connection."""
        logger.info(f"🚀 Connecting to Coinbase WebSocket: {COINBASE_WS_URL}")

        self.ws = WebSocketApp(
            COINBASE_WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def start(self):
        """Start the ingestor."""
        logger.info("=" * 70)
        logger.info("🚀 Starting Resilient Coinbase WebSocket Ingestor")
        logger.info("=" * 70)
        logger.info(f"📍 Coinbase URL: {COINBASE_WS_URL}")
        logger.info(f"📊 Trading Pairs: {', '.join(TRADING_PAIRS)}")
        logger.info(f"📤 Kafka Topic: {KAFKA_TOPIC}")
        logger.info(f"🔧 Kafka Server: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"🔄 Max Reconnect Attempts: {MAX_RECONNECT_ATTEMPTS}")
        logger.info(f"⚡ Backoff: {MIN_RECONNECT_DELAY}s - {MAX_RECONNECT_DELAY}s")
        logger.info("=" * 70)

        # Create Kafka producer
        self.producer = create_kafka_producer_with_retry()
        if not self.producer:
            logger.error("❌ Failed to create Kafka producer. Exiting.")
            sys.exit(1)

        # Connect to WebSocket
        self.connect()


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main():
    """Main entry point."""
    try:
        ingestor = ResilientCoinbaseIngestor()
        ingestor.start()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
