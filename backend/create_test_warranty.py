#!/usr/bin/env python3
"""
Create a test warranty for testing Apprise notifications
"""

import sys
import os
from datetime import datetime, timedelta, date

# Add the backend directory to the path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

print("🧪 Creating Test Warranty for Apprise Notifications")
print("=" * 60)

# Test imports
try:
    from backend.db_handler import get_db_connection, release_db_connection, init_db_pool
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

# Get the first user ID to assign the test warranty to
conn = None
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get a user ID (preferably admin)
    cursor.execute("SELECT id FROM users WHERE is_admin = true LIMIT 1")
    admin_user = cursor.fetchone()
    
    if not admin_user:
        cursor.execute("SELECT id FROM users LIMIT 1")
        any_user = cursor.fetchone()
        if any_user:
            user_id = any_user[0]
            print(f"📋 Using first available user ID: {user_id}")
        else:
            print("❌ No users found in database")
            sys.exit(1)
    else:
        user_id = admin_user[0]
        print(f"📋 Using admin user ID: {user_id}")
    
    # Create test warranties with different expiration dates
    today = date.today()
    test_warranties = [
        {
            'product_name': 'Test Product - Expires in 5 days',
            'expiration_date': today + timedelta(days=5),
            'purchase_date': today - timedelta(days=360),
            'vendor': 'Test Vendor',
            'warranty_type': 'Extended',
            'notes': 'Test warranty for Apprise notification testing'
        },
        {
            'product_name': 'Test Product - Expires in 15 days',
            'expiration_date': today + timedelta(days=15),
            'purchase_date': today - timedelta(days=350),
            'vendor': 'Test Vendor',
            'warranty_type': 'Standard',
            'notes': 'Test warranty for Apprise notification testing'
        },
        {
            'product_name': 'Test Product - Expires in 25 days',
            'expiration_date': today + timedelta(days=25),
            'purchase_date': today - timedelta(days=340),
            'vendor': 'Test Vendor',
            'warranty_type': 'Manufacturer',
            'notes': 'Test warranty for Apprise notification testing'
        }
    ]
    
    print(f"\n📝 Creating {len(test_warranties)} test warranties...")
    
    created_warranties = []
    
    for warranty in test_warranties:
        try:
            cursor.execute("""
                INSERT INTO warranties (
                    product_name, purchase_date, expiration_date, 
                    user_id, vendor, warranty_type, notes, 
                    is_lifetime, warranty_duration_years, warranty_duration_months, warranty_duration_days
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                warranty['product_name'],
                warranty['purchase_date'],
                warranty['expiration_date'],
                user_id,
                warranty['vendor'],
                warranty['warranty_type'],
                warranty['notes'],
                False,  # not lifetime
                1,      # warranty_duration_years
                0,      # warranty_duration_months
                0       # warranty_duration_days
            ))
            
            warranty_id = cursor.fetchone()[0]
            created_warranties.append({
                'id': warranty_id,
                'name': warranty['product_name'],
                'expires': warranty['expiration_date']
            })
            
            print(f"   ✅ Created: {warranty['product_name']} (ID: {warranty_id}, expires: {warranty['expiration_date']})")
            
        except Exception as e:
            print(f"   ❌ Failed to create {warranty['product_name']}: {e}")
    
    # Commit the changes
    conn.commit()
    cursor.close()
    
    print(f"\n🎉 Successfully created {len(created_warranties)} test warranties!")
    
    if created_warranties:
        print("\n📅 Test warranty schedule:")
        for warranty in created_warranties:
            days_until = (warranty['expires'] - today).days
            print(f"   • {warranty['name']} - {days_until} days from now ({warranty['expires']})")
        
        print("\n🧪 To test notifications:")
        print("1. Go to your Warracker admin settings")
        print("2. Click 'Send Expiration Notifications' in the Apprise section")
        print("3. Check your Discord/notification service for messages")
        print("\n🧹 To clean up test data later:")
        print("- Go to your warranty dashboard and delete the test warranties")
        print("- Or run a cleanup script")
    
except Exception as e:
    print(f"❌ Error creating test warranties: {e}")
    import traceback
    traceback.print_exc()
    if conn:
        conn.rollback()
finally:
    if conn:
        release_db_connection(conn)

print("\n" + "=" * 60)
print("🎯 Test warranties created! Now you can test Apprise notifications.") 