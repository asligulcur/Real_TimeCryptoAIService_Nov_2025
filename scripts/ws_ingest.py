#!/usr/bin/env python3
"""
Coinbase WebSocket Ingestor
============================
This script connects to Coinbase's real-time WebSocket feed,
subscribes to crypto ticker data, and publishes it to Kafka.

Features:
- Real-time data ingestion from Coinbase Exchange
- Automatic reconnection on disconnection
- Heartbeat mechanism to keep connection alive
- Publishes to Kafka topic 'ticks.raw'
- Optional: Save raw data to local files
"""

import json
import time
import logging
import ssl
import os
from datetime import datetime
from kafka import KafkaProducer
from websocket import WebSocketApp

# ============================================================================
# CONFIGURATION
# ============================================================================

# Coinbase WebSocket URL
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# Trading pairs to subscribe to (you can add more like "ETH-USD", "SOL-USD")
TRADING_PAIRS = ["BTC-USD"]

# Kafka configuration
# Use environment variable to support both local and Docker deployments
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = "ticks.raw"

# Reconnection settings
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5  # seconds

# Heartbeat settings (to keep connection alive)
HEARTBEAT_INTERVAL = 30  # seconds

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# KAFKA PRODUCER SETUP
# ============================================================================

def create_kafka_producer():
    """
    Create a Kafka producer that will send messages to our Kafka broker.
    
    value_serializer: Converts Python dictionaries to JSON bytes for Kafka
    """
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logger.info(f"✅ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
        return producer
    except Exception as e:
        logger.error(f"❌ Failed to create Kafka producer: {e}")
        raise

# ============================================================================
# WEBSOCKET EVENT HANDLERS
# ============================================================================

class CoinbaseIngestor:
    """
    Handles WebSocket connection to Coinbase and publishes data to Kafka.
    """
    
    def __init__(self):
        self.producer = create_kafka_producer()
        self.ws = None
        self.reconnect_count = 0
        self.message_count = 0
        self.last_heartbeat = time.time()
        
    def on_open(self, ws):
        """
        Called when WebSocket connection is established.
        Send subscription message to Coinbase.
        """
        logger.info("🔗 WebSocket connection opened!")
        
        # Create subscription message
        # This tells Coinbase: "Send me ticker updates for these trading pairs"
        subscribe_message = {
            "type": "subscribe",
            "product_ids": TRADING_PAIRS,
            "channels": ["ticker"]  # ticker channel gives us price updates
        }
        
        # Send the subscription
        ws.send(json.dumps(subscribe_message))
        logger.info(f"📡 Subscribed to ticker data for: {', '.join(TRADING_PAIRS)}")
        
        # Reset reconnect counter on successful connection
        self.reconnect_count = 0
    
    def on_message(self, ws, message):
        """
        Called when we receive a message from Coinbase.
        Parse the message and send it to Kafka.
        """
        try:
            # Parse JSON message from Coinbase
            data = json.loads(message)
            
            # Coinbase sends different types of messages
            # We only want "ticker" messages (price updates)
            if data.get("type") == "ticker":
                
                # Add timestamp when we received this message
                data["ingestion_timestamp"] = datetime.utcnow().isoformat()
                
                # Send to Kafka
                self.producer.send(KAFKA_TOPIC, value=data)
                
                # Update counter
                self.message_count += 1
                
                # Log every 10 messages so we can see progress
                if self.message_count % 10 == 0:
                    price = data.get("price", "N/A")
                    product = data.get("product_id", "N/A")
                    logger.info(f"📊 Message #{self.message_count} | {product}: ${price}")
            
            # Update heartbeat timestamp
            self.last_heartbeat = time.time()
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    def on_error(self, ws, error):
        """
        Called when an error occurs with the WebSocket connection.
        """
        logger.error(f"❌ WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """
        Called when WebSocket connection is closed.
        Attempt to reconnect if needed.
        """
        logger.warning(f"🔌 WebSocket connection closed: {close_msg} (code: {close_status_code})")
        
        # Try to reconnect if we haven't exceeded max attempts
        if self.reconnect_count < MAX_RECONNECT_ATTEMPTS:
            self.reconnect_count += 1
            logger.info(f"🔄 Reconnecting... (Attempt {self.reconnect_count}/{MAX_RECONNECT_ATTEMPTS})")
            time.sleep(RECONNECT_DELAY)
            self.connect()
        else:
            logger.error(f"❌ Max reconnection attempts reached. Giving up.")
    
    def connect(self):
        """
        Establish WebSocket connection to Coinbase.
        """
        logger.info(f"🚀 Connecting to Coinbase WebSocket: {COINBASE_WS_URL}")
        
        # Create WebSocket application with our event handlers
        self.ws = WebSocketApp(
            COINBASE_WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run the WebSocket with SSL disabled cert verification (for dev)
        # Note: In production, you'd want proper SSL verification
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    
    def check_heartbeat(self):
        """
        Check if connection is still alive by monitoring message timestamps.
        If no messages received for too long, reconnect.
        """
        time_since_last_message = time.time() - self.last_heartbeat
        
        if time_since_last_message > HEARTBEAT_INTERVAL:
            logger.warning(f"⚠️  No messages for {time_since_last_message:.0f} seconds. Reconnecting...")
            if self.ws:
                self.ws.close()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main entry point for the WebSocket ingestor.
    """
    logger.info("=" * 70)
    logger.info("🚀 Starting Coinbase WebSocket Ingestor")
    logger.info("=" * 70)
    logger.info(f"📍 Coinbase URL: {COINBASE_WS_URL}")
    logger.info(f"📊 Trading Pairs: {', '.join(TRADING_PAIRS)}")
    logger.info(f"📤 Kafka Topic: {KAFKA_TOPIC}")
    logger.info(f"🔧 Kafka Server: {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info("=" * 70)
    
    try:
        # Create ingestor and connect
        ingestor = CoinbaseIngestor()
        ingestor.connect()
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Shutting down gracefully...")
        logger.info(f"📊 Total messages processed: {ingestor.message_count}")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
    finally:
        # Clean up
        if ingestor.producer:
            ingestor.producer.close()
            logger.info("✅ Kafka producer closed")

if __name__ == "__main__":
    main()
