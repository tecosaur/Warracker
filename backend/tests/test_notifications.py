import unittest
from datetime import date, timedelta
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to allow importing app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the functions from app.py
from app import get_expiring_warranties, format_expiration_email, send_expiration_notifications

class TestWarrantyNotifications(unittest.TestCase):
    
    @patch('app.get_db_connection')
    def test_get_expiring_warranties(self, mock_get_db_connection):
        """Test that get_expiring_warranties correctly queries expiring warranties."""
        # Set up mock connection and cursor
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_db_connection.return_value = mock_conn
        
        # Set up mock cursor fetchall response
        today = date.today()
        mock_cur.fetchall.return_value = [
            # Format: email, first_name, product_name, expiration_date, expiring_soon_days
            ('user1@example.com', 'John', 'Laptop', today + timedelta(days=10), 30),
            ('user2@example.com', 'Jane', 'Phone', today + timedelta(days=20), 30),
            ('user3@example.com', None, 'Tablet', today + timedelta(days=5), 30)
        ]
        
        # Call the function
        result = get_expiring_warranties()
        
        # Verify the SQL query is correct (simplified check)
        self.assertTrue(mock_cur.execute.called)
        args = mock_cur.execute.call_args[0]
        self.assertIn('warranties w', args[0])  # Check if the query includes the warranties table
        self.assertIn('users u', args[0])       # Check if the query includes the users table
        self.assertIn('user_preferences up', args[0])  # Check if the query includes user_preferences
        
        # Verify the result
        self.assertEqual(len(result), 3)  # Should return 3 warranties
        
        # Check the first warranty
        self.assertEqual(result[0]['email'], 'user1@example.com')
        self.assertEqual(result[0]['first_name'], 'John')
        self.assertEqual(result[0]['product_name'], 'Laptop')
        self.assertEqual(result[0]['expiration_date'], (today + timedelta(days=10)).strftime('%Y-%m-%d'))
        
        # Check that null first_name is handled correctly
        self.assertEqual(result[2]['first_name'], 'User')  # Default value for NULL
        
        # Verify the connection is released
        self.assertTrue(mock_conn.close.called)
    
    def test_format_expiration_email(self):
        """Test that format_expiration_email correctly formats the email."""
        # Test data
        user = {
            'first_name': 'John',
            'email': 'john@example.com'
        }
        
        warranties = [
            {
                'product_name': 'Laptop',
                'expiration_date': '2023-12-31'
            },
            {
                'product_name': 'Phone',
                'expiration_date': '2023-11-30'
            }
        ]
        
        # Call the function
        email = format_expiration_email(user, warranties)
        
        # Verify the email
        self.assertEqual(email['Subject'], 'Warracker: Upcoming Warranty Expirations')
        self.assertEqual(email['From'], 'notifications@warracker.com')
        self.assertEqual(email['To'], 'john@example.com')
        
        # Check both parts exist (plain text and HTML)
        self.assertEqual(len(email.get_payload()), 2)
        
        # Check content of plain text part
        plain_text = email.get_payload(0).get_payload()
        self.assertIn('Hello John', plain_text)
        self.assertIn('Laptop (expires on 2023-12-31)', plain_text)
        self.assertIn('Phone (expires on 2023-11-30)', plain_text)
        
        # Check content of HTML part
        html = email.get_payload(1).get_payload()
        self.assertIn('Hello John', html)
        self.assertIn('Laptop', html)
        self.assertIn('2023-12-31', html)
        self.assertIn('Phone', html)
        self.assertIn('2023-11-30', html)
    
    @patch('app.get_expiring_warranties')
    @patch('smtplib.SMTP')
    def test_send_expiration_notifications(self, mock_smtp, mock_get_expiring_warranties):
        """Test that send_expiration_notifications correctly sends emails."""
        # Mock environment variables
        with patch.dict(os.environ, {
            'SMTP_HOST': 'test.example.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@example.com',
            'SMTP_PASSWORD': 'test_password'
        }):
            # Set up mock SMTP instance
            mock_smtp_instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
            
            # Set up mock for expiring warranties
            mock_get_expiring_warranties.return_value = [
                {
                    'email': 'user1@example.com',
                    'first_name': 'John',
                    'product_name': 'Laptop',
                    'expiration_date': '2023-12-31'
                },
                {
                    'email': 'user1@example.com',
                    'first_name': 'John',
                    'product_name': 'Phone',
                    'expiration_date': '2023-11-30'
                },
                {
                    'email': 'user2@example.com',
                    'first_name': 'Jane',
                    'product_name': 'Tablet',
                    'expiration_date': '2023-10-15'
                }
            ]
            
            # Call the function
            send_expiration_notifications()
            
            # Verify SMTP is initialized with correct parameters
            mock_smtp.assert_called_once_with('test.example.com', 587)
            
            # Verify starttls and login are called
            self.assertTrue(mock_smtp_instance.starttls.called)
            mock_smtp_instance.login.assert_called_once_with('test@example.com', 'test_password')
            
            # Verify sendmail is called twice (for two different users)
            self.assertEqual(mock_smtp_instance.sendmail.call_count, 2)
            
            # Verify first call to sendmail (for user1 with 2 warranties)
            from_email, to_email, msg = mock_smtp_instance.sendmail.call_args_list[0][0]
            self.assertEqual(from_email, 'test@example.com')
            self.assertEqual(to_email, 'user1@example.com')
            self.assertIn('Laptop', msg)
            self.assertIn('Phone', msg)
            
            # Verify second call to sendmail (for user2 with 1 warranty)
            from_email, to_email, msg = mock_smtp_instance.sendmail.call_args_list[1][0]
            self.assertEqual(from_email, 'test@example.com')
            self.assertEqual(to_email, 'user2@example.com')
            self.assertIn('Tablet', msg)

if __name__ == '__main__':
    unittest.main() 