-- Create user_preferences table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'user_preferences'
    ) THEN
        CREATE TABLE user_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
            default_view VARCHAR(10) NOT NULL DEFAULT 'grid',
            theme VARCHAR(10) NOT NULL DEFAULT 'light',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Add user_id constraint if users table exists
        IF EXISTS (
            SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
        ) THEN
            -- First drop the constraint if it already exists (to avoid errors)
            BEGIN
                ALTER TABLE user_preferences DROP CONSTRAINT IF EXISTS user_preferences_user_id_fkey;
            EXCEPTION WHEN OTHERS THEN
                -- Ignore errors
            END;
            
            -- Add the foreign key constraint
            ALTER TABLE user_preferences 
            ADD CONSTRAINT user_preferences_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        END IF;

        -- Add index for faster user lookups
        CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
    END IF;
END $$; 