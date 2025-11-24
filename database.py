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
                    title TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    channel_id BIGINT,
                    guild_id BIGINT
                )
            ''')
            
            # Create messages table with foreign key
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
        print("✅ Database connected and initialized.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

async def save_conversation(messages_data, title, channel_id, guild_id):
    """
    Saves a conversation with multiple messages.
    
    Args:
        messages_data: List of tuples (content, author)
        title: AI-generated title for the conversation
        channel_id: Discord channel ID
        guild_id: Discord guild ID
    
    Returns:
        conversation_id or None if failed
    """
    if not pool:
        print("❌ Database pool not initialized.")
        return None

    try:
        async with pool.acquire() as conn:
            # Start transaction
            async with conn.transaction():
                # Insert conversation
                conversation_id = await conn.fetchval('''
                    INSERT INTO conversations (title, channel_id, guild_id)
                    VALUES ($1, $2, $3)
                    RETURNING id
                ''', title, channel_id, guild_id)
                
                # Insert all messages
                for content, author in messages_data:
                    await conn.execute('''
                        INSERT INTO messages (conversation_id, content, author)
                        VALUES ($1, $2, $3)
                    ''', conversation_id, content, author)
                
                return conversation_id
    except Exception as e:
        print(f"❌ Failed to save conversation: {e}")
        return None


async def get_conversations(limit=10):
    """
    Retrieves the last N conversations with their messages.
    
    Returns:
        List of dicts with conversation info and messages
    """
    if not pool:
        print("❌ Database pool not initialized.")
        return []

    async with pool.acquire() as conn:
        # Get conversations
        conversations = await conn.fetch('''
            SELECT 
                c.id,
                c.title,
                c.created_at,
                c.channel_id,
                c.guild_id,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
            LIMIT $1
        ''', limit)
        
        result = []
        for conv in conversations:
            # Get messages for this conversation
            messages = await conn.fetch('''
                SELECT content, author, timestamp
                FROM messages
                WHERE conversation_id = $1
                ORDER BY timestamp ASC
            ''', conv['id'])
            
            result.append({
                'id': conv['id'],
                'title': conv['title'],
                'created_at': conv['created_at'],
                'message_count': conv['message_count'],
                'messages': messages
            })
        
        return result

async def search_conversations(query):
    """
    Searches conversations by title or message content.
    
    Args:
        query: Search term
    
    Returns:
        List of matching conversations with basic info (no full messages)
    """
    if not pool:
        print("❌ Database pool not initialized.")
        return []

    async with pool.acquire() as conn:
        # Search in titles and message content using ILIKE for case-insensitive search
        conversations = await conn.fetch('''
            SELECT DISTINCT
                c.id,
                c.title,
                c.created_at,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE 
                c.title ILIKE $1 OR
                m.content ILIKE $1
            GROUP BY c.id
            ORDER BY c.created_at DESC
        ''', f'%{query}%')
        
        return [dict(row) for row in conversations]

async def get_conversation_by_id(conversation_id):
    """
    Retrieves a single conversation with all its messages.
    
    Args:
        conversation_id: ID of the conversation
    
    Returns:
        Dict with conversation info and messages, or None if not found
    """
    if not pool:
        print("❌ Database pool not initialized.")
        return None

    async with pool.acquire() as conn:
        # Get conversation
        conv = await conn.fetchrow('''
            SELECT 
                c.id,
                c.title,
                c.created_at,
                c.channel_id,
                c.guild_id,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.id = $1
            GROUP BY c.id
        ''', conversation_id)
        
        if not conv:
            return None
        
        # Get messages
        messages = await conn.fetch('''
            SELECT content, author, timestamp
            FROM messages
            WHERE conversation_id = $1
            ORDER BY timestamp ASC
        ''', conversation_id)
        
        return {
            'id': conv['id'],
            'title': conv['title'],
            'created_at': conv['created_at'],
            'message_count': conv['message_count'],
            'messages': messages
        }

async def close_db():
    """Closes the database connection pool."""
    if pool:
        await pool.close()

