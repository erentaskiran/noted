import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import database

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    # Initialize database
    await database.init_db()

# Store search results temporarily (per user)
search_results_cache = {}

@bot.command(name='search')
async def search(ctx, *, query: str):
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
        title = conv['title']
        created_at = conv['created_at']
        message_link = conv['message_link']
        
        response += f"{i}. **{title}**\n"
        response += f"   *Saved: {created_at}*\n"
        response += f"   🔗 [Jump to message]({message_link})\n\n"
    
    response += f"\n💡 Use `!show <number>` to view a conversation (e.g., `!show 1`)"
    
    # Split if too long
    if len(response) > 2000:
        response = response[:1997] + "..."
    
    await ctx.send(response)

@bot.command(name='show')
async def show(ctx, number: int):
    """
    Shows the link to a conversation from search results.
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
    conv = results[number - 1]
    
    # Build response
    title = conv['title']
    created_at = conv['created_at']
    message_link = conv['message_link']
    
    response = f"**📌 {title}**\n"
    response += f"*Saved: {created_at}*\n"
    response += f"🔗 [Jump to message]({message_link})"
    
    await ctx.send(response)

@bot.command(name='save')
async def save_topic(ctx, *, topic: str ):
    """
    Saves a conversation topic with a link.
    Usage: 
    - !save 'Topic title' <message_link> - Saves the topic with the provided link
    - !save 'Topic title' - Saves the topic with a link to the current message
    """
    if not topic:
        await ctx.send("❌ Please provide a topic. Usage: `!save 'Your topic here' <link>`")
        return
    
    # Extract text between quotes if present
    import re
    quote_match = re.search(r'["\'](.+?)["\']', topic)
    title = quote_match.group(1) if quote_match else topic
    
    # Extract Discord message link from the input
    link_pattern = r'https://discord\.com/channels/\d+/\d+/\d+'
    link_match = re.search(link_pattern, topic)
    
    if link_match:
        # User provided a link
        message_link = link_match.group(0)
    elif ctx.message.reference:
        # Reply to a message - save that message link
        original_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        message_link = original_message.jump_url
    else:
        # No link provided, use command message link
        message_link = ctx.message.jump_url
    
    # Save to database with link
    conversation_id = await database.save_conversation(
        title,
        ctx.channel.id,
        ctx.guild.id,
        message_link
    )
    
    if conversation_id:
        # Send confirmation in original channel
        await ctx.send(
            f"✅ Saved topic: **{title}**\n"
            f"🔗 Link: {message_link}"
        )
    else:
        await ctx.send("❌ Failed to save conversation.")

@bot.command(name='i')
async def info(ctx, number: int ):
    """
    Shows saved conversations with their links.
    Usage: 
    - !i - Shows last 10 saved conversations
    - !i <number> - Shows specific conversation details
    """
    if number is None:
        # Show last 10 conversations
        conversations = await database.get_conversations(10)
        
        if not conversations:
            await ctx.send("📭 No saved conversations yet.")
            return
        
        response = "**📚 Saved Conversations:**\n\n"
        for i, conv in enumerate(conversations, 1):
            title = conv['title']
            created_at = conv['created_at']
            message_link = conv['message_link']
            
            response += f"{i}. **{title}**\n"
            response += f"   *Saved: {created_at}*\n"
            response += f"   🔗 [Jump to message]({message_link})\n\n"
        
        response += "\n💡 Use `!i <number>` to view details (e.g., `!i 1`)"
        
        if len(response) > 2000:
            response = response[:1997] + "..."
        
        await ctx.send(response)
    else:
        # Show specific conversation
        conversations = await database.get_conversations(50)
        
        if number < 1 or number > len(conversations):
            await ctx.send(f"❌ Invalid number. Please choose between 1 and {len(conversations)}.")
            return
        
        conv = conversations[number - 1]
        
        # Build response
        title = conv['title']
        created_at = conv['created_at']
        message_link = conv['message_link']
        
        response = f"**📌 {title}**\n"
        response += f"*Saved: {created_at}*\n"
        response += f"🔗 [Jump to message]({message_link})\n"
        
        await ctx.send(response)

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables.")
    else:
        bot.run(TOKEN)
