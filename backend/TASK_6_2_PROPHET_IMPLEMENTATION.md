# Task 6.2: Prophet Prediction Template Implementation

## Summary

Successfully implemented Facebook Prophet prediction template in the Code Agent (`backend/app/agents/code.py`).

## Implementation Details

### 1. Prophet Code Generation Method

Added `generate_prophet_code()` method to the `CodeAgent` class with the following features:

**Configuration:**
- `changepoint_prior_scale=0.05` - Controls flexibility of trend changes (moderate flexibility)
- `seasonality_mode='multiplicative'` - Better for stock prices with varying amplitude

**Data Preparation:**
- Fetches 2 years of historical data using yfinance
- Converts data to Prophet format with `ds` (date) and `y` (value) columns
- Handles empty datasets with proper error messages

**Model Training:**
- Creates Prophet model with optimized parameters
- Trains on historical data
- Generates predictions for specified horizon (default: 30 days)

**Predictions:**
- Generates forecast with `yhat` (predicted value)
- Includes confidence intervals: `yhat_lower` and `yhat_upper`
- Calculates model performance metrics (RMSE, MAE, R² score)

**Visualization:**
- Creates matplotlib plot with historical data (last 100 days)
- Plots predictions with confidence interval shading
- Saves as PNG file with proper formatting
- Uses headless backend (`matplotlib.use('Agg')`)

**Output:**
- Prints model performance metrics
- Displays prediction summary with current price, predicted price, bounds, and expected change

### 2. Integration with Code Agent

Updated the `process()` method to support both LSTM and Prophet models:

**Model Selection Logic:**
- Detects prediction queries using keywords (predict, forecast, future, etc.)
- Checks for explicit model preference in query ('prophet' or 'lstm')
- Defaults to LSTM if no preference specified
- Extracts prediction horizon from query (e.g., "30 days")

**Execution Flow:**
1. Detect if query is a prediction request
2. Determine which model to use (LSTM or Prophet)
3. Generate code using appropriate template
4. Execute code in sandbox
5. Return results with model type, output, and images

### 3. Code Structure

```python
def generate_prophet_code(self, symbol: str, horizon: int = 30) -> Dict[str, Any]:
    """
    Generate Prophet prediction code template.
    
    Returns:
        {
            "code": "...",           # Complete Python code
            "explanation": "...",    # Human-readable explanation
            "model_type": "PROPHET", # Model identifier
            "expected_accuracy": 0.85
        }
    """
```

## Testing

### Unit Tests (test_prophet_prediction.py)

Created comprehensive unit tests covering:

1. **Basic Functionality:**
   - Code generation returns correct structure
   - All required imports present
   - Data format preparation (ds, y columns)

2. **Configuration:**
   - changepoint_prior_scale=0.05 is set
   - seasonality_mode='multiplicative' is set

3. **Features:**
   - Confidence intervals (yhat_lower, yhat_upper)
   - Visualization generation and saving
   - Custom horizon support
   - Stock symbol usage
   - Error handling

4. **Quality:**
   - Performance metrics calculation
   - Output summary generation
   - Explanation content
   - Syntax validity
   - Matplotlib backend setup

5. **Comparison:**
   - Prophet vs LSTM distinction

**Results:** 15/15 tests passed ✅

### Integration Tests (test_prophet_integration.py)

Created integration tests covering:

1. Prophet library availability check
2. Code execution validation
3. Required components verification
4. Error handling structure
5. Multiple stock symbols support
6. Different prediction horizons

**Results:** 6/6 tests passed ✅

### Total Test Coverage

**21/21 tests passed** ✅

## Requirements Validation

### Requirement 3.1: Advanced Models
✅ **Validated** - Prophet model is used instead of simple linear regression for stock predictions

### Requirement 3.6: Confidence Intervals
✅ **Validated** - Predictions include:
- Upper bound (yhat_upper)
- Lower bound (yhat_lower)
- Model performance metrics (RMSE, MAE, R² score)

## Key Features

1. **Automatic Trend Detection:** Prophet automatically detects trends and seasonal patterns
2. **Robust Handling:** Handles missing data and outliers well
3. **Uncertainty Quantification:** Provides confidence intervals based on historical volatility
4. **Performance Metrics:** Includes RMSE, MAE, and R² score for model evaluation
5. **Visualization:** Creates professional charts with confidence interval shading
6. **Error Handling:** Comprehensive error handling for data fetching and processing

## Usage Example

```python
from app.agents.code import CodeAgent

agent = CodeAgent()

# Generate Prophet prediction code
result = agent.generate_prophet_code("HDFCBANK.NS", horizon=30)

print(result["code"])        # Complete Python code
print(result["explanation"]) # Human-readable explanation
print(result["model_type"])  # "PROPHET"
```

## Model Selection in Queries

Users can specify which model to use:

- **"Predict AAPL stock price using Prophet for 30 days"** → Uses Prophet
- **"Predict AAPL stock price using LSTM for 30 days"** → Uses LSTM
- **"Predict AAPL stock price for 30 days"** → Uses LSTM (default)

## Prophet vs LSTM

| Feature | Prophet | LSTM |
|---------|---------|------|
| Training Time | Fast (~1 minute) | Slower (~2-3 minutes) |
| Complexity | Moderate | High |
| Seasonality | Automatic detection | Manual feature engineering |
| Trend Changes | Automatic (changepoints) | Learned from data |
| Interpretability | High | Low |
| Best For | Daily data with seasonality | Complex patterns, large datasets |

## Files Modified

1. **backend/app/agents/code.py**
   - Added `generate_prophet_code()` method
   - Updated `process()` method for model selection

## Files Created

1. **backend/test_prophet_prediction.py** - Unit tests (15 tests)
2. **backend/test_prophet_integration.py** - Integration tests (6 tests)
3. **backend/TASK_6_2_PROPHET_IMPLEMENTATION.md** - This summary document

## Next Steps

Task 6.2 is now complete. The Prophet prediction template is fully implemented and tested.

Suggested next steps:
- Task 6.3: Write property test for advanced model usage (Property 8)
- Task 6.4: Implement code syntax validation
- Continue with remaining tasks in Epic 6

## Notes

- Prophet library must be installed: `pip install prophet`
- The implementation follows the same pattern as the LSTM template for consistency
- Both models can coexist and be selected based on user preference or query context
- The code is production-ready with proper error handling and validation
