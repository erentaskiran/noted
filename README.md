# Discord Advice Bot

AI-powered Discord bot - Save important conversations to Supabase PostgreSQL and find them easily with smart search.

## ✨ Features

- 🤖 **AI Title Generation** - Automatic, contextual titles with Gemini 1.5 Flash
- 🔍 **Smart Search** - Full-text search in titles and content
- 💾 **Relational Database** - Secure storage with Supabase PostgreSQL
- ⚡ **High Performance** - Fast response times with async/await
- 📊 **Flexible Saving** - Save single messages, last N messages, or ranges

## 📋 Requirements

- Python 3.8+
- Discord Bot Token
- Supabase account (free)
- Google Gemini API Key (free)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repo-url>
cd bot
```

### 2. Install Dependencies
```bash
python3 -m pip install -r requirements.txt
```

### 3. Set Up Environment Variables
```bash
cp .env.example .env
```

Edit `.env` file:
```env
DISCORD_TOKEN=your_discord_bot_token
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Run the Bot
```bash
python3 bot.py
```

## 📝 Commands

### `!note` - Save Conversation
```bash
# Reply to a message to save it
!note

# Save last 5 messages
!note 5

# Save from 5th to 3rd last message
!note 5 3
```

### `!search` - Search Conversations
```bash
# Search by keyword
!search python

# Searches in both titles and content
!search recipe ideas
```

### `!show` - View Conversation
```bash
# Show conversation #1 from search results
!show 1
```

## 🗄️ Database Schema

```sql
-- Conversations (1)
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    channel_id BIGINT,
    guild_id BIGINT
);

-- Messages (Many)
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    author TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Detailed Setup

### Discord Bot Creation

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. "New Application" → Enter bot name → "Create"
3. "Bot" tab → "Add Bot"
4. Copy the token
5. **Privileged Gateway Intents** → Enable `MESSAGE CONTENT INTENT`
6. "OAuth2" → "URL Generator":
   - Scopes: `bot`
   - Permissions: `Read Messages`, `Send Messages`, `Read Message History`
7. Copy the URL, open in browser, and add to your server

### Supabase Setup

1. Go to [Supabase](https://supabase.com) → Create free account
2. "New Project" → Choose project name, password, region
3. "Project Settings" → "Database" → Copy "Connection String (URI)"
4. Replace `[PASSWORD]` with your password

### Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey) → Sign in
2. "Create API Key" → Copy it

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot can't connect | Check `DISCORD_TOKEN` and Message Content Intent |
| Database error | Verify `DATABASE_URL` format and Supabase password |
| AI titles not generating | Check `GEMINI_API_KEY` (bot works without titles too) |

## 📦 Technologies

- **discord.py** - Discord bot framework
- **asyncpg** - PostgreSQL async driver
- **google-generativeai** - Gemini AI SDK
- **python-dotenv** - Environment variables management

## 🎯 Use Cases

- 💡 Save important advice
- 📚 Archive knowledge sharing
- 🎓 Organize educational materials
- 💼 Store meeting notes

## 📄 License

MIT License - Open source and free to use.

---

**Note:** Database tables are automatically created on first run.
