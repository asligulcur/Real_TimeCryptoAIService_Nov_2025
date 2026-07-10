#!/usr/bin/env python3
"""
Featurizer - Real-Time Feature Engineering Consumer

This Kafka consumer:
1. Reads raw tick data from 'ticks.raw' topic
2. Maintains a rolling buffer of recent ticks
3. Calculates features for volatility prediction
4. Outputs to both Parquet file and Kafka topic 'ticks.features'

Features calculated:
- Midprice returns (% change over time windows)
- Rolling volatility (standard deviation)
- Bid-ask spread
- Trade intensity (trades per minute)

Author: Asli Gulcur
Author: Asli Gulcur
"""

import json
import logging
import sys
import statistics
import pandas as pd
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

from kafka import KafkaConsumer, KafkaProducer

# ============================================================================
# CONFIGURATION
# ============================================================================

# Kafka settings
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
INPUT_TOPIC = "ticks.raw"           # Read raw ticks from here
OUTPUT_TOPIC = "ticks.features"     # Publish features to here

# Feature engineering settings
BUFFER_SIZE = 500                    # Keep last 500 ticks in memory (~5 min at 2/sec)
PARQUET_PATH = "data/processed/features.parquet"
BATCH_SIZE = 100                     # Write to Parquet every 100 features

# Return calculation windows (in seconds)
RETURN_WINDOWS = [10, 30, 60]        # Calculate returns over 10s, 30s, 60s

# Volatility calculation windows (in seconds)
VOLATILITY_WINDOWS = [30, 60, 120]   # Calculate volatility over 30s, 60s, 120s

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Featurizer")

# ============================================================================
# FEATURIZER CLASS
# ============================================================================

class CryptoFeaturizer:
    """
    Real-time feature engineering consumer.
    
    Maintains a rolling buffer of ticks and calculates features
    for volatility prediction.
    """
    
    def __init__(self):
        """Initialize the featurizer with Kafka connections and buffer."""
        logger.info("🚀 Initializing CryptoFeaturizer...")
        
        # Rolling buffer to store recent ticks
        self.tick_buffer = deque(maxlen=BUFFER_SIZE)
        
        # Feature batch buffer for Parquet writes
        self.feature_batch = []
        
        # Message counter
        self.message_count = 0
        
        # Features written counter
        self.features_written = 0
        
        # Track last processed tick timestamp to avoid duplicates
        self.last_processed_timestamp = None
        
        # Initialize Kafka consumer
        self._init_consumer()
        
        # Initialize Kafka producer (for publishing features)
        self._init_producer()
        
        # Ensure output directory exists
        Path(PARQUET_PATH).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ Featurizer initialized successfully!")
        logger.info(f"📥 Consuming from topic: {INPUT_TOPIC}")
        logger.info(f"📤 Publishing to topic: {OUTPUT_TOPIC}")
        logger.info(f"💾 Saving features to: {PARQUET_PATH}")
        logger.info(f"📦 Batch size: {BATCH_SIZE} features")
    
    def _init_consumer(self):
        """Initialize Kafka consumer for reading raw ticks."""
        try:
            self.consumer = KafkaConsumer(
                INPUT_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='latest',  # Start from most recent messages
                enable_auto_commit=True,
                group_id='featurizer-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logger.info("✅ Kafka consumer connected")
        except Exception as e:
            logger.error(f"❌ Failed to initialize consumer: {e}")
            sys.exit(1)
    
    def _init_producer(self):
        """Initialize Kafka producer for publishing features."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info("✅ Kafka producer connected")
        except Exception as e:
            logger.error(f"❌ Failed to initialize producer: {e}")
            sys.exit(1)
    
    def calculate_return(self, window_seconds: int) -> float:
        """
        Calculate percentage return over a time window.
        
        Args:
            window_seconds: How far back to look (e.g., 10, 30, 60 seconds)
        
        Returns:
            Percentage return as decimal (e.g., 0.005 = 0.5%)
            Returns 0.0 if not enough data in buffer
        """
        if len(self.tick_buffer) < 2:
            return 0.0
        
        # Current (most recent) data
        current_tick = self.tick_buffer[-1]
        current_price = current_tick['price']
        current_time = current_tick['timestamp']
        
        # Search backwards for price from X seconds ago
        for tick in reversed(self.tick_buffer):
            time_diff = (current_time - tick['timestamp']).total_seconds()
            
            # Found a tick that's at least X seconds old
            if time_diff >= window_seconds:
                past_price = tick['price']
                
                # Calculate return: (current - past) / past
                if past_price > 0:  # Avoid division by zero
                    return_pct = ((current_price - past_price) / past_price) * 100
                    return return_pct
                else:
                    return 0.0
        
        # Window not filled yet (not enough historical data)
        return 0.0
    
    def calculate_volatility(self, window_seconds: int) -> float:
        """
        Calculate rolling volatility (standard deviation of returns) over a time window.
        
        Volatility measures price instability - how much prices "jump around".
        High volatility = risky, unpredictable price movements.
        Low volatility = stable, predictable price movements.
        
        Args:
            window_seconds: Time window to look back (e.g., 30, 60, 120 seconds)
        
        Returns:
            Standard deviation of returns as percentage (e.g., 0.15 = 0.15% volatility)
            Returns 0.0 if insufficient data (need at least 2 data points for std dev)
        
        Example:
            If prices over 60s were: $100k → $101k → $99.5k → $100.5k
            Returns would be: [+1.0%, -1.48%, +1.01%]
            Volatility (std dev) ≈ 1.2% (high volatility - prices jumping around!)
        """
        if len(self.tick_buffer) < 2:
            return 0.0
        
        current_time = self.tick_buffer[-1]['timestamp']
        
        # Collect all returns within the time window
        returns: List[float] = []
        
        # We need at least 2 ticks to calculate a return
        for i in range(len(self.tick_buffer) - 1, 0, -1):  # Iterate backwards
            tick = self.tick_buffer[i]
            prev_tick = self.tick_buffer[i - 1]
            
            # Check if this tick is within our time window
            time_diff = (current_time - tick['timestamp']).total_seconds()
            if time_diff > window_seconds:
                break  # Exceeded window, stop collecting
            
            # Calculate return between consecutive ticks
            if prev_tick['price'] > 0:
                tick_return = ((tick['price'] - prev_tick['price']) / prev_tick['price']) * 100
                returns.append(tick_return)
        
        # Calculate standard deviation (volatility)
        if len(returns) >= 2:  # Need at least 2 returns for std dev
            try:
                volatility = statistics.stdev(returns)
                return volatility
            except statistics.StatisticsError:
                # All returns are identical (zero variance)
                return 0.0
        else:
            # Not enough data points yet
            return 0.0
    
    def calculate_spread(self) -> float:
        """
        Calculate bid-ask spread as percentage of midprice.
        
        Spread measures market liquidity - how expensive trading is.
        - Narrow spread = High liquidity (easy to trade, many buyers/sellers)
        - Wide spread = Low liquidity (expensive to trade, few participants)
        
        Formula: ((ask - bid) / midprice) * 100
        
        Real-world analogy:
            Airport currency exchange: Spread = 10% (EXPENSIVE!)
            Major bank: Spread = 0.01% (CHEAP!)
        
        Returns:
            Spread as percentage (e.g., 0.002 = 0.002% spread)
            Returns 0.0 if no data available
        
        Example:
            bid = $102,888.00, ask = $102,888.10, midprice = $102,888.05
            spread = ((102888.10 - 102888.00) / 102888.05) * 100
                   = (0.10 / 102888.05) * 100
                   = 0.0001% (very tight spread - high liquidity!)
        """
        if len(self.tick_buffer) == 0:
            return 0.0
        
        current_tick = self.tick_buffer[-1]
        bid = current_tick['bid']
        ask = current_tick['ask']
        midprice = current_tick['price']
        
        if midprice > 0 and ask >= bid:  # Sanity check
            spread_pct = ((ask - bid) / midprice) * 100
            return spread_pct
        return 0.0
    
    def calculate_trade_intensity(self, window_seconds: int) -> float:
        """
        Calculate trade intensity (ticks per second) over a time window.
        
        Trade intensity measures market activity level:
        - Low intensity (<1 tick/sec) = Quiet market, low participation
        - Medium intensity (1-5 ticks/sec) = Normal activity
        - High intensity (>5 ticks/sec) = Active market, high participation
        
        High intensity often precedes or accompanies volatility spikes,
        indicating increased trader interest and potential price movements.
        
        Formula: (number_of_ticks_in_window / window_seconds)
        
        Example:
            window = 30 seconds
            ticks in last 30s = 150
            intensity = 150 / 30 = 5.0 ticks/second (normal activity)
        
        Args:
            window_seconds: Time window to analyze (e.g., 30, 60, 120)
            
        Returns:
            float: Ticks per second, 0.0 if insufficient data
        """
        if len(self.tick_buffer) < 2:
            return 0.0
        
        current_time = self.tick_buffer[-1]['timestamp']
        cutoff_time = current_time - timedelta(seconds=window_seconds)
        
        # Count ticks within the time window
        tick_count = 0
        for tick in reversed(self.tick_buffer):
            if tick['timestamp'] >= cutoff_time:
                tick_count += 1
            else:
                break  # Stop once we're outside the window
        
        # Calculate ticks per second
        if tick_count < 2:
            return 0.0
        
        intensity = tick_count / window_seconds
        return intensity
    
    def calculate_features(self) -> Dict[str, Any]:
        """
        Calculate all features from current buffer state.
        
        Uses the feature calculation time (not tick time) as the timestamp
        to ensure unique timestamps for each feature record.
        
        Returns:
            Dictionary with timestamp, price, and calculated features
        """
        if len(self.tick_buffer) == 0:
            return {}
        
        # Current tick data
        current_tick = self.tick_buffer[-1]
        
        # Calculate returns over different windows
        # Use current time for feature timestamp to avoid duplicates
        features = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'price': current_tick['price'],
            'bid': current_tick['bid'],
            'ask': current_tick['ask'],
        }
        
        # Add returns for each window
        for window in RETURN_WINDOWS:
            features[f'return_{window}s'] = self.calculate_return(window)
        
        # Add volatility for each window
        for window in VOLATILITY_WINDOWS:
            features[f'volatility_{window}s'] = self.calculate_volatility(window)
        
        # Add bid-ask spread (liquidity indicator)
        features['spread'] = self.calculate_spread()
        
        # Add trade intensity (market activity indicator)
        for window in VOLATILITY_WINDOWS:  # Use same windows as volatility: 30s, 60s, 120s
            features[f'intensity_{window}s'] = self.calculate_trade_intensity(window)
        
        return features
    
    def save_features_to_parquet(self):
        """
        Save accumulated features to Parquet file.
        
        Uses append mode to preserve historical data. Parquet provides:
        - Efficient columnar storage (10x smaller than CSV)
        - Fast analytics queries
        - Schema preservation
        - Compression (snappy)
        """
        if not self.feature_batch:
            return
        
        try:
            # Convert batch to DataFrame
            df = pd.DataFrame(self.feature_batch)
            
            # Check if file exists
            if Path(PARQUET_PATH).exists():
                # Append to existing file
                existing_df = pd.read_parquet(PARQUET_PATH)
                df = pd.concat([existing_df, df], ignore_index=True)
            
            # Write to Parquet with compression
            df.to_parquet(
                PARQUET_PATH,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            
            batch_size = len(self.feature_batch)
            self.features_written += batch_size
            logger.info(f"💾 Saved {batch_size} features to Parquet | Total: {self.features_written}")
            
            # Clear batch
            self.feature_batch = []
            
        except Exception as e:
            logger.error(f"❌ Error saving to Parquet: {e}")
    
    def publish_features_to_kafka(self, features: Dict[str, Any]):
        """
        Publish features to Kafka topic for real-time consumers.
        
        Args:
            features: Dictionary of calculated features
        """
        try:
            self.producer.send(OUTPUT_TOPIC, features)
        except Exception as e:
            logger.error(f"❌ Error publishing to Kafka: {e}")
    
    def process_tick(self, tick: Dict[str, Any]):
        """
        Process a single tick: update buffer and calculate features.
        
        Args:
            tick: Raw tick data from Coinbase (price, volume, timestamp, etc.)
        """
        self.message_count += 1
        
        # Extract key fields from tick
        try:
            price = float(tick['price'])
            timestamp = datetime.fromisoformat(tick['time'].replace('Z', '+00:00'))
            
            # Store structured data in buffer
            tick_data = {
                'timestamp': timestamp,
                'price': price,
                'bid': float(tick.get('best_bid', price)),
                'ask': float(tick.get('best_ask', price))
            }
            
            # Add to rolling buffer
            self.tick_buffer.append(tick_data)
            
        except (KeyError, ValueError) as e:
            logger.warning(f"⚠️ Error processing tick: {e}")
            return
        
        # Calculate features only if:
        # 1. We have enough data (at least 2 ticks)
        # 2. This is a NEW tick (different timestamp from last processed)
        if len(self.tick_buffer) >= 2:
            # Check if this is a new tick to avoid duplicate feature calculations
            current_timestamp = tick_data['timestamp']
            if self.last_processed_timestamp is None or current_timestamp != self.last_processed_timestamp:
                # Update tracking
                self.last_processed_timestamp = current_timestamp
                
                # Calculate features
                features = self.calculate_features()
                
                # Publish features to Kafka (real-time streaming)
                self.publish_features_to_kafka(features)
                
                # Add to batch for Parquet writing
                self.feature_batch.append(features)
                
                # Save batch to Parquet when threshold reached
                if len(self.feature_batch) >= BATCH_SIZE:
                    self.save_features_to_parquet()
                
                # Log features every 10 messages
                if self.message_count % 10 == 0:
                    logger.info(f"📊 Processed {self.message_count} ticks | Buffer: {len(self.tick_buffer)} | Batch: {len(self.feature_batch)}/{BATCH_SIZE}")
                    logger.info(f"💹 Price: ${price:,.2f} | Returns: 10s={features.get('return_10s', 0):.4f}%, 30s={features.get('return_30s', 0):.4f}%, 60s={features.get('return_60s', 0):.4f}%")
                    logger.info(f"📈 Volatility: 30s={features.get('volatility_30s', 0):.4f}%, 60s={features.get('volatility_60s', 0):.4f}%, 120s={features.get('volatility_120s', 0):.4f}%")
                    
                    # Display spread (liquidity indicator)
                    spread = features.get('spread', 0)
                    liquidity_status = 'High' if spread < 0.01 else 'Medium' if spread < 0.05 else 'Low'
                    logger.info(f"💰 Spread: {spread:.4f}% | Liquidity: {liquidity_status}")
                    
                    # Display trade intensity (activity indicator)
                    intensity_30s = features.get('intensity_30s', 0)
                    intensity_60s = features.get('intensity_60s', 0)
                    intensity_120s = features.get('intensity_120s', 0)
                    activity_status = 'Quiet' if intensity_30s < 1 else 'Normal' if intensity_30s < 5 else 'Active'
                    logger.info(f"⚡ Intensity: 30s={intensity_30s:.2f}, 60s={intensity_60s:.2f}, 120s={intensity_120s:.2f} ticks/sec")
                    logger.info(f"🎯 Market Activity: {activity_status}")
                    logger.info("=" * 80)
                    
                    # Show full feature dict on first calculation
                    if self.message_count == 10:
                        logger.info(f"📋 Sample features: {json.dumps(features, indent=2, default=str)}")
            else:
                # Duplicate tick timestamp - skip feature calculation
                if self.message_count % 100 == 0:
                    logger.debug(f"⏭️  Skipped duplicate tick at {current_timestamp}")
        else:
            # Not enough data yet
            if self.message_count % 10 == 0:
                logger.info(f"📊 Processed {self.message_count} ticks | Buffer: {len(self.tick_buffer)} (collecting initial data...)")
    
    def run(self):
        """
        Main processing loop.
        
        Continuously consumes messages from Kafka and processes them.
        """
        logger.info("🎬 Starting featurizer main loop...")
        logger.info("⏸️  Press Ctrl+C to stop")
        
        try:
            for message in self.consumer:
                tick = message.value
                self.process_tick(tick)
                
        except KeyboardInterrupt:
            logger.info("\n⏹️  Stopped by user")
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("🧹 Cleaning up...")
        
        # Save any remaining features in batch before shutdown
        if self.feature_batch:
            logger.info(f"💾 Saving final batch of {len(self.feature_batch)} features...")
            self.save_features_to_parquet()
        
        # Close Kafka connections
        if hasattr(self, 'consumer'):
            self.consumer.close()
            logger.info("✅ Consumer closed")
        
        if hasattr(self, 'producer'):
            self.producer.close()
            logger.info("✅ Producer closed")
        
        # Log final stats
        logger.info(f"📊 Final stats:")
        logger.info(f"   - Total ticks processed: {self.message_count}")
        logger.info(f"   - Features calculated: {self.features_written}")
        logger.info(f"   - Buffer size: {len(self.tick_buffer)}")
        logger.info("👋 Featurizer shutdown complete")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the featurizer."""
    logger.info("=" * 70)
    logger.info("🎯 Crypto Volatility Featurizer")
    logger.info("=" * 70)
    
    # Create and run featurizer
    featurizer = CryptoFeaturizer()
    featurizer.run()

if __name__ == "__main__":
    main()
