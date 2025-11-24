import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import database
import google.generativeai as genai

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    model = None
    print("⚠️ GEMINI_API_KEY not found. Title generation will be disabled.")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


async def generate_title(messages_content):
    """Generate a short title for the given messages using Gemini."""
    if not model:
        return None
    
    try:
        prompt = f"""You are a helpful assistant that creates concise, descriptive titles for conversations.

Analyze the following conversation and create a short, specific title (maximum 5 words) that captures the main topic or theme.

DO NOT use generic phrases like "Bot saves messages" or "Conversation summary".
DO create a title that reflects the actual content being discussed.

Conversation:
{messages_content}

Return ONLY the title, nothing else."""
        
        response = model.generate_content(prompt)
        title = response.text.strip()
        # Remove quotes if present
        title = title.strip('"\'')
        return title[:100]  # Limit to 100 chars
    except Exception as e:
        print(f"❌ Title generation failed: {e}")
        return None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    # Initialize database
    await database.init_db()

@bot.command(name='note')
async def note(ctx, *args):
    """
    Saves a message or a conversation.
    Usage:
    - Reply to a message with !note to save it.
    - !note 5 to save the last 5 messages.
    - !note 5 3 to save messages from 5th last to 3rd last.
    """
    messages_to_save = []
    
    # Case 1: Reply to a message
    if ctx.message.reference:
        original_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        messages_to_save = [(original_msg.content, str(original_msg.author))]
        combined_content = f"{original_msg.author}: {original_msg.content}"

    # Case 2: Save last N messages or Range N to M
    elif args and all(arg.isdigit() for arg in args):
        if len(args) == 1:
            # !note 5
            start = int(args[0])
            end = 1
        elif len(args) == 2:
            # !note 5 3
            start = int(args[0])
            end = int(args[1])
            if start < end:
                await ctx.send("❌ Start number must be greater than end number (e.g., `!note 5 3`).")
                return
        else:
             await ctx.send("❌ Invalid usage. Use `!note <N>` or `!note <Start> <End>`.")
             return

        limit = start + 1 # +1 to include command itself
        messages = [message async for message in ctx.channel.history(limit=limit)]
        
        if len(messages) < limit:
             # Handle case where history is shorter than requested
             pass 

        subset = messages[end : start + 1]
        
        # Prepare messages for saving
        for msg in reversed(subset):
            messages_to_save.append((msg.content, str(msg.author)))
        
        # Aggregate content for title generation
        combined_content = "\n".join([f"{author}: {content}" for content, author in messages_to_save])
    
    else:
        await ctx.send("❌ Please reply to a message, specify a number (e.g., `!note 5`), or a range (e.g., `!note 5 3`).")
        return
    
    # Generate title
    title = await generate_title(combined_content)
    
    # Save conversation
    conversation_id = await database.save_conversation(
        messages_to_save, 
        title, 
        ctx.channel.id, 
        ctx.guild.id
    )
    
    if conversation_id:
        if title:
            await ctx.send(f"✅ Saved {len(messages_to_save)} message(s)!\n📌 Title: *{title}*")
        else:
            await ctx.send(f"✅ Saved {len(messages_to_save)} message(s)!")
    else:
        await ctx.send("❌ Failed to save conversation.")

# Store search results temporarily (per user)
search_results_cache = {}

@bot.command(name='search')
async def search(ctx, *, query: str = None):
    """
    Searches saved conversations by keyword.
    Usage: !search <query>
    """
    if not query:
        await ctx.send("❌ Please provide a search query. Usage: `!search <keyword>`")
        return
    
    results = await database.search_conversations(query)
    
    if not results:
        await ctx.send(f"🔍 No conversations found matching '{query}'.")
        return
    
    # Store results for this user
    search_results_cache[ctx.author.id] = results
    
    # Build response with numbered list
    response = f"**🔍 Search Results for '{query}':**\n\n"
    for i, conv in enumerate(results, 1):
        title = conv['title'] or "Untitled"
        message_count = conv['message_count']
        created_at = conv['created_at']
        
        response += f"{i}. **{title}** ({message_count} message{'s' if message_count != 1 else ''})\n"
        response += f"   *Saved: {created_at}*\n\n"
    
    response += f"\n💡 Use `!show <number>` to view a conversation (e.g., `!show 1`)"
    
    # Split if too long
    if len(response) > 2000:
        response = response[:1997] + "..."
    
    await ctx.send(response)

@bot.command(name='show')
async def show(ctx, number: int = None):
    """
    Shows the full content of a conversation from search results.
    Usage: !show <number>
    """
    if number is None:
        await ctx.send("❌ Please specify a number. Usage: `!show <number>`")
        return
    
    # Check if user has search results
    if ctx.author.id not in search_results_cache:
        await ctx.send("❌ No search results found. Please use `!search <query>` first.")
        return
    
    results = search_results_cache[ctx.author.id]
    
    # Validate number
    if number < 1 or number > len(results):
        await ctx.send(f"❌ Invalid number. Please choose between 1 and {len(results)}.")
        return
    
    # Get the conversation
    conv_id = results[number - 1]['id']
    conversation = await database.get_conversation_by_id(conv_id)
    
    if not conversation:
        await ctx.send("❌ Conversation not found.")
        return
    
    # Build response
    title = conversation['title'] or "Untitled"
    message_count = conversation['message_count']
    created_at = conversation['created_at']
    
    response = f"**📌 {title}**\n"
    response += f"*Saved: {created_at} • {message_count} message{'s' if message_count != 1 else ''}*\n\n"
    response += "**Messages:**\n"
    
    for msg in conversation['messages']:
        response += f"**{msg['author']}** ({msg['timestamp']}):\n"
        response += f"{msg['content']}\n\n"
    
    # Split if too long (Discord has 2000 char limit)
    if len(response) > 2000:
        # Send in chunks
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables.")
    else:
        bot.run(TOKEN)
