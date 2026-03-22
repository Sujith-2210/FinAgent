# Infrastructure Setup

This document describes the infrastructure components set up for the FinAgent production upgrade.

## Dependencies Installed

### Caching
- **redis>=5.0.0**: In-memory data structure store for caching
- **aioredis>=2.0.1**: Async Redis client for Python

### Property-Based Testing
- **hypothesis>=6.92.0**: Property-based testing framework

### Privacy & Encryption
- **pyfhel>=3.4.0**: Homomorphic encryption library (Optional - requires OpenMP, may fail on macOS)

### Machine Learning
- **tensorflow>=2.15.0**: Deep learning framework for LSTM models
- **prophet>=1.1.5**: Time series forecasting library

### Monitoring
- **prometheus-client>=0.19.0**: Prometheus instrumentation library for Python

## Redis Setup

Redis is installed and running as a background service via Homebrew.

### Start Redis
```bash
brew services start redis
```

### Stop Redis
```bash
brew services stop redis
```

### Check Redis Status
```bash
redis-cli ping
# Should return: PONG
```

### Redis Configuration
- Default port: 6379
- Default host: localhost
- Configuration file: /opt/homebrew/etc/redis.conf

## Prometheus Metrics

The FastAPI application now exposes Prometheus metrics at the `/metrics` endpoint.

### Available Metrics
- `finagent_requests_total`: Total request count (labeled by method, endpoint, status)
- `finagent_request_duration_seconds`: Request latency histogram (labeled by method, endpoint)

### Access Metrics
```bash
curl http://localhost:8000/metrics
```

## Notes

### pyfhel Installation
The `pyfhel` package requires OpenMP and may fail to build on macOS. It has been marked as optional in requirements.txt. If homomorphic encryption features are needed, you may need to:

1. Install OpenMP via Homebrew:
   ```bash
   brew install libomp
   ```

2. Set environment variables before installing:
   ```bash
   export CC=clang
   export CXX=clang++
   export LDFLAGS="-L/opt/homebrew/opt/libomp/lib"
   export CPPFLAGS="-I/opt/homebrew/opt/libomp/include"
   pip install pyfhel
   ```

Alternatively, homomorphic encryption features can be implemented using alternative libraries or deferred to a later phase.

## Verification

To verify all dependencies are installed correctly:

```bash
cd backend
source venv/bin/activate
python -c "import redis; import hypothesis; import tensorflow; import prophet; import prometheus_client; print('✅ All dependencies OK')"
```

## Next Steps

1. Implement caching layer using Redis (Task 8)
2. Set up property-based tests using Hypothesis (Task 28)
3. Implement LSTM/Prophet models using TensorFlow/Prophet (Task 6)
4. Configure Prometheus scraping and Grafana dashboards (Task 16)
