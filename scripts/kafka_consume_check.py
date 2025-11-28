#!/usr/bin/env python3
"""
Kafka Consumer Validation Script
=================================
This script reads messages from the Kafka topic 'ticks.raw'
to verify that the WebSocket ingestor is working correctly.

Usage:
    python3 kafka_consume_check.py
    
Press Ctrl+C to stop.
"""

import json
import logging
from kafka import KafkaConsumer

# ============================================================================
# CONFIGURATION
# ============================================================================

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "ticks.raw"

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Consume messages from Kafka topic and display them.
    """
    logger.info("=" * 70)
    logger.info("📥 Kafka Consumer - Validation Check")
    logger.info("=" * 70)
    logger.info(f"🔧 Kafka Server: {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"📊 Topic: {KAFKA_TOPIC}")
    logger.info(f"⏳ Waiting for messages... (Press Ctrl+C to stop)")
    logger.info("=" * 70)
    
    try:
        # Create Kafka consumer
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',  # Start from beginning of topic
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        logger.info(f"✅ Connected to Kafka!")
        logger.info(f"📖 Reading from topic '{KAFKA_TOPIC}'...")
        logger.info("")
        
        message_count = 0
        
        # Read messages from Kafka
        for message in consumer:
            message_count += 1
            data = message.value
            
            # Extract relevant fields
            product_id = data.get('product_id', 'N/A')
            price = data.get('price', 'N/A')
            time = data.get('time', 'N/A')
            volume_24h = data.get('volume_24h', 'N/A')
            
            # Display message
            print(f"\n{'='*70}")
            print(f"📨 Message #{message_count}")
            print(f"{'='*70}")
            print(f"  🪙  Product:    {product_id}")
            print(f"  💵 Price:      ${price}")
            print(f"  🕐 Time:       {time}")
            print(f"  📊 24h Volume: {volume_24h}")
            print(f"{'='*70}")
            
            # Show full message every 10 messages
            if message_count % 10 == 0:
                print(f"\n📋 Full message #{message_count}:")
                print(json.dumps(data, indent=2))
                print("")
                
    except KeyboardInterrupt:
        logger.info(f"\n\n⏹️  Stopped by user")
        logger.info(f"📊 Total messages consumed: {message_count}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
    finally:
        if consumer:
            consumer.close()
            logger.info("✅ Consumer closed")

if __name__ == "__main__":
    main()
