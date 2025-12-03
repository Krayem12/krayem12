import os
import logging

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class RedisManager:
    """
    مدير Redis بسيط لتخزين اتجاهات الرموز بشكل دائم.
    يعتمد على المتغيرات:
    REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB
    """
    def __init__(self):
        if redis is None:
            logger.warning("⚠️ مكتبة redis غير مثبتة - سيتم تعطيل التكامل مع Redis")
            self.client = None
            return

        host = os.getenv("REDIS_HOST")
        port = os.getenv("REDIS_PORT")
        password = os.getenv("REDIS_PASSWORD")
        db = os.getenv("REDIS_DB", "0")

        if not host or not port:
            logger.warning("⚠️ لم يتم ضبط REDIS_HOST/REDIS_PORT - سيتم تعطيل Redis")
            self.client = None
            return

        try:
            self.client = redis.Redis(
                host=host,
                port=int(port),
                password=password or None,
                db=int(db),
                decode_responses=True,
            )
            # اختبار الاتصال
            self.client.ping()
            logger.info("✅ تم الاتصال بـ Redis بنجاح")
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بـ Redis: {e}", exc_info=True)
            self.client = None

    def is_enabled(self) -> bool:
        return self.client is not None

    # --------- دوال خاصة بالاتجاه ---------
    def _trend_key(self, symbol: str) -> str:
        return f"trend:{symbol.upper()}"

    def _symbols_set_key(self) -> str:
        return "trend:symbols"

    def set_trend(self, symbol: str, trend: str) -> None:
        if not self.is_enabled():
            return
        key = self._trend_key(symbol)
        try:
            pipe = self.client.pipeline()
            pipe.set(key, trend)
            pipe.sadd(self._symbols_set_key(), symbol.upper())
            pipe.execute()
            logger.debug(f"💾 حفظ الاتجاه في Redis: {symbol.upper()} → {trend}")
        except Exception as e:
            logger.error(f"⚠️ خطأ في set_trend لـ {symbol}: {e}", exc_info=True)

    def get_trend(self, symbol: str):
        if not self.is_enabled():
            return None
        try:
            return self.client.get(self._trend_key(symbol))
        except Exception as e:
            logger.error(f"⚠️ خطأ في get_trend لـ {symbol}: {e}", exc_info=True)
            return None

    def clear_trend(self, symbol: str) -> None:
        if not self.is_enabled():
            return
        try:
            pipe = self.client.pipeline()
            pipe.delete(self._trend_key(symbol))
            pipe.srem(self._symbols_set_key(), symbol.upper())
            pipe.execute()
            logger.debug(f"🧹 حذف اتجاه {symbol.upper()} من Redis")
        except Exception as e:
            logger.error(f"⚠️ خطأ في clear_trend لـ {symbol}: {e}", exc_info=True)

    def get_all_trends(self):
        if not self.is_enabled():
            return {}
        try:
            symbols = self.client.smembers(self._symbols_set_key()) or set()
            trends = {}
            for sym in symbols:
                val = self.client.get(self._trend_key(sym))
                if val:
                    trends[sym] = val
            return trends
        except Exception as e:
            logger.error(f"⚠️ خطأ في get_all_trends: {e}", exc_info=True)
            return {}
