"""
Real-Time Data Service
Provides live market data with <2s latency using Yahoo Finance and Redis caching.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, asdict
import yfinance as yf
from loguru import logger
import redis.asyncio as aioredis
import json


@dataclass
class RealTimePrice:
    """Real-time stock price data"""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: str
    source: str = "YAHOO"
    latency_ms: int = 0


@dataclass
class PriceAlert:
    """Price alert configuration"""
    alert_id: str
    user_id: str
    symbol: str
    threshold_type: str  # "ABOVE" | "BELOW" | "CHANGE_PERCENT"
    threshold_value: float
    triggered: bool = False
    created_at: str = ""


class RealTimeDataService:
    """
    Aggregates and streams live market data.

    Features:
    - Subscribe to real-time stock updates
    - Yahoo Finance integration with 1-2s polling
    - Redis caching for latest prices
    - Market regime detection
    - Real-time alert triggering
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize the real-time data service.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.alerts: Dict[str, PriceAlert] = {}  # alert_id -> PriceAlert
        self.polling_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.poll_interval = 2  # seconds

    async def connect(self):
        """Connect to Redis and start background polling."""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("✅ Connected to Redis for real-time data")

            # Start background polling task
            self.is_running = True
            self.polling_task = asyncio.create_task(self._poll_prices())
            logger.info("✅ Started background price polling")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis and stop polling."""
        self.is_running = False

        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass

        if self.redis:
            await self.redis.close()
            logger.info("✅ Disconnected from Redis")

    async def subscribe_stock(self, symbol: str, callback: Callable) -> str:
        """
        Subscribe to real-time updates for a stock.

        Args:
            symbol: Stock symbol (e.g., "HDFCBANK.NS", "TSLA")
            callback: Async function called on price updates

        Returns:
            subscription_id: Unique subscription identifier
        """
        # Normalize symbol
        normalized_symbol = self._normalize_symbol(symbol)

        # Add callback to subscriptions
        if normalized_symbol not in self.subscriptions:
            self.subscriptions[normalized_symbol] = []

        self.subscriptions[normalized_symbol].append(callback)

        subscription_id = f"{normalized_symbol}_{len(self.subscriptions[normalized_symbol])}"

        logger.info(f"📊 Subscribed to {normalized_symbol} (ID: {subscription_id})")

        # Fetch initial price immediately
        try:
            price_data = await self.get_latest_price(normalized_symbol)
            if price_data:
                await callback(price_data)
        except Exception as e:
            logger.error(f"Failed to fetch initial price for {normalized_symbol}: {e}")

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Cancel a subscription.

        Args:
            subscription_id: Subscription ID from subscribe_stock

        Returns:
            True if unsubscribed successfully
        """
        # Parse subscription_id to get symbol
        parts = subscription_id.rsplit('_', 1)
        if len(parts) != 2:
            return False

        symbol = parts[0]

        if symbol in self.subscriptions and self.subscriptions[symbol]:
            # Remove the last callback (FIFO)
            self.subscriptions[symbol].pop()

            # Clean up empty subscription lists
            if not self.subscriptions[symbol]:
                del self.subscriptions[symbol]

            logger.info(f"📊 Unsubscribed from {symbol} (ID: {subscription_id})")
            return True

        return False

    async def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest cached price (< 2s old).

        Args:
            symbol: Stock symbol

        Returns:
            Price data dictionary or None if not available
        """
        if not self.redis:
            logger.warning("Redis not connected, fetching directly from Yahoo Finance")
            return await self._fetch_price_from_yahoo(symbol)

        try:
            # Try to get from cache first
            cache_key = f"price:{symbol}"
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                price_data = json.loads(cached_data)

                # Check if data is fresh (< 5 seconds old)
                timestamp = datetime.fromisoformat(price_data['timestamp'])
                age_seconds = (datetime.now() - timestamp).total_seconds()

                if age_seconds < 5:
                    logger.debug(f"📊 Cache hit for {symbol} (age: {age_seconds:.1f}s)")
                    return price_data

            # Cache miss or stale data - fetch fresh
            logger.debug(f"📊 Cache miss for {symbol}, fetching from Yahoo Finance")
            return await self._fetch_price_from_yahoo(symbol)

        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return None

    async def get_market_regime(self, index_symbol: str = "^NSEI") -> str:
        """
        Detect current market regime using moving averages.

        Args:
            index_symbol: Market index symbol (default: NIFTY 50)

        Returns:
            "BULL" | "BEAR" | "SIDEWAYS"
        """
        try:
            # Fetch historical data for moving average calculation
            ticker = yf.Ticker(index_symbol)
            hist = ticker.history(period="1y")

            if hist.empty or len(hist) < 200:
                logger.warning(f"Insufficient data for regime detection: {index_symbol}")
                return "SIDEWAYS"

            # Calculate 50-day and 200-day moving averages
            ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            current_price = hist['Close'].iloc[-1]

            # Determine regime
            if ma_50 > ma_200 and current_price > ma_50:
                regime = "BULL"
            elif ma_50 < ma_200 and current_price < ma_50:
                regime = "BEAR"
            else:
                regime = "SIDEWAYS"

            logger.info(f"📈 Market regime for {index_symbol}: {regime} (MA50: {ma_50:.2f}, MA200: {ma_200:.2f}, Price: {current_price:.2f})")

            # Check for regime change and trigger notification
            await self._check_regime_change(index_symbol, regime)

            # Cache the regime
            if self.redis:
                cache_key = f"regime:{index_symbol}"
                await self.redis.setex(
                    cache_key,
                    300,  # 5 minute TTL
                    regime
                )

            return regime

        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return "SIDEWAYS"

    async def _check_regime_change(self, index_symbol: str, new_regime: str):
        """
        Check if regime has changed and trigger notifications.

        Args:
            index_symbol: Market index symbol
            new_regime: Newly detected regime
        """
        if not self.redis:
            return

        try:
            # Get previous regime from cache
            cache_key = f"regime:{index_symbol}"
            previous_regime = await self.redis.get(cache_key)

            # If regime changed, trigger notification
            if previous_regime and previous_regime != new_regime:
                logger.warning(f"🚨 Market regime changed: {previous_regime} → {new_regime}")

                # Store regime change event
                event_key = f"regime_change:{index_symbol}:{int(time.time())}"
                event_data = {
                    "index": index_symbol,
                    "previous_regime": previous_regime,
                    "new_regime": new_regime,
                    "timestamp": datetime.now().isoformat()
                }
                await self.redis.setex(
                    event_key,
                    86400,  # 24 hour TTL
                    json.dumps(event_data)
                )

                # Trigger WebSocket broadcast (will be called by external code)
                # This is just storing the event for now

        except Exception as e:
            logger.error(f"Error checking regime change: {e}")

    async def monitor_regime_changes(self, index_symbol: str = "^NSEI", interval_seconds: int = 300):
        """
        Background task to monitor market regime changes.

        Args:
            index_symbol: Market index to monitor
            interval_seconds: Check interval (default: 5 minutes)
        """
        logger.info(f"📈 Starting regime monitoring for {index_symbol}")

        while self.is_running:
            try:
                await self.get_market_regime(index_symbol)
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                logger.info("🛑 Regime monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in regime monitoring: {e}")
                await asyncio.sleep(interval_seconds)

    async def create_price_alert(
        self,
        user_id: str,
        symbol: str,
        threshold_type: str,
        threshold_value: float
    ) -> str:
        """
        Create a price alert for a user.

        Args:
            user_id: User identifier
            symbol: Stock symbol
            threshold_type: "ABOVE" | "BELOW" | "CHANGE_PERCENT"
            threshold_value: Threshold value

        Returns:
            alert_id: Unique alert identifier
        """
        alert_id = f"{user_id}_{symbol}_{threshold_type}_{int(time.time())}"

        alert = PriceAlert(
            alert_id=alert_id,
            user_id=user_id,
            symbol=self._normalize_symbol(symbol),
            threshold_type=threshold_type,
            threshold_value=threshold_value,
            triggered=False,
            created_at=datetime.now().isoformat()
        )

        self.alerts[alert_id] = alert

        # Store in Redis for persistence
        if self.redis:
            cache_key = f"alert:{alert_id}"
            await self.redis.setex(
                cache_key,
                86400 * 30,  # 30 day TTL
                json.dumps(asdict(alert))
            )

        logger.info(f"🔔 Created alert {alert_id}: {symbol} {threshold_type} {threshold_value}")

        return alert_id

    async def remove_price_alert(self, alert_id: str) -> bool:
        """
        Remove a price alert.

        Args:
            alert_id: Alert identifier

        Returns:
            True if removed successfully
        """
        if alert_id in self.alerts:
            del self.alerts[alert_id]

            # Remove from Redis
            if self.redis:
                cache_key = f"alert:{alert_id}"
                await self.redis.delete(cache_key)

            logger.info(f"🔔 Removed alert {alert_id}")
            return True

        return False

    async def check_price_alerts(self, symbol: str, price_data: Dict[str, Any]):
        """
        Check if any alerts should be triggered for a symbol.

        Args:
            symbol: Stock symbol
            price_data: Current price data
        """
        current_price = price_data["price"]
        change_percent = price_data["change_percent"]

        triggered_alerts = []

        for alert_id, alert in list(self.alerts.items()):
            if alert.symbol != symbol or alert.triggered:
                continue

            should_trigger = False

            if alert.threshold_type == "ABOVE" and current_price >= alert.threshold_value:
                should_trigger = True
            elif alert.threshold_type == "BELOW" and current_price <= alert.threshold_value:
                should_trigger = True
            elif alert.threshold_type == "CHANGE_PERCENT":
                if abs(change_percent) >= abs(alert.threshold_value):
                    should_trigger = True

            if should_trigger:
                alert.triggered = True
                triggered_alerts.append(alert)

                logger.warning(f"🚨 Alert triggered: {alert_id} - {symbol} {alert.threshold_type} {alert.threshold_value}")

                # Store triggered alert event
                if self.redis:
                    event_key = f"alert_triggered:{alert_id}:{int(time.time())}"
                    event_data = {
                        "alert_id": alert_id,
                        "user_id": alert.user_id,
                        "symbol": symbol,
                        "threshold_type": alert.threshold_type,
                        "threshold_value": alert.threshold_value,
                        "current_price": current_price,
                        "change_percent": change_percent,
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.redis.setex(
                        event_key,
                        86400,  # 24 hour TTL
                        json.dumps(event_data)
                    )

        return triggered_alerts

    async def get_user_alerts(self, user_id: str) -> List[PriceAlert]:
        """
        Get all alerts for a user.

        Args:
            user_id: User identifier

        Returns:
            List of user's alerts
        """
        user_alerts = [
            alert for alert in self.alerts.values()
            if alert.user_id == user_id
        ]
        return user_alerts

    async def _poll_prices(self):
        """Background task to poll prices for subscribed stocks."""
        logger.info("🔄 Starting price polling loop")

        while self.is_running:
            try:
                if not self.subscriptions:
                    # No subscriptions, sleep and continue
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Fetch prices for all subscribed symbols
                symbols = list(self.subscriptions.keys())

                for symbol in symbols:
                    try:
                        price_data = await self._fetch_price_from_yahoo(symbol)

                        if price_data:
                            # Check price alerts
                            await self.check_price_alerts(symbol, price_data)

                            # Notify all callbacks for this symbol
                            callbacks = self.subscriptions.get(symbol, [])
                            for callback in callbacks:
                                try:
                                    await callback(price_data)
                                except Exception as e:
                                    logger.error(f"Error in callback for {symbol}: {e}")

                    except Exception as e:
                        logger.error(f"Error polling price for {symbol}: {e}")

                # Sleep before next poll
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                logger.info("🛑 Price polling cancelled")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _fetch_price_from_yahoo(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch current price from Yahoo Finance.

        Args:
            symbol: Stock symbol

        Returns:
            Price data dictionary
        """
        start_time = time.time()

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get current price and change
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            previous_close = info.get('previousClose', current_price)

            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0

            volume = info.get('volume', 0)

            latency_ms = int((time.time() - start_time) * 1000)

            price_data = {
                "symbol": symbol,
                "price": float(current_price),
                "change": float(change),
                "change_percent": float(change_percent),
                "volume": int(volume),
                "timestamp": datetime.now().isoformat(),
                "source": "YAHOO",
                "latency_ms": latency_ms
            }

            # Cache in Redis
            if self.redis:
                cache_key = f"price:{symbol}"
                await self.redis.setex(
                    cache_key,
                    300,  # 5 minute TTL
                    json.dumps(price_data)
                )

            logger.debug(f"📊 Fetched {symbol}: ₹{current_price:.2f} ({change_percent:+.2f}%) in {latency_ms}ms")

            return price_data

        except Exception as e:
            logger.error(f"Error fetching price from Yahoo Finance for {symbol}: {e}")
            return None

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize stock symbol to Yahoo Finance format.

        Args:
            symbol: Raw stock symbol or name

        Returns:
            Normalized symbol
        """
        # Common Indian stock mappings
        indian_stocks = {
            "HDFC": "HDFCBANK.NS",
            "HDFCBANK": "HDFCBANK.NS",
            "RELIANCE": "RELIANCE.NS",
            "TCS": "TCS.NS",
            "INFY": "INFY.NS",
            "INFOSYS": "INFY.NS",
            "ICICI": "ICICIBANK.NS",
            "ICICIBANK": "ICICIBANK.NS",
            "SBIN": "SBIN.NS",
            "SBI": "SBIN.NS",
            "WIPRO": "WIPRO.NS",
            "ITC": "ITC.NS",
            "BHARTIARTL": "BHARTIARTL.NS",
            "AIRTEL": "BHARTIARTL.NS",
            "KOTAKBANK": "KOTAKBANK.NS",
            "KOTAK": "KOTAKBANK.NS",
            "LT": "LT.NS",
            "AXISBANK": "AXISBANK.NS",
            "AXIS": "AXISBANK.NS",
            "MARUTI": "MARUTI.NS",
            "TATAMOTORS": "TATAMOTORS.NS",
            "TATA": "TATAMOTORS.NS",
        }

        # Convert to uppercase
        symbol_upper = symbol.upper().strip()

        # Check if it's a known Indian stock
        if symbol_upper in indian_stocks:
            return indian_stocks[symbol_upper]

        # If already has exchange suffix, return as-is
        if ".NS" in symbol_upper or ".BO" in symbol_upper:
            return symbol_upper

        # For US stocks, return as-is
        if symbol_upper in ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA"]:
            return symbol_upper

        # Default: assume NSE for Indian-looking symbols
        if len(symbol_upper) <= 10 and symbol_upper.isalpha():
            return f"{symbol_upper}.NS"

        return symbol_upper


# Global instance
_realtime_service: Optional[RealTimeDataService] = None


async def get_realtime_service() -> RealTimeDataService:
    """Get or create the global RealTimeDataService instance."""
    global _realtime_service

    if _realtime_service is None:
        _realtime_service = RealTimeDataService()
        await _realtime_service.connect()

    return _realtime_service
