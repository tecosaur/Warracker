#!/usr/bin/env python3
"""
Debug script for Apprise settings saving and loading
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

print("🔍 Debugging Apprise Settings")
print("=" * 50)

# Test imports
print("\n1. Testing imports...")
try:
    from backend.db_handler import get_db_connection, release_db_connection, init_db_pool, get_site_setting, update_site_setting
    print("✅ Database functions imported successfully")
except Exception as e:
    print(f"❌ Failed to import database functions: {e}")
    sys.exit(1)

# Test database connection
print("\n2. Testing database connection...")
try:
    init_db_pool()
    print("✅ Database pool initialized")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)

# Check if site_settings table exists
print("\n3. Checking site_settings table...")
conn = None
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'site_settings'
        )
    """)
    table_exists = cursor.fetchone()[0]
    print(f"✅ site_settings table exists: {table_exists}")
    
    if table_exists:
        # Check table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'site_settings'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print("   Table structure:")
        for column in columns:
            print(f"     {column[0]} ({column[1]}) {'NULL' if column[2] == 'YES' else 'NOT NULL'}")
        
        # Check existing Apprise settings
        cursor.execute("SELECT key, value FROM site_settings WHERE key LIKE 'apprise_%'")
        apprise_settings = cursor.fetchall()
        print(f"\n   Existing Apprise settings ({len(apprise_settings)}):")
        for key, value in apprise_settings:
            print(f"     {key} = {value}")
    
    cursor.close()
    
except Exception as e:
    print(f"❌ Error checking table: {e}")
    import traceback
    traceback.print_exc()
finally:
    if conn:
        release_db_connection(conn)

# Test setting and getting values
print("\n4. Testing setting and getting values...")
test_key = "apprise_test_debug"
test_value = "test_value_123"

try:
    # Test setting a value
    print(f"   Setting {test_key} = {test_value}")
    success = update_site_setting(test_key, test_value)
    print(f"   Update result: {success}")
    
    if success:
        # Test getting the value
        retrieved_value = get_site_setting(test_key, "default")
        print(f"   Retrieved value: {retrieved_value}")
        
        if retrieved_value == test_value:
            print("✅ Setting and getting values works correctly")
        else:
            print(f"❌ Value mismatch! Expected: {test_value}, Got: {retrieved_value}")
    else:
        print("❌ Failed to update setting")
        
except Exception as e:
    print(f"❌ Error testing set/get: {e}")
    import traceback
    traceback.print_exc()

# Test specific Apprise settings
print("\n5. Testing Apprise-specific settings...")
apprise_test_settings = {
    'apprise_enabled': 'true',
    'apprise_urls': 'test://url1,test://url2',
    'apprise_expiration_days': '7,30',
    'apprise_notification_time': '09:00',
    'apprise_title_prefix': '[Test Warracker]'
}

try:
    for key, value in apprise_test_settings.items():
        print(f"   Testing {key} = {value}")
        
        # Save the setting
        success = update_site_setting(key, value)
        if not success:
            print(f"   ❌ Failed to save {key}")
            continue
            
        # Retrieve the setting
        retrieved = get_site_setting(key, "NOT_FOUND")
        if retrieved == value:
            print(f"   ✅ {key} saved and retrieved correctly")
        else:
            print(f"   ❌ {key} mismatch! Expected: {value}, Got: {retrieved}")

except Exception as e:
    print(f"❌ Error testing Apprise settings: {e}")
    import traceback
    traceback.print_exc()

# Test database query directly for troubleshooting
print("\n6. Direct database query test...")
conn = None
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert test setting directly
    test_direct_key = "apprise_direct_test"
    test_direct_value = "direct_test_value"
    
    cursor.execute("""
        INSERT INTO site_settings (key, value, updated_at) 
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (key) 
        DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
    """, (test_direct_key, test_direct_value))
    
    conn.commit()
    print(f"   ✅ Direct insert of {test_direct_key} successful")
    
    # Query it back
    cursor.execute("SELECT value FROM site_settings WHERE key = %s", (test_direct_key,))
    result = cursor.fetchone()
    
    if result and result[0] == test_direct_value:
        print(f"   ✅ Direct query retrieved correct value: {result[0]}")
    else:
        print(f"   ❌ Direct query failed or wrong value: {result}")
    
    cursor.close()
    
except Exception as e:
    print(f"❌ Error with direct database test: {e}")
    import traceback
    traceback.print_exc()
finally:
    if conn:
        release_db_connection(conn)

# Check if API route works by simulating request
print("\n7. Testing API route simulation...")
try:
    # Import Flask components
    from backend.app import app
    
    with app.test_client() as client:
        # This won't work without proper authentication, but we can check if the route exists
        print("   ✅ App imported successfully - API routes should be available")
        
except Exception as e:
    print(f"❌ Error importing app: {e}")

print("\n" + "=" * 50)
print("🎯 Debug completed!")
print("\nIf settings are saving but not appearing in frontend:")
print("1. Check browser network tab for API errors")
print("2. Check if frontend is calling the correct API endpoints")
print("3. Verify authentication token is valid")
print("4. Check browser console for JavaScript errors") 