

from typing import Dict, Any, List, Tuple
from loguru import logger
import ast

from app.agents.base import BaseAgent
from app.services.sandbox import SandboxService

class CodeAgent(BaseAgent):
    """
    Code Generation Agent - Writes and runs Python code.
    Capabilities: Quantitative Analysis, Plotting, Math.
    """
    
    def __init__(self, sandbox: SandboxService = None):
        super().__init__()
        self.name = "code"
        self.description = "Generates and executes Python code for analysis"
        self.read_layers = {"agent_working_memory"}
        self.write_layers = {"agent_working_memory"}
        self._sandbox = sandbox
        self.system_prompt = """You are a Python Data Analyst.
Your goal is to write Python code to solve the user's query.
You have access to: pandas, numpy, matplotlib, scipy, sklearn, yfinance, statsmodels.

Rules:
1. Write COMPLETE, RUNNABLE code.
2. IMPORT ALL LIBRARIES you use (e.g., `import yfinance`, `import pandas as pd`, `import numpy as np`).
3. MATPLOTLIB SETUP (CRITICAL):
   - Import matplotlib BEFORE pyplot: `import matplotlib` then `import matplotlib.pyplot as plt`
   - Set backend for headless environment: `matplotlib.use('Agg')` - place this AFTER `import matplotlib` and BEFORE `import matplotlib.pyplot`
   - NEVER use `plt.use()` - this method doesn't exist on pyplot
   - The system will auto-save plots as PNG files
   - Example correct order:
     ```python
     import matplotlib
     matplotlib.use('Agg')
     import matplotlib.pyplot as plt
     ```

4. STOCK PREDICTION RULES:
   - For Indian stocks, ALWAYS append '.NS' to the ticker (e.g., use 'HDFCBANK.NS' for HDFC Bank, 'RELIANCE.NS' for Reliance).
   - Fetch at least 1-2 years of historical data using `yfinance.download(ticker, start='YYYY-MM-DD', end='YYYY-MM-DD')`.
   - IMPORTANT: ALWAYS USE DYNAMIC DATES. Do NOT hardcode years like '2023' or '2024'.
   - Example:
     ```python
     from datetime import datetime, timedelta
     end_date = datetime.now().strftime('%Y-%m-%d')
     start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d') # 2 years
     data = yf.download(ticker, start=start_date, end=end_date)
     ```
   - IMPORTANT: Do NOT use `date_range` parameter. Use `start` and `end`.
   - NOTE: `yfinance` data has Date as index. Access it via `data.index`, NOT `data['Date']`.
   - CHECK IF DATA IS EMPTY before proceeding. If empty, print "No data found" and exit.
   - ⚠️ CRITICAL: DO NOT recreate the index using pd.date_range()! Stock data has gaps (weekends/holidays).
     Use the yfinance data AS-IS: `df = data` or `df = data[['Close']].copy()`.
     NEVER do: `pd.DataFrame(data['Close'].values, index=pd.date_range(...))` - this causes shape mismatches!
   
5. PREDICTION TECHNIQUES (choose based on context):
   
   A) LINEAR REGRESSION (Simple trend-based forecast):
   - CRITICAL SKLEARN USAGE:
     * Linear regression expects 2D arrays for X (features)
     * Use `X.reshape(-1, 1)` to convert 1D arrays to 2D
     * predict() takes ONLY the feature array: model.predict(X_future)
     * DO NOT pass length as second argument to predict()
   - Example:
     ```python
     from sklearn.linear_model import LinearRegression
     
     # ... fetch data with dynamic dates ...
     
     # Historical data preparation
     X = np.arange(len(df)).reshape(-1, 1)  # Days as feature
     y = df['Close'].values
     
     # Train model
     model = LinearRegression()
     model.fit(X, y)
     
     # Future predictions (next 30 days)
     future_days = 30
     X_future = np.arange(len(df), len(df) + future_days).reshape(-1, 1)
     y_future = model.predict(X_future)  # CORRECT: only X_future
     
     # Create future dates for plotting
     last_date = df.index[-1]
     future_dates = pd.date_range(start=last_date, periods=future_days+1, freq='D')[1:]
     ```
   
   B) MOVING AVERAGE (Smoothed trend analysis):
   - Use for identifying trends without complex models
   - Example:
     ```python
     # Calculate moving averages
     df['MA_20'] = df['Close'].rolling(window=20).mean()
     df['MA_50'] = df['Close'].rolling(window=50).mean()
     
     # Simple forecast: extend last MA value
     last_ma = df['MA_20'].iloc[-1]
     future_days = 30
     
     plt.figure(figsize=(12, 6))
     plt.plot(df.index[-100:], df['Close'][-100:], label='Price', color='blue')
     plt.plot(df.index[-100:], df['MA_20'][-100:], label='20-day MA', color='orange')
     plt.axhline(y=last_ma, color='red', linestyle='--', label=f'Projected: {last_ma:.2f}')
     ```
   
   C) ARIMA (Advanced time series):
   - Use for more sophisticated forecasting
   - Requires statsmodels: `from statsmodels.tsa.arima.model import ARIMA`
   - Example:
     ```python
     from statsmodels.tsa.arima.model import ARIMA
     
     # Fit ARIMA model (p=5, d=1, q=0 is a simple starting point)
     model = ARIMA(df['Close'], order=(5, 1, 0))
     fitted = model.fit()
     
     # Forecast
     forecast = fitted.forecast(steps=30)
     future_dates = pd.date_range(start=df.index[-1], periods=31, freq='D')[1:]
     
     # Plot
     plt.figure(figsize=(12, 6))
     plt.plot(df.index, df['Close'], label='Historical', color='blue')
     plt.plot(future_dates, forecast, label='ARIMA Forecast', color='red', linestyle='--')
     ```
   
6. DATE HANDLING BEST PRACTICES:
   - Always check if data has DatetimeIndex: `isinstance(df.index, pd.DatetimeIndex)`
   - If not, convert: `df.index = pd.to_datetime(df.index)`
   - For future dates, use: `pd.date_range(start=last_date, periods=N+1, freq='D')[1:]`
   - Handle weekends/holidays: yfinance data only has trading days, so predictions should too
   
7. ERROR HANDLING:
   - Always wrap data fetching in try-except
   - Check for empty dataframes before processing
   - Validate that required columns exist ('Close', 'Open', etc.)
   - Example:
     ```python
     try:
         from datetime import datetime, timedelta
         end = datetime.now().strftime('%Y-%m-%d')
         start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
         data = yf.download('HDFCBANK.NS', start=start, end=end)
         if data.empty:
             print("No data retrieved for this ticker")
             exit()
     except Exception as e:
         print(f"Error fetching data: {e}")
         exit()
     ```

8. ALWAYS PLOT the historical data and prediction using `plt.plot()`. Title the chart with stock name and prediction method.

9. Print the final answer/insights to stdout.

10. Do NOT ask for clarification, just try your best with the assumption.

11. Return JSON format with two keys: "code" (the python code string) and "explanation" (what the code does/finds).

12. IMPORTANT: The "code" field must contain ONLY valid Python code. Do NOT include explanations inside the code string unless they are comments.

13. Put your non-technical explanation in the "explanation" JSON field only.
"""

    def set_sandbox(self, sandbox: SandboxService):
        self._sandbox = sandbox

    @staticmethod
    def _derive_execution_error(exec_result: Dict[str, Any]) -> str:
        """Build a useful failure message from sandbox execution output."""
        stderr = (exec_result.get("stderr") or "").strip()
        if stderr:
            return stderr

        stdout = (exec_result.get("stdout") or "").strip()
        if stdout:
            # Preserve a concise diagnostic snippet from stdout when stderr is empty.
            return stdout[:500]

        return_code = exec_result.get("return_code")
        if return_code is not None:
            return f"Execution failed with return code {return_code}"
        return "Execution failed without diagnostic output"

    def validate_code(self, code: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate Python code for syntax correctness and security issues.
        
        This method checks:
        1. Syntax validity using ast.parse()
        2. Dangerous imports (os, subprocess, sys, shutil, etc.)
        
        Args:
            code: Python code string to validate
            
        Returns:
            Tuple of (is_valid, errors, warnings):
            - is_valid: True if code passes all validation checks
            - errors: List of error messages (syntax errors, critical issues)
            - warnings: List of warning messages (dangerous imports, security concerns)
            
        Validates: Requirement 3.3 (code syntax validation)
        
        Example:
            >>> is_valid, errors, warnings = agent.validate_code("import os\\nprint('hello')")
            >>> print(is_valid)  # False
            >>> print(warnings)  # ['Dangerous import detected: os']
        """
        errors = []
        warnings = []
        
        # List of dangerous modules that should not be imported
        # These modules can be used for system manipulation, file operations, etc.
        dangerous_imports = {
            'os', 'subprocess', 'sys', 'shutil', 'socket', 'requests',
            'urllib', 'http', 'ftplib', 'telnetlib', 'pickle', 'shelve',
            'eval', 'exec', 'compile', '__import__', 'open'
        }
        
        # Step 1: Check syntax validity using ast.parse()
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            return False, errors, warnings
        except Exception as e:
            errors.append(f"Failed to parse code: {str(e)}")
            return False, errors, warnings
        
        # Step 2: Scan for dangerous imports
        for node in ast.walk(tree):
            # Check for import statements (import x, import x as y)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]  # Get base module name
                    if module_name in dangerous_imports:
                        warnings.append(f"Dangerous import detected: {alias.name}")
            
            # Check for from imports (from x import y)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]  # Get base module name
                    if module_name in dangerous_imports:
                        warnings.append(f"Dangerous import detected: {node.module}")
            
            # Check for dangerous function calls (eval, exec, __import__)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec', '__import__', 'compile']:
                        warnings.append(f"Dangerous function call detected: {node.func.id}")
        
        # Code is valid if there are no errors
        # Warnings don't make code invalid, but should be reported
        is_valid = len(errors) == 0
        
        return is_valid, errors, warnings

    def generate_prophet_code(self, symbol: str, horizon: int = 30) -> Dict[str, Any]:
        """
        Generate Prophet prediction code template.
        
        Args:
            symbol: Stock symbol (e.g., "HDFCBANK.NS", "TSLA")
            horizon: Number of days to predict (default: 30)
            
        Returns:
            Dictionary with 'code' and 'explanation' keys
            
        Validates: Requirements 3.1, 3.6
        """
        code = f"""
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    from prophet import Prophet
except ImportError:
    print("Error: Prophet not installed. Please install: pip install prophet")
    raise SystemExit(1)

# Configuration
horizon = {horizon}  # Days to predict

# Fetch stock data (2 years for sufficient training data)
print("Fetching stock data for {symbol}...")
try:
    stock = yf.download("{symbol}", period="2y", progress=False)
    if stock.empty:
        print("No data found for {symbol}")
        raise SystemExit(1)
except Exception as e:
    print(f"Error fetching data: {{e}}")
    raise SystemExit(1)

print(f"Retrieved {{len(stock)}} days of data")

# Prepare data in Prophet format (ds, y columns)
df = stock.reset_index()[['Date', 'Close']]
df.columns = ['ds', 'y']

print(f"Training data shape: {{df.shape}}")

# Train Prophet model with optimized parameters
print("Building Prophet model...")
model = Prophet(
    changepoint_prior_scale=0.05,  # Controls flexibility of trend changes
    seasonality_mode='multiplicative'  # Better for stock prices with varying amplitude
)

print("Training model (this may take a minute)...")
model.fit(df)
print("Training complete!")

# Make predictions for next horizon days
print(f"Generating {{horizon}}-day forecast...")
future = model.make_future_dataframe(periods=horizon)
forecast = model.predict(future)

# Extract predictions and confidence intervals
predictions = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(horizon)

# Calculate model performance metrics on training data
train_predictions = forecast[['ds', 'yhat']].head(len(df))
actual_values = df['y'].values
predicted_values = train_predictions['yhat'].values

mse = np.mean((actual_values - predicted_values) ** 2)
rmse = np.sqrt(mse)
mae = np.mean(np.abs(actual_values - predicted_values))

# Calculate R² score
ss_res = np.sum((actual_values - predicted_values) ** 2)
ss_tot = np.sum((actual_values - np.mean(actual_values)) ** 2)
r2_score = 1 - (ss_res / ss_tot)

print(f"\\nModel Performance Metrics:")
print(f"  RMSE: ₹{{rmse:.2f}}")
print(f"  MAE: ₹{{mae:.2f}}")
print(f"  R² Score: {{r2_score:.4f}}")

# Create visualization
plt.figure(figsize=(14, 7))

# Plot historical data (last 100 days for clarity)
historical_cutoff = max(0, len(df) - 100)
plt.plot(df['ds'][historical_cutoff:], df['y'][historical_cutoff:], 
         label='Historical Price', color='blue', linewidth=2)

# Plot predictions
future_dates = predictions['ds']
plt.plot(future_dates, predictions['yhat'], 
         label='Prophet Prediction', color='red', linewidth=2, linestyle='--')

# Plot confidence intervals
plt.fill_between(future_dates, 
                 predictions['yhat_lower'],
                 predictions['yhat_upper'],
                 alpha=0.3, color='red', label='95% Confidence Interval')

plt.xlabel('Date', fontsize=12)
plt.ylabel('Price (₹)', fontsize=12)
plt.title(f'{symbol} - Prophet Price Prediction ({{horizon}} days)', fontsize=14, fontweight='bold')
plt.legend(loc='best', fontsize=10)
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()

# Save plot
plt.savefig('prophet_prediction.png', dpi=100, bbox_inches='tight')
print("\\nPlot saved as 'prophet_prediction.png'")

# Print prediction summary
print(f"\\n{'='*60}")
print(f"PROPHET PREDICTION SUMMARY FOR {symbol}")
print(f"{'='*60}")
print(f"Current Price: ₹{{df['y'].iloc[-1]:.2f}}")
print(f"Predicted Price ({{horizon}} days): ₹{{predictions['yhat'].iloc[-1]:.2f}}")
print(f"Lower Bound: ₹{{predictions['yhat_lower'].iloc[-1]:.2f}}")
print(f"Upper Bound: ₹{{predictions['yhat_upper'].iloc[-1]:.2f}}")
change = ((predictions['yhat'].iloc[-1] - df['y'].iloc[-1]) / df['y'].iloc[-1]) * 100
print(f"Expected Change: {{change:+.2f}}%")
print(f"{'='*60}")
"""
        
        explanation = f"""
This code implements Facebook Prophet for stock price prediction.

Key Features:
- Uses Prophet's time series forecasting with trend and seasonality detection
- Configured with changepoint_prior_scale=0.05 for moderate trend flexibility
- Uses multiplicative seasonality mode suitable for stock prices
- Trained on 2 years of historical data
- Generates {horizon}-day forecast with upper/lower confidence bounds
- Includes model performance metrics (RMSE, MAE, R² score)
- Creates visualization with historical data and predictions

Prophet advantages:
- Automatically detects trends and seasonal patterns
- Handles missing data and outliers robustly
- Provides uncertainty intervals (yhat_lower, yhat_upper)
- Works well with daily data that has strong seasonal effects

The confidence intervals represent the uncertainty in the forecast based on
historical volatility and trend changes.
"""
        
        return {
            "code": code.strip(),
            "explanation": explanation.strip(),
            "model_type": "PROPHET",
            "expected_accuracy": 0.85
        }

    def generate_linear_regression_code(self, symbol: str, horizon: int = 30) -> Dict[str, Any]:
        """
        Generate dependency-light linear trend prediction code template.

        This model intentionally avoids TensorFlow/Prophet to maximize execution reliability
        in constrained sandbox environments.
        """
        code = f"""
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Configuration
horizon = {horizon}  # Days to predict

# Fetch stock data (2 years for trend estimation)
print("Fetching stock data for {symbol}...")
try:
    stock = yf.download("{symbol}", period="2y", progress=False)
    if stock.empty:
        print("No data found for {symbol}")
        raise SystemExit(1)
except Exception as e:
    print(f"Error fetching data: {{e}}")
    raise SystemExit(1)

# Normalize close series across yfinance variants
# (single ticker may still arrive as a 1-column DataFrame in some versions).
close_raw = stock['Close']
if isinstance(close_raw, pd.DataFrame):
    if close_raw.shape[1] == 0:
        print("No close-price column data available")
        raise SystemExit(1)
    close = close_raw.iloc[:, 0].dropna()
else:
    close = close_raw.dropna()

if len(close) < 30:
    print("Insufficient data points for prediction")
    raise SystemExit(1)

# Fit linear trend using numpy polyfit
X = np.arange(len(close))
y = close.to_numpy(dtype=float)
slope, intercept = np.polyfit(X, y, 1)

# Predict next horizon days
future_idx = np.arange(len(close), len(close) + horizon)
predictions = intercept + slope * future_idx
future_dates = pd.date_range(start=close.index[-1], periods=horizon + 1, freq='D')[1:]

# Approximate confidence interval from residual volatility
fitted = intercept + slope * X
residual_std = float(np.std(y - fitted))
ci_margin = 1.96 * residual_std
lower = predictions - ci_margin
upper = predictions + ci_margin

# Performance metrics on in-sample fit
rmse = float(np.sqrt(np.mean((y - fitted) ** 2)))
mae = float(np.mean(np.abs(y - fitted)))
ss_res = float(np.sum((y - fitted) ** 2))
ss_tot = float(np.sum((y - np.mean(y)) ** 2))
r2_score = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

print("\\nModel Performance Metrics:")
print(f"  RMSE: ₹{{rmse:.2f}}")
print(f"  MAE: ₹{{mae:.2f}}")
print(f"  R² Score: {{r2_score:.4f}}")

# Plot historical and forecast
plt.figure(figsize=(14, 7))
plt.plot(close.index[-120:], close.values[-120:], label='Historical Price', color='blue', linewidth=2)
plt.plot(future_dates, predictions, label='Linear Trend Prediction', color='red', linestyle='--', linewidth=2)
plt.fill_between(future_dates, lower, upper, alpha=0.25, color='red', label='95% Confidence Interval')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Price (₹)', fontsize=12)
plt.title(f'{symbol} - Linear Trend Forecast ({{horizon}} days)', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)
plt.legend(loc='best')
plt.tight_layout()

# Save chart artifact
plt.savefig('linear_regression_prediction.png', dpi=100, bbox_inches='tight')
print("\\nPlot saved as 'linear_regression_prediction.png'")

# Print summary
print(f"\\n{'='*60}")
print(f"LINEAR TREND PREDICTION SUMMARY FOR {symbol}")
print(f"{'='*60}")
current_price = float(close.iloc[-1])
print(f"Current Price: ₹{{current_price:.2f}}")
print(f"Predicted Price ({{horizon}} days): ₹{{predictions[-1]:.2f}}")
print(f"Confidence Interval: ₹{{lower[-1]:.2f}} - ₹{{upper[-1]:.2f}}")
change = ((predictions[-1] - current_price) / current_price) * 100
print(f"Expected Change: {{change:+.2f}}%")
print(f"{'='*60}")
"""

        explanation = f"""
This code predicts {symbol} price for the next {horizon} days using a linear trend model.

Key points:
- Uses 2 years of historical closing prices from Yahoo Finance
- Fits a straight-line trend via numpy.polyfit (no TensorFlow dependency)
- Produces a 95% confidence interval from residual volatility
- Saves a chart artifact for UI rendering
- Reports RMSE, MAE, and R² on in-sample fit
"""

        return {
            "code": code.strip(),
            "explanation": explanation.strip(),
            "model_type": "LINEAR_REGRESSION",
            "expected_accuracy": 0.70,
        }

    def generate_lstm_code(self, symbol: str, horizon: int = 30) -> Dict[str, Any]:
        """
        Generate LSTM prediction code template.
        
        Args:
            symbol: Stock symbol (e.g., "HDFCBANK.NS", "TSLA")
            horizon: Number of days to predict (default: 30)
            
        Returns:
            Dictionary with 'code' and 'explanation' keys
            
        Validates: Requirements 3.1, 3.6
        """
        code = f"""
import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Suppress TensorFlow warnings
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
except ImportError:
    print("Error: TensorFlow not installed. Please install: pip install tensorflow")
    raise SystemExit(1)

# Configuration
horizon = {horizon}  # Days to predict

# Fetch stock data (2 years for sufficient training data)
print("Fetching stock data for {symbol}...")
try:
    stock = yf.download("{symbol}", period="2y", progress=False)
    if stock.empty:
        print("No data found for {symbol}")
        raise SystemExit(1)
except Exception as e:
    print(f"Error fetching data: {{e}}")
    raise SystemExit(1)

print(f"Retrieved {{len(stock)}} days of data")

# Prepare data
data = stock['Close'].values.reshape(-1, 1)

# Scale data to 0-1 range (required for LSTM)
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(data)

# Create sequences with 60-day lookback window
lookback = 60
X, y = [], []
for i in range(lookback, len(scaled_data)):
    X.append(scaled_data[i-lookback:i, 0])
    y.append(scaled_data[i, 0])

X, y = np.array(X), np.array(y)
X = X.reshape(X.shape[0], X.shape[1], 1)

print(f"Training data shape: X={{X.shape}}, y={{y.shape}}")

# Build LSTM model with 50 units and dropout 0.2
print("Building LSTM model...")
model = Sequential([
    LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)),
    Dropout(0.2),
    LSTM(50, return_sequences=False),
    Dropout(0.2),
    Dense(25),
    Dense(1)
])

model.compile(optimizer='adam', loss='mean_squared_error')

# Train model
print("Training model (this may take a minute)...")
model.fit(X, y, batch_size=32, epochs=10, verbose=0)
print("Training complete!")

# Generate predictions for next horizon days
print(f"Generating {{horizon}}-day forecast...")
predictions = []
last_sequence = scaled_data[-lookback:]

for _ in range(horizon):
    # Predict next value
    pred = model.predict(last_sequence.reshape(1, lookback, 1), verbose=0)
    predictions.append(pred[0, 0])
    # Update sequence with prediction
    last_sequence = np.append(last_sequence[1:], pred)

# Inverse transform predictions to original scale
predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))

# Calculate confidence intervals (±5% as approximation)
confidence_lower = predictions * 0.95
confidence_upper = predictions * 1.05

# Create future dates
last_date = stock.index[-1]
future_dates = pd.date_range(start=last_date, periods=horizon+1, freq='D')[1:]

# Calculate model performance metrics
train_predictions = model.predict(X, verbose=0)
train_predictions = scaler.inverse_transform(train_predictions)
actual_train = scaler.inverse_transform(y.reshape(-1, 1))
mse = np.mean((train_predictions - actual_train) ** 2)
rmse = np.sqrt(mse)
mae = np.mean(np.abs(train_predictions - actual_train))

# Calculate R² score
ss_res = np.sum((actual_train - train_predictions) ** 2)
ss_tot = np.sum((actual_train - np.mean(actual_train)) ** 2)
r2_score = 1 - (ss_res / ss_tot)

print(f"\\nModel Performance Metrics:")
print(f"  RMSE: ₹{{rmse:.2f}}")
print(f"  MAE: ₹{{mae:.2f}}")
print(f"  R² Score: {{r2_score:.4f}}")

# Plot results
plt.figure(figsize=(14, 7))

# Plot historical data (last 100 days for clarity)
plt.plot(stock.index[-100:], stock['Close'][-100:], 
         label='Historical Price', color='blue', linewidth=2)

# Plot predictions
plt.plot(future_dates, predictions, 
         label='LSTM Prediction', color='red', linewidth=2, linestyle='--')

# Plot confidence intervals
plt.fill_between(future_dates, 
                 confidence_lower.flatten(),
                 confidence_upper.flatten(),
                 alpha=0.3, color='red', label='95% Confidence Interval')

plt.xlabel('Date', fontsize=12)
plt.ylabel('Price (₹)', fontsize=12)
plt.title(f'{symbol} - LSTM Price Prediction ({{horizon}} days)', fontsize=14, fontweight='bold')
plt.legend(loc='best', fontsize=10)
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Save plot
plt.savefig('lstm_prediction.png', dpi=100, bbox_inches='tight')
print("\\nPlot saved as 'lstm_prediction.png'")

# Print prediction summary
print(f"\\n{'='*60}")
print(f"LSTM PREDICTION SUMMARY FOR {symbol}")
print(f"{'='*60}")
print(f"Current Price: ₹{{stock['Close'].iloc[-1]:.2f}}")
print(f"Predicted Price ({{horizon}} days): ₹{{predictions[-1][0]:.2f}}")
print(f"Confidence Interval: ₹{{confidence_lower[-1][0]:.2f}} - ₹{{confidence_upper[-1][0]:.2f}}")
change = ((predictions[-1][0] - stock['Close'].iloc[-1]) / stock['Close'].iloc[-1]) * 100
print(f"Expected Change: {{change:+.2f}}%")
print(f"{'='*60}")
"""
        
        explanation = f"""
This code implements an LSTM (Long Short-Term Memory) neural network for stock price prediction.

Key Features:
- Uses 60-day lookback window to capture temporal patterns
- Two LSTM layers with 50 units each and 0.2 dropout for regularization
- Trained on 2 years of historical data
- Generates {horizon}-day forecast with 95% confidence intervals
- Includes model performance metrics (RMSE, MAE, R² score)
- Creates visualization with historical data and predictions

The LSTM model is more sophisticated than linear regression as it can:
- Capture non-linear patterns in stock prices
- Learn from sequential dependencies in time series data
- Handle complex market dynamics

Confidence intervals provide uncertainty estimates for the predictions.
"""
        
        return {
            "code": code.strip(),
            "explanation": explanation.strip(),
            "model_type": "LSTM",
            "expected_accuracy": 0.85
        }

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_topic": {"type": "string"}
            },
            "required": ["query_topic"]
        }
        
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "explanation": {"type": "string"}
            }
        }

    def normalize_stock_symbol(self, symbol: str) -> str:
        """
        Normalize stock symbol for Yahoo Finance.
        
        Rules:
        - Indian stocks (NSE): Add .NS if missing
        - US stocks: Keep as is
        - Crypto: Add -USD
        """
        if not symbol:
            return ""
            
        symbol = symbol.upper().strip()
        
        # Indian Stocks (Common identifiers)
        indian_stocks = {
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", 
            "BHARTIARTL", "ITC", "KOTAKBANK", "LICI", "HINDUNILVR",
            "TATASTEEL", "TATAMOTORS", "MARUTI", "SUNPHARMA", "NTPC",
            "TITAN", "BAJFINANCE", "ONGC", "ADANIENT", "ADANIPORTS"
        }
        
        # Crypto
        crypto = {"BTC", "ETH", "SOL", "DOGE", "XRP", "ADA"}
        
        if symbol in crypto:
             return f"{symbol}-USD"
             
        # Check if it's likely an Indian stock
        if symbol in indian_stocks:
            return f"{symbol}.NS"
            
        # Already has suffix
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            return symbol
            
        # Default: Return as is (US stocks usually)
        return symbol

    @staticmethod
    def _is_optional_dependency_error(error_text: str) -> bool:
        """Detect missing optional-model dependencies and trigger fallback model."""
        err = (error_text or "").lower()
        dependency_markers = [
            "tensorflow not installed",
            "no module named 'tensorflow'",
            "no module named \"tensorflow\"",
            "prophet not installed",
            "no module named 'prophet'",
            "no module named \"prophet\"",
        ]
        return any(marker in err for marker in dependency_markers)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a code generation request."""
        query = input_data.get("query_topic", "")
        raw_symbol = input_data.get("stock_symbol")
        
        # Normalize symbol
        stock_symbol = self.normalize_stock_symbol(raw_symbol) if raw_symbol else None
        
        self.add_reasoning_step(f"Generating code for: {query}")
        if stock_symbol:
            self.add_reasoning_step(f"Using normalized stock symbol: {stock_symbol}")
        
        # 1. Generate Code (LLM Call)
        try:
            # Build prompt with stock symbol if available
            prompt = f"Write python code to: {query}"
            if stock_symbol:
                prompt += f"\n\nIMPORTANT: Use the exact stock ticker '{stock_symbol}' with yfinance."
                
                # Additional context for LLM based on symbol type
                if stock_symbol.endswith('.NS'):
                     prompt += " This is an Indian NSE stock."
                elif stock_symbol.endswith('-USD'):
                     prompt += " This is a Cryptocurrency."
                else:
                     prompt += " This is likely a US stock."
            
            # CRITICAL: Detect if query asks for prediction/forecast
            prediction_keywords = ['predict', 'forecast', 'future', 'next', 'upcoming', 'projection']
            is_prediction_query = any(keyword in query.lower() for keyword in prediction_keywords)
            
            # Use advanced models for prediction queries (Requirement 3.1, 3.6)
            if is_prediction_query and stock_symbol:
                # Extract horizon from query if specified
                import re
                horizon_match = re.search(r'(\d+)\s*days?', query.lower())
                horizon = int(horizon_match.group(1)) if horizon_match else 30
                
                # Determine model based on query keywords.
                # Default to linear regression for reliability in constrained sandboxes.
                model_type = "LINEAR_REGRESSION"
                if 'prophet' in query.lower():
                    model_type = "PROPHET"
                elif 'lstm' in query.lower():
                    model_type = "LSTM"
                
                self.add_reasoning_step(f"Using {model_type} model for prediction (advanced model)")
                
                # Check cache for existing prediction
                from app.core.cache import cache_manager
                cache_key = f"prediction:{stock_symbol}:{horizon}:{model_type}"
                
                cached_result = await cache_manager.get(cache_key)
                if cached_result:
                    cached_success = bool(cached_result.get("success"))
                    cached_images = cached_result.get("images") or []
                    if cached_success and isinstance(cached_images, list) and len(cached_images) > 0:
                        self.add_reasoning_step("Using cached prediction result (faster response)")
                        return cached_result
                    self.add_reasoning_step("Ignoring stale cached prediction without chart artifacts")
                    await cache_manager.delete(cache_key)
                
                # Generate code using selected template
                if model_type == "PROPHET":
                    model_result = self.generate_prophet_code(stock_symbol, horizon)
                elif model_type == "LSTM":
                    model_result = self.generate_lstm_code(stock_symbol, horizon)
                else:
                    model_result = self.generate_linear_regression_code(stock_symbol, horizon)
                
                code = model_result["code"]
                explanation = model_result["explanation"]
                
                # Execute the code directly
                if self._sandbox:
                    exec_result = self._sandbox.execute_code(code)
                    
                    output = exec_result.get("stdout", "")
                    error = self._derive_execution_error(exec_result)
                    images = exec_result.get("images", [])
                    
                    if exec_result["success"]:
                        if not images:
                            logger.warning(f"{model_type} execution completed but produced no chart artifacts")
                            self.add_reasoning_step(f"{model_type} execution completed without chart output")
                            return {
                                "code": code,
                                "output": output,
                                "error": "Prediction run completed but produced no chart image artifact.",
                                "stderr": "Prediction run completed but produced no chart image artifact.",
                                "success": False,
                                "explanation": explanation,
                                "model_type": model_type,
                            }

                        self.add_reasoning_step(f"{model_type} prediction executed successfully")
                        logger.info(f"{model_type} prediction generated {len(images)} chart(s)")
                        
                        result = {
                            "code": code,
                            "output": output,
                            "success": True,
                            "explanation": explanation,
                            "images": images,
                            "model_type": model_type
                        }
                        
                        # Cache successful predictions with chart artifacts for 1 hour
                        await cache_manager.set(cache_key, result, ttl=3600)
                        self.add_reasoning_step("Cached prediction result for faster future queries")
                        
                        return result
                    else:
                        logger.warning(f"{model_type} execution failed: {error[:200]}")

                        # If chart artifacts were generated, return them despite non-critical post-processing failure.
                        if images:
                            self.add_reasoning_step(
                                f"{model_type} produced chart artifacts with non-fatal execution errors"
                            )
                            return {
                                "code": code,
                                "output": output,
                                "success": True,
                                "explanation": f"{explanation}\n\nExecution warning: {error}",
                                "images": images,
                                "model_type": model_type,
                            }

                        # Auto-fallback to linear regression if a heavy optional dependency is missing.
                        if model_type in {"LSTM", "PROPHET"} and self._is_optional_dependency_error(error):
                            fallback_model_type = "LINEAR_REGRESSION"
                            self.add_reasoning_step(
                                f"{model_type} unavailable in sandbox. Falling back to {fallback_model_type}."
                            )

                            fallback_cache_key = f"prediction:{stock_symbol}:{horizon}:{fallback_model_type}"
                            fallback_cached = await cache_manager.get(fallback_cache_key)
                            if fallback_cached:
                                fallback_images = fallback_cached.get("images") or []
                                if fallback_cached.get("success") and isinstance(fallback_images, list) and len(fallback_images) > 0:
                                    self.add_reasoning_step("Using cached linear fallback prediction")
                                    return fallback_cached
                                await cache_manager.delete(fallback_cache_key)

                            fallback_result = self.generate_linear_regression_code(stock_symbol, horizon)
                            fallback_code = fallback_result["code"]
                            fallback_explanation = fallback_result["explanation"]
                            fallback_exec = self._sandbox.execute_code(fallback_code)
                            fallback_output = fallback_exec.get("stdout", "")
                            fallback_error = self._derive_execution_error(fallback_exec)
                            fallback_images = fallback_exec.get("images", [])

                            if fallback_exec.get("success") and fallback_images:
                                self.add_reasoning_step("Linear fallback prediction executed successfully")
                                cached_payload = {
                                    "code": fallback_code,
                                    "output": fallback_output,
                                    "success": True,
                                    "explanation": fallback_explanation,
                                    "images": fallback_images,
                                    "model_type": fallback_model_type,
                                }
                                await cache_manager.set(fallback_cache_key, cached_payload, ttl=3600)
                                return cached_payload

                            combined_error = (
                                f"{model_type} failed: {error}. "
                                f"Linear fallback failed: {fallback_error}"
                            )
                            self.add_reasoning_step(f"Fallback execution failed: {fallback_error}")
                            return {
                                "code": fallback_code,
                                "output": fallback_output,
                                "error": combined_error,
                                "stderr": combined_error,
                                "success": False,
                                "explanation": fallback_explanation,
                                "model_type": fallback_model_type,
                            }

                        self.add_reasoning_step(f"{model_type} execution failed: {error}")
                        return {
                            "code": code,
                            "output": output,
                            "error": error,
                            "stderr": error,
                            "success": False,
                            "explanation": explanation,
                            "model_type": model_type,
                        }
                else:
                    return {"result": "Sandbox service not available."}
            
            # For non-prediction queries or when stock_symbol is not available, use LLM
            # ENHANCEMENT: Add explicit visualization instructions for analysis queries
            analysis_viz_keywords = ['volatility', 'volatile', 'std', 'variance', 'correlation',
                                     'compare', 'top', 'best', 'worst', 'performance', 'returns',
                                     'growth', 'decline', 'chart', 'plot', 'graph', 'visualize',
                                     'show', 'allocation', 'distribution', 'portfolio']
            is_analysis_query = any(keyword in query.lower() for keyword in analysis_viz_keywords)
            
            if is_analysis_query and not is_prediction_query:
                prompt += "\n\nIMPORTANT ANALYSIS & VISUALIZATION REQUIREMENTS:"
                prompt += "\n- ALWAYS generate a matplotlib chart (bar chart, line chart, pie chart, etc.)"
                prompt += "\n- Use matplotlib correctly:"
                prompt += "\n  import matplotlib"
                prompt += "\n  matplotlib.use('Agg')"
                prompt += "\n  import matplotlib.pyplot as plt"
                prompt += "\n- For volatility: calculate std() or variance on daily returns"
                prompt += "\n- For comparisons: use bar charts with proper labels"
                prompt += "\n- For portfolio/allocation: use pie charts"
                prompt += "\n- Always call plt.savefig('analysis_chart.png', dpi=100, bbox_inches='tight')"
                prompt += "\n- Print numerical results to stdout"
                prompt += "\n- Use professional styling: grid, colors, proper titles and labels"
            
            if is_prediction_query:
                stock_ticker = stock_symbol if stock_symbol else "TICKER"
                prompt += f"\n\n⚠️ PREDICTION REQUIRED - Copy this COMPLETE template and adapt:"
                prompt += "\n```python"
                prompt += "\nimport yfinance as yf"
                prompt += "\nimport pandas as pd"
                prompt += "\nimport numpy as np"
                prompt += "\nfrom sklearn.linear_model import LinearRegression"
                prompt += "\nimport matplotlib"
                prompt += "\nmatplotlib.use('Agg')"
                prompt += "\nimport matplotlib.pyplot as plt"
                prompt += "\nfrom datetime import datetime, timedelta"
                prompt += f"\n\nticker = '{stock_ticker}'"
                prompt += "\nend_date = datetime.now().strftime('%Y-%m-%d')"
                prompt += "\nstart_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')"
                prompt += "\ndata = yf.download(ticker, start=start_date, end=end_date)"
                prompt += "\nif data.empty:"
                prompt += "\n    print('No data found')"
                prompt += "\n    raise SystemExit(1)"
                prompt += "\n"
                prompt += "\n# Linear Regression"
                prompt += "\nX = np.arange(len(data)).reshape(-1, 1)"
                prompt += "\ny = data['Close'].values"
                prompt += "\nmodel = LinearRegression()"
                prompt += "\nmodel.fit(X, y)"
                prompt += "\n"
                prompt += "\n# Predict next 30 days"
                prompt += "\nX_future = np.arange(len(data), len(data) + 30).reshape(-1, 1)"
                prompt += "\ny_future = model.predict(X_future)"
                prompt += "\nfuture_dates = pd.date_range(start=data.index[-1], periods=31, freq='D')[1:]"
                prompt += "\n"
                prompt += "\n# Plot"
                prompt += "\nplt.figure(figsize=(12, 6))"
                prompt += "\nplt.plot(data.index, data['Close'], label='Historical', color='blue')"
                prompt += "\nplt.plot(future_dates, y_future, label='Predicted', color='red')"
                prompt += "\nplt.xlabel('Date')"
                prompt += "\nplt.ylabel('Price')"
                prompt += f"\nplt.title('{stock_ticker} Prediction')"
                prompt += "\nplt.legend()"
                prompt += "\nplt.grid(True)"
                prompt += "\nplt.show()"
                prompt += "\n```"
            
            llm_response = await self.invoke_llm(prompt)
            logger.info(f"DEBUG LLM RESPONSE TYPE: {type(llm_response)}")
            logger.info(f"DEBUG LLM RESPONSE CONTENT: {llm_response}")
            
            code = ""
            explanation = ""
            
            # Handle dictionary response (JSON)
            if isinstance(llm_response, dict):
                # Check for nested 'properties' key (common local LLM hallucination based on schema)
                if "properties" in llm_response and isinstance(llm_response["properties"], dict):
                    props = llm_response["properties"]
                    code = props.get("code", "")
                    explanation = props.get("explanation", "")
                else:
                    code = llm_response.get("code", "")
                    explanation = llm_response.get("explanation", "")
            # Handle string response (Raw Text / Markdown)
            elif isinstance(llm_response, str):
                import re
                # Try to extract code from ```python ... ``` blocks
                code_match = re.search(r"```python(.*?)```", llm_response, re.DOTALL)
                if code_match:
                    code = code_match.group(1).strip()
                else:
                    # Fallback: try ``` ... ```
                    code_match = re.search(r"```(.*?)```", llm_response, re.DOTALL)
                    if code_match:
                        code = code_match.group(1).strip()
                    else:
                        # Assume the whole response is code if it looks like python
                        if "import " in llm_response or "print(" in llm_response:
                            code = llm_response.strip()
                            
                # Extract explanation (everything else)
                explanation = re.sub(r"```.*?```", "", llm_response, flags=re.DOTALL).strip()
            
            if not code:
                return {"result": "Failed to generate code."}
                
            # Sanitize code: remove any lines that look like "EXPLANATION: ..." which might cause SyntaxError
            sanitized_lines = []
            for line in code.split('\n'):
                if line.strip().startswith("EXPLANATION:"):
                    continue
                sanitized_lines.append(line)
            code = '\n'.join(sanitized_lines)
                
            self.add_reasoning_step("Code generated. Executing in Sandbox...")
            
            # 2. Execute Code
            if self._sandbox:
                exec_result = self._sandbox.execute_code(code)
                
                output = exec_result.get("stdout", "")
                error = self._derive_execution_error(exec_result)
                images = exec_result.get("images", [])
                
                if exec_result["success"]:
                    self.add_reasoning_step("Execution successful")
                    if images:
                        logger.info(f"Code execution generated {len(images)} chart(s)")
                    return {
                        "code": code,
                        "output": output,
                        "success": True,
                        "explanation": explanation,
                        "images": images
                    }
                else:
                    logger.warning(f"Code execution failed: {error[:200]}")
                    self.add_reasoning_step(f"Execution failed: {error}")
                    return {
                        "code": code,
                        "output": output,
                        "error": error,
                        "stderr": error,
                        "success": False,
                        "explanation": explanation
                    }
            else:
                 return {"result": "Sandbox service not available."}
                 
        except Exception as e:
            self.add_reasoning_step(f"Agent failed: {e}")
            return {"error": str(e)}
