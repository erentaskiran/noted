import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

pool = None

async def init_db():
    """Initializes the database connection pool and creates the tables if they don't exist."""
    global pool
    if not DATABASE_URL:
        print("Error: DATABASE_URL not found in environment variables.")
        return

    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            # Create conversations table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    channel_id BIGINT,
                    guild_id BIGINT,
                    message_link TEXT NOT NULL
                )
            ''')
            
        print("✅ Database connected and initialized.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

async def save_conversation(title, channel_id, guild_id, message_link):
    """
    Saves a conversation with title and message link.
    
    Args:
        title: Title for the conversation
        channel_id: Discord channel ID
        guild_id: Discord guild ID
        message_link: Discord message link
    
    Returns:
        conversation_id or None if failed
    """
    if not pool:
        print("❌ Database pool not initialized.")
        return None

    try:
        async with pool.acquire() as conn:
            # Insert conversation
            conversation_id = await conn.fetchval('''
                INSERT INTO conversations (title, channel_id, guild_id, message_link)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', title, channel_id, guild_id, message_link)
            
            return conversation_id
    except Exception as e:
        print(f"❌ Failed to save conversation: {e}")
        return None


async def get_conversations(limit=10):
    """
    Retrieves the last N conversations.
    
    Returns:
        List of dicts with conversation info
    """
    if not pool:
        print("❌ Database pool not initialized.")
        return []

    async with pool.acquire() as conn:
        # Get conversations
        conversations = await conn.fetch('''
            SELECT 
                id,
                title,
                created_at,
                channel_id,
                guild_id,
                message_link
            FROM conversations
            ORDER BY created_at DESC
            LIMIT $1
        ''', limit)
        
        return [dict(row) for row in conversations]

async def search_conversations(query):
    """
    Searches conversations by title.
    
    Args:
        query: Search term
    
    Returns:
        List of matching conversations
    """
    if not pool:
        print("❌ Database pool not initialized.")
        return []

    async with pool.acquire() as conn:
        # Search in titles using ILIKE for case-insensitive search
        conversations = await conn.fetch('''
            SELECT
                id,
                title,
                created_at,
                message_link
            FROM conversations
            WHERE title ILIKE $1
            ORDER BY created_at DESC
        ''', f'%{query}%')
        
        return [dict(row) for row in conversations]

async def get_conversation_by_id(conversation_id):
    """
    Retrieves a single conversation.
    
    Args:
        conversation_id: ID of the conversation
    
    Returns:
        Dict with conversation info, or None if not found
    """
    if not pool:
        print("❌ Database pool not initialized.")
        return None

    async with pool.acquire() as conn:
        # Get conversation
        conv = await conn.fetchrow('''
            SELECT 
                id,
                title,
                created_at,
                channel_id,
                guild_id,
                message_link
            FROM conversations
            WHERE id = $1
        ''', conversation_id)
        
        if not conv:
            return None
        
        return dict(conv)

async def close_db():
    """Closes the database connection pool."""
    if pool:
        await pool.close()

