"""
Replay Mode: Read historical ticks from Parquet and publish to Kafka.

This script simulates live market data by reading saved features from Parquet
and publishing them to Kafka's ticks.raw topic. This enables:
- Testing without live market connection
- Faster development iteration
- Reproducible testing with same data
- Offline development

Usage:
    python3 scripts/replay.py

Features:
- Reads from data/processed/features.parquet
- Publishes to ticks.raw topic (same as ws_ingest.py)
- Simulates real-time with configurable speed multiplier
- Preserves original timestamps
- Can replay subset or full dataset

Author: Feature Engineering Team
Date: November 7, 2025
"""

import sys
import time
import logging
import pandas as pd
from pathlib import Path
from kafka import KafkaProducer
import json
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
KAFKA_TOPIC = 'ticks.raw'

# Replay configuration
PARQUET_PATH = "data/processed/features.parquet"
SPEED_MULTIPLIER = 10.0  # Replay 10x faster than real-time (0 = as fast as possible)
MAX_TICKS = None  # Set to number to limit replay (None = replay all)


class TickReplayer:
    """Replays historical ticks from Parquet to Kafka."""
    
    def __init__(self):
        """Initialize Kafka producer and load data."""
        logger.info("🔄 Initializing Tick Replayer...")
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
        logger.info(f"✅ Connected to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
        
        # Load Parquet data
        self.df = self.load_parquet()
        self.total_ticks = len(self.df)
        self.ticks_published = 0
        
    def load_parquet(self) -> pd.DataFrame:
        """
        Load features from Parquet file.
        
        Returns:
            DataFrame with features sorted by timestamp
        """
        parquet_path = Path(PARQUET_PATH)
        
        if not parquet_path.exists():
            logger.error(f"❌ Parquet file not found: {PARQUET_PATH}")
            logger.error("💡 Run featurizer first to generate features!")
            sys.exit(1)
        
        logger.info(f"📂 Loading data from: {PARQUET_PATH}")
        df = pd.read_parquet(parquet_path)
        
        # Sort by timestamp (ensure chronological order)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Limit ticks if specified
        if MAX_TICKS:
            df = df.head(MAX_TICKS)
        
        logger.info(f"✅ Loaded {len(df)} ticks")
        logger.info(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        logger.info(f"   Columns: {list(df.columns)}")
        
        return df
    
    def create_tick_message(self, row: pd.Series) -> dict:
        """
        Convert DataFrame row to tick message format.
        
        This recreates the original tick format that ws_ingest.py produces,
        so featurizer.py processes it the same way.
        
        Args:
            row: DataFrame row with feature data
            
        Returns:
            Tick message dict matching ws_ingest.py format
        """
        # Extract base tick data (ignore calculated features)
        tick = {
            'type': 'ticker',
            'product_id': 'BTC-USD',
            'price': str(row['price']),  # Convert to string (like Coinbase)
            'time': row['timestamp'],
            'best_bid': str(row['bid']),
            'best_ask': str(row['ask']),
            # Add metadata for replay tracking
            'replay': True,
            'replay_index': int(row.name) if hasattr(row, 'name') else 0
        }
        
        return tick
    
    def publish_tick(self, tick: dict):
        """
        Publish tick to Kafka topic.
        
        Args:
            tick: Tick message dict
        """
        try:
            self.producer.send(KAFKA_TOPIC, tick)
            self.ticks_published += 1
        except Exception as e:
            logger.error(f"❌ Error publishing tick: {e}")
            raise
    
    def calculate_delay(self, current_idx: int) -> float:
        """
        Calculate delay to next tick based on timestamp difference.
        
        Args:
            current_idx: Current row index
            
        Returns:
            Delay in seconds (adjusted by speed multiplier)
        """
        if current_idx >= len(self.df) - 1:
            return 0.0  # Last tick, no delay
        
        # Get timestamps
        current_time = pd.to_datetime(self.df.iloc[current_idx]['timestamp'])
        next_time = pd.to_datetime(self.df.iloc[current_idx + 1]['timestamp'])
        
        # Calculate real-time difference
        real_delay = (next_time - current_time).total_seconds()
        
        # Apply speed multiplier (0 = as fast as possible)
        if SPEED_MULTIPLIER == 0:
            return 0.0
        
        replay_delay = real_delay / SPEED_MULTIPLIER
        
        return max(0.0, replay_delay)  # No negative delays
    
    def replay(self):
        """
        Main replay loop: read ticks and publish to Kafka.
        """
        logger.info("🎬 Starting replay...")
        logger.info(f"   Speed: {SPEED_MULTIPLIER}x real-time" if SPEED_MULTIPLIER > 0 else "   Speed: Maximum (no delay)")
        logger.info(f"   Topic: {KAFKA_TOPIC}")
        logger.info(f"   Ticks: {self.total_ticks}")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            for idx, row in self.df.iterrows():
                # Create and publish tick
                tick = self.create_tick_message(row)
                self.publish_tick(tick)
                
                # Log progress every 1000 ticks
                if self.ticks_published % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = self.ticks_published / elapsed if elapsed > 0 else 0
                    progress = (self.ticks_published / self.total_ticks) * 100
                    
                    logger.info(
                        f"📊 Progress: {self.ticks_published}/{self.total_ticks} "
                        f"({progress:.1f}%) | Rate: {rate:.1f} ticks/sec"
                    )
                
                # Calculate delay to next tick (simulate timing)
                delay = self.calculate_delay(idx)
                if delay > 0:
                    time.sleep(delay)
            
            # Final flush
            self.producer.flush()
            
            # Summary
            elapsed = time.time() - start_time
            avg_rate = self.ticks_published / elapsed if elapsed > 0 else 0
            
            logger.info("=" * 60)
            logger.info("🎉 Replay complete!")
            logger.info(f"   Total ticks: {self.ticks_published}")
            logger.info(f"   Duration: {elapsed:.1f} seconds")
            logger.info(f"   Average rate: {avg_rate:.1f} ticks/sec")
            
        except KeyboardInterrupt:
            logger.info("\n⚠️  Replay interrupted by user")
        except Exception as e:
            logger.error(f"❌ Error during replay: {e}")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("🧹 Cleaning up...")
        self.producer.close()
        logger.info("✅ Kafka producer closed")


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("🔄 TICK REPLAY MODE")
    logger.info("=" * 60)
    
    # Check Parquet file exists
    if not Path(PARQUET_PATH).exists():
        logger.error(f"❌ Parquet file not found: {PARQUET_PATH}")
        logger.error("💡 Run featurizer first to collect data:")
        logger.error("   1. Start Kafka: cd docker && docker compose up -d")
        logger.error("   2. Start ingestion: python3 scripts/ws_ingest.py")
        logger.error("   3. Start featurizer: python3 features/featurizer.py")
        logger.error("   4. Wait for features to accumulate")
        logger.error("   5. Then run replay: python3 scripts/replay.py")
        sys.exit(1)
    
    # Create and run replayer
    replayer = TickReplayer()
    replayer.replay()


if __name__ == "__main__":
    main()
