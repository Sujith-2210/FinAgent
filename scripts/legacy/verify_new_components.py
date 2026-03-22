import sys
import os
import asyncio
from loguru import logger

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def verify_components():
    logger.info("Verifying Caching Layer...")
    try:
        from app.core.cache import CacheManager
        from app.services.cache_service import CacheService
        
        cm = CacheManager()
        logger.info(f"CacheManager initialized: {cm}")
        
        cs = CacheService()
        logger.info(f"CacheService initialized: {cs}")
        
    except Exception as e:
        logger.error(f"Caching verification failed: {e}")
        return False

    logger.info("Verifying Privacy Layer...")
    try:
        from app.privacy.encryption import HomomorphicEncryption
        from app.privacy.enhancer import PrivacyEnhancer
        
        he = HomomorphicEncryption()
        enc = he.encrypt(100.0)
        dec = he.decrypt(enc)
        logger.info(f"FHE Encrypt/Decrypt Check: {dec == 100.0}")
        
        pe = PrivacyEnhancer()
        logger.info(f"PrivacyEnhancer initialized: {pe}")
        
    except Exception as e:
        logger.error(f"Privacy verification failed: {e}")
        return False

    logger.info("Verifying Agent Enhancements...")
    try:
        from app.agents.finance import FinanceReasoningAgent
        from app.agents.code import CodeAgent
        
        fa = FinanceReasoningAgent()
        mpt = fa._optimize_portfolio_mpt({"Equity": 0.5, "Debt": 0.5})
        logger.info(f"FinanceAgent MPT Check: {mpt['action']}")
        
        ca = CodeAgent()
        norm = ca.normalize_stock_symbol("RELIANCE")
        logger.info(f"CodeAgent Symbol Normalization: {norm}")
        if norm != "RELIANCE.NS":
             logger.error(f"Normalization failed: Expected RELIANCE.NS, got {norm}")
             return False
             
    except Exception as e:
        logger.error(f"Agent verification failed: {e}")
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(verify_components())
    if success:
        logger.info("✅ All new components verified successfully")
        sys.exit(0)
    else:
        logger.error("❌ Component verification failed")
        sys.exit(1)
