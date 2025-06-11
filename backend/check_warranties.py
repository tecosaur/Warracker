#!/usr/bin/env python3
"""
Check warranties and their expiration dates
"""

import sys
import os
from datetime import datetime, timedelta, date

# Add the backend directory to the path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

print("🔍 Checking Warranties and Expiration Dates")
print("=" * 60)

# Test imports
try:
    from backend.db_handler import get_db_connection, release_db_connection, init_db_pool, get_expiring_warranties
    print("✅ Database functions imported successfully")
except Exception as e:
    print(f"❌ Failed to import database functions: {e}")
    sys.exit(1)

# Test database connection
try:
    init_db_pool()
    print("✅ Database pool initialized")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)

# Check all warranties
conn = None
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n1. Checking all warranties...")
    cursor.execute("""
        SELECT 
            id, product_name, expiration_date, is_lifetime,
            purchase_date, user_id
        FROM warranties 
        ORDER BY expiration_date ASC
    """)
    
    warranties = cursor.fetchall()
    print(f"   Total warranties in database: {len(warranties)}")
    
    if warranties:
        print("\n   Sample warranties:")
        today = date.today()
        
        for i, warranty in enumerate(warranties[:10]):  # Show first 10
            warranty_id, product_name, exp_date, is_lifetime, purchase_date, user_id = warranty
            
            if is_lifetime:
                days_until_exp = "∞ (Lifetime)"
            elif exp_date:
                days_until_exp = (exp_date - today).days
                if days_until_exp < 0:
                    days_until_exp = f"{abs(days_until_exp)} days ago (EXPIRED)"
                else:
                    days_until_exp = f"{days_until_exp} days"
            else:
                days_until_exp = "No expiration date"
            
            print(f"     {i+1}. {product_name[:30]:<30} | Expires: {exp_date} | {days_until_exp}")
    
    # Check specifically for warranties expiring soon
    print("\n2. Checking warranties expiring in next 30 days...")
    
    today = date.today()
    next_30_days = today + timedelta(days=30)
    
    cursor.execute("""
        SELECT 
            id, product_name, expiration_date, user_id,
            (expiration_date - %s) as days_until_expiry
        FROM warranties 
        WHERE is_lifetime = false 
        AND expiration_date BETWEEN %s AND %s
        ORDER BY expiration_date ASC
    """, (today, today, next_30_days))
    
    expiring_soon = cursor.fetchall()
    print(f"   Warranties expiring in next 30 days: {len(expiring_soon)}")
    
    if expiring_soon:
        print("\n   Expiring warranties:")
        for warranty in expiring_soon:
            warranty_id, product_name, exp_date, user_id, days_until = warranty
            print(f"     • {product_name} (ID: {warranty_id}, User: {user_id}) - Expires: {exp_date} ({days_until.days} days)")
    
    # Test the get_expiring_warranties function specifically
    print("\n3. Testing get_expiring_warranties function...")
    
    for days in [1, 7, 14, 30, 60, 90]:
        try:
            expiring = get_expiring_warranties(days)
            print(f"   Expiring in {days} days: {len(expiring)} warranties")
            
            if expiring and days <= 30:  # Show details for shorter timeframes
                for w in expiring[:3]:  # Show first 3
                    print(f"     - {w.get('product_name', 'Unknown')} (expires: {w.get('expiration_date', 'Unknown')})")
        except Exception as e:
            print(f"   ❌ Error checking {days} days: {e}")
    
    cursor.close()
    
except Exception as e:
    print(f"❌ Error checking warranties: {e}")
    import traceback
    traceback.print_exc()
finally:
    if conn:
        release_db_connection(conn)

print("\n" + "=" * 60)
print("🎯 Summary:")
print("\nIf you see 0 warranties expiring soon, you have a few options:")
print("1. Add a test warranty with an upcoming expiration date")
print("2. Modify an existing warranty to expire soon")
print("3. Test with longer notification periods (like 60, 90 days)")
print("\nTo add a test warranty:")
print("- Go to your Warracker dashboard")
print("- Add a new warranty with expiration date in the next few days")
print("- Then test the Apprise notifications again") 