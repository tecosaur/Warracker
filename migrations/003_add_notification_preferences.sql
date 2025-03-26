-- Add notification preferences columns to user_preferences table

-- Check if notification_frequency column exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'user_preferences' AND column_name = 'notification_frequency'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN notification_frequency VARCHAR(10) NOT NULL DEFAULT 'daily';
    END IF;
END $$;

-- Check if notification_time column exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'user_preferences' AND column_name = 'notification_time'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN notification_time VARCHAR(5) NOT NULL DEFAULT '09:00';
    END IF;
END $$;

-- Add indexes for the new columns
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'user_preferences' AND indexname = 'idx_user_preferences_notification'
    ) THEN
        CREATE INDEX idx_user_preferences_notification ON user_preferences(notification_frequency, notification_time);
    END IF;
END $$; 