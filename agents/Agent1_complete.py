import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models.data_models import DemandForecast
from utils.groq_helper import groq
from utils.logger import log_info, log_error
import pandas as pd
import numpy as np
import json
from datetime import datetime
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')


class DataHarmonizerAndForecaster(BaseAgent):
    """Standalone agent combining harmonization, cleaning, and forecasting."""
    def __init__(self):
        super().__init__(
            name="Agent 1 - Data Harmonizer & Demand Forecaster",
            role="End-to-End Data Processing and Forecasting",
            goal="Transform messy data into accurate demand forecasts",
            backstory="Complete data pipeline specialist"
        )
    
    def _load_and_filter_data(self, file_path: str, item_code: str):
        """Load CSV and filter by item code."""
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"error": f"Failed to load file: {str(e)}"}
        
        if 'item_code' not in df.columns:
            return {"error": "CSV must have 'item_code' column"}
        
        df_item = df[df['item_code'] == item_code].copy()
        
        if df_item.empty:
            available = df['item_code'].unique()[:10].tolist()
            return {"error": f"Item '{item_code}' not found. Available: {available}"}
        
        return df_item

    def execute(self, item_code: str, file_path: str = None):
        """Load, clean, and forecast demand for specific item."""
        self.log_start(f"Running forecast for {item_code}")
        
        # STEP 1 & 2: Load CSV and find item by item_code
        if file_path is None:
            file_path = 'data/historical_orders.csv' # Default path if not provided
        
        df_item_result = self._load_and_filter_data(file_path, item_code)
        if isinstance(df_item_result, dict) and "error" in df_item_result:
            return df_item_result
        df_item = df_item_result
        
        # STEP 3: Clean data
        df_item = df_item.dropna(subset=['order_date', 'quantity_ordered'])
        df_item['order_date'] = pd.to_datetime(df_item['order_date'])
        df_item = df_item[df_item['quantity_ordered'] > 0]
        
        # STEP 4: Aggregate by month
        df_monthly = df_item.groupby(df_item['order_date'].dt.to_period('M'))['quantity_ordered'].sum().reset_index()
        df_monthly.columns = ['month', 'quantity']
        df_monthly['month'] = df_monthly['month'].dt.to_timestamp()
        
        if len(df_monthly) < 6:
            return {"error": f"Need 6+ months, found {len(df_monthly)} months"}
        
        # STEP 5: Forecast
        ts_data = df_monthly.set_index('month')['quantity']
        
        # Test models
        split_idx = int(len(ts_data) * 0.8)
        train = ts_data[:split_idx]
        test = ts_data[split_idx:]
        
        models = []
        
        # Model 1: Moving Average
        ma_pred = [train[-3:].mean()] * len(test)
        ma_mape = mean_absolute_percentage_error(test, ma_pred) * 100
        models.append({"name": "Moving Average", "mape": ma_mape})
        
        # Model 2: Exponential Smoothing
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            es_model = ExponentialSmoothing(train, trend='add', seasonal=None).fit()
            es_pred = es_model.forecast(steps=len(test))
            es_mape = mean_absolute_percentage_error(test, es_pred) * 100
            models.append({"name": "Exponential Smoothing", "mape": es_mape})
        except:
            models.append({"name": "Exponential Smoothing", "mape": 999.0})
        
        # Model 3: Linear Regression
        try:
            X_train = np.arange(len(train)).reshape(-1, 1)
            X_test = np.arange(len(train), len(train) + len(test)).reshape(-1, 1)
            lr_model = LinearRegression().fit(X_train, train.values)
            lr_pred = lr_model.predict(X_test)
            lr_mape = mean_absolute_percentage_error(test, lr_pred) * 100
            models.append({"name": "Linear Regression", "mape": lr_mape})
        except:
            models.append({"name": "Linear Regression", "mape": 999.0})
        
        # Pick best model
        best = min(models, key=lambda x: x['mape'])
        
        # Final forecast
        if best['name'] == "Moving Average":
            forecast_qty = int(ts_data[-3:].mean())
        elif best['name'] == "Exponential Smoothing":
            try:
                from statsmodels.tsa.holtwinters import ExponentialSmoothing
                final_model = ExponentialSmoothing(ts_data, trend='add', seasonal=None).fit()
                forecast_qty = int(final_model.forecast(steps=1).iloc[0])
            except:
                forecast_qty = int(ts_data.mean())
        else:  # Linear Regression
            try:
                X_all = np.arange(len(ts_data)).reshape(-1, 1)
                X_next = np.array([[len(ts_data)]])
                final_lr = LinearRegression().fit(X_all, ts_data.values)
                forecast_qty = int(final_lr.predict(X_next)[0])
            except:
                forecast_qty = int(ts_data.mean())
        
        forecast_qty = max(0, forecast_qty)
        
        # Detect trend
        slope = np.polyfit(np.arange(len(ts_data)), ts_data.values, 1)[0]
        threshold = ts_data.mean() * 0.05
        if slope > threshold:
            trend = "increasing"
        elif slope < -threshold:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Confidence
        if best['mape'] < 10:
            confidence = 0.95
        elif best['mape'] < 15:
            confidence = 0.85
        elif best['mape'] < 20:
            confidence = 0.75
        else:
            confidence = 0.65
        
        # Create forecast object
        forecast = DemandForecast(
            item_code=item_code,
            predicted_demand=forecast_qty,
            confidence=confidence,
            model_used=best['name'],
            historical_average=int(ts_data.mean()),
            trend=trend,
            seasonality_detected=False
        )
        
        self.log_complete("Forecast", f"{forecast_qty} units ({best['name']}, {best['mape']:.1f}% MAPE)")
        
        return {
            "forecast": forecast,
            "model_comparison": models,
            "best_model": best,
            "context": {
                "months_of_data": len(ts_data),
                "avg_monthly_demand": int(ts_data.mean()),
                "trend": trend
            }
        }


if __name__ == "__main__":
    print("="*60)
    print("Testing Agent 1 - STANDALONE VERSION")
    print("="*60)
    
    agent1 = DataHarmonizerAndForecaster()
    
    print("\nTest 1: ITM001")
    result = agent1.execute("ITM001")
    
    if result.get('error'):
        print(f"ERROR: {result['error']}")
    else:
        fc = result['forecast']
        print(f"Predicted: {fc.predicted_demand} units")
        print(f"Model: {fc.model_used}")
        print(f"Confidence: {fc.confidence*100:.0f}%")
        print(f"Trend: {fc.trend}")
        
        print("\nModels tested:")
        for m in result['model_comparison']:
            print(f"  {m['name']}: {m['mape']:.1f}% MAPE")
    
    print("\n" + "="*60)
    print("DONE!")
    print("="*60)
    