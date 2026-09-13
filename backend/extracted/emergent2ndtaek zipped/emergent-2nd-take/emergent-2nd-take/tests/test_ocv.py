import sys
import os
import pytest

# Add backend directory to path so we can import server
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_path)

# Mock environment variables required by server.py on import
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "mock_secret"

from server import get_retention_multiplier, get_engagement_multiplier, calculate_ocv

def test_retention_multipliers():
    # Boundary: <25% = 0.60
    assert get_retention_multiplier(24.9) == 0.60
    
    # Boundary: 25-39% = 0.80
    assert get_retention_multiplier(25.0) == 0.80
    assert get_retention_multiplier(39.0) == 0.80
    
    # Boundary: 40-54% = 0.95
    assert get_retention_multiplier(40.0) == 0.95
    assert get_retention_multiplier(54.0) == 0.95
    
    # Boundary: 55-69% = 1.00
    assert get_retention_multiplier(55.0) == 1.00
    assert get_retention_multiplier(69.0) == 1.00
    
    # Boundary: 70-84% = 1.15
    assert get_retention_multiplier(70.0) == 1.15
    assert get_retention_multiplier(84.0) == 1.15
    
    # Boundary: 85%+ = 1.30
    assert get_retention_multiplier(85.0) == 1.30
    assert get_retention_multiplier(90.0) == 1.30

def test_engagement_multipliers():
    # Boundary: <0.5% = 0.80
    assert get_engagement_multiplier(0.49) == 0.80
    
    # Boundary: 0.5-1% = 0.90
    assert get_engagement_multiplier(0.5) == 0.90
    assert get_engagement_multiplier(0.99) == 0.90
    
    # Boundary: 1-2.5% = 1.00
    assert get_engagement_multiplier(1.0) == 1.00
    assert get_engagement_multiplier(2.49) == 1.00
    
    # Boundary: 2.5-4% = 1.10
    assert get_engagement_multiplier(2.5) == 1.10
    assert get_engagement_multiplier(3.99) == 1.10
    
    # Boundary: 4-6% = 1.20
    assert get_engagement_multiplier(4.0) == 1.20
    assert get_engagement_multiplier(5.99) == 1.20
    
    # Boundary: 6%+ = 1.30
    assert get_engagement_multiplier(6.0) == 1.30
    assert get_engagement_multiplier(7.5) == 1.30

def test_calculate_ocv_categories():
    # Poor clip: views = 1000, retention = 15% (0.60), engagement = 0.3% (0.80) => 1000 * 0.60 * 0.80 = 480.0
    assert calculate_ocv(1000, 15.0, 0.3) == 480.0

    # Average clip: views = 5000, retention = 60% (1.00), engagement = 2.0% (1.00) => 5000 * 1.00 * 1.00 = 5000.0
    assert calculate_ocv(5000, 60.0, 2.0) == 5000.0

    # Good clip: views = 20000, retention = 75% (1.15), engagement = 3.5% (1.10) => 20000 * 1.15 * 1.10 = 25300.0
    assert calculate_ocv(20000, 75.0, 3.5) == 25300.0

    # Excellent clip: views = 100000, retention = 90% (1.30), engagement = 7.0% (1.30) => 100000 * 1.30 * 1.30 = 169000.0
    assert calculate_ocv(100000, 90.0, 7.0) == 169000.0
