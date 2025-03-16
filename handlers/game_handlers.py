"""
Game handlers for the Telegram bot.
"""
import re
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from checkers_game import CheckersGame, active_games, GameState

logger = logging.getLogger(__name__)

async def checkers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start a game of checkers.
    Format: /checkers [opponent_username]
    If no opponent is specified, play against the bot.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if there's already an active game in this chat
    if chat_id in active_games:
        game = active_games[chat_id]
        await update.message.reply_text(
            "There's already an active checkers game in this chat. "
            "Finish it or use /endcheckers to end it first."
        )
        return
    
    # First, send the rules and FAQ
    rules_text = (
        "♟️ *CHECKERS GAME RULES & FAQ* ♟️\n\n"
        
        "*Basic Rules:*\n"
        "• Pieces move diagonally on dark squares\n"
        "• Regular pieces can only move forward\n"
        "• Kings can move forward or backward\n"
        "• Capture by jumping over opponent pieces\n"
        "• Multiple jumps in one turn are allowed\n"
        "• Reach opponent's end to become a King\n\n"
        
        "*How to Play:*\n"
        "• Make moves using the format: `A3-B4`\n"
        "• A3 is the starting position (column A, row 3)\n"
        "• B4 is the destination (column B, row 4)\n"
        "• You can also use the 'Make a Move' button\n\n"
        
        "*FAQ:*\n"
        "• *Q: Who goes first?*\n"
        "  A: White (bottom pieces) always goes first\n\n"
        "• *Q: Is capturing mandatory?*\n"
        "  A: No, capturing is optional in this version\n\n"
        "• *Q: How do I get a King?*\n"
        "  A: Reach the opposite end of the board\n\n"
        "• *Q: How do I know if I'm winning?*\n"
        "  A: Try to capture more opponent pieces\n\n"
        "• *Q: How do I end the game?*\n"
        "  A: Use `/endcheckers` to terminate the game"
    )
    
    await update.message.reply_markdown(rules_text)
    
    # Check if playing against another user or the bot
    opponent_username = None
    if context.args and len(context.args) > 0:
        opponent_username = context.args[0].replace("@", "")
    
    if opponent_username:
        # Create a game with a human opponent (they'll need to join)
        game = CheckersGame(user_id)
        active_games[chat_id] = game
        
        # Create the join game button
        keyboard = [
            [InlineKeyboardButton("Join Game", callback_data=f"join_checkers:{user_id}")],
            [InlineKeyboardButton("Game Rules", callback_data="checkers_rules")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎮 {update.effective_user.first_name} has started a game of Checkers and is waiting for {opponent_username} to join!\n"
            f"Use the button below to join the game.",
            reply_markup=reply_markup
        )
    else:
        # Create a game against the AI
        game = CheckersGame(user_id, None)  # None indicates AI opponent
        active_games[chat_id] = game
        
        # Show the initial board
        board_text = game.get_board_as_string()
        status_text = game.get_game_status()
        
        # Create the move button
        keyboard = [
            [InlineKeyboardButton("Make a Move", callback_data="move_checkers")],
            [InlineKeyboardButton("Game Rules", callback_data="checkers_rules")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎮 {update.effective_user.first_name} has started a game of Checkers against the AI!\n\n"
            f"{board_text}\n"
            f"{status_text}\n\n"
            f"Use the button below to make a move or type a move in the format: A3-B4",
            reply_markup=reply_markup
        )

async def end_checkers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """End the current checkers game in the chat."""
    chat_id = update.effective_chat.id
    
    if chat_id in active_games:
        del active_games[chat_id]
        await update.message.reply_text("The checkers game has been ended.")
    else:
        await update.message.reply_text("There's no active checkers game in this chat.")

async def move_checkers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Make a move in the current checkers game.
    Format: /move A3-B4
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if chat_id not in active_games:
        await update.message.reply_text(
            "There's no active checkers game in this chat. "
            "Start one with /checkers."
        )
        return
    
    game = active_games[chat_id]
    
    # Check if it's this user's turn
    is_user_turn = False
    if game.current_turn.name == "WHITE" and game.user_id1 == user_id:
        is_user_turn = True
    elif game.current_turn.name == "BLACK" and game.user_id2 == user_id:
        is_user_turn = True
    
    if not is_user_turn:
        await update.message.reply_text("It's not your turn!")
        return
    
    # Get the move text from the command
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Please specify a move in the format: /move A3-B4"
        )
        return
    
    move_text = context.args[0]
    
    # Process the move
    await process_move(update, context, move_text)

async def process_move(update: Update, context: ContextTypes.DEFAULT_TYPE, move_text: str) -> None:
    """Process a move for the checkers game."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if chat_id not in active_games:
        return
    
    game = active_games[chat_id]
    
    # Check if it's game over
    if game.state == GameState.GAME_OVER:
        await update.message.reply_text(
            f"This game is already over. {game.get_game_status()}\n"
            f"Start a new game with /checkers."
        )
        return
    
    # Check if it's this user's turn
    is_user_turn = False
    if game.current_turn.name == "WHITE" and game.user_id1 == user_id:
        is_user_turn = True
    elif game.current_turn.name == "BLACK" and game.user_id2 == user_id:
        is_user_turn = True
    
    if not is_user_turn and user_id != update.effective_chat.id:  # Allow moves in private chat
        await update.message.reply_text("It's not your turn!")
        return
    
    # Parse and validate the move
    from_pos, to_pos = game.parse_move(move_text)
    if from_pos is None or to_pos is None:
        await update.message.reply_text(
            "Invalid move format. Please use the format A3-B4."
        )
        return
    
    # Make the move
    if not game.make_move(from_pos, to_pos):
        await update.message.reply_text(
            "Invalid move. Please try again."
        )
        return
    
    # Update the game display
    board_text = game.get_board_as_string()
    status_text = game.get_game_status()
    
    # Create the move button
    keyboard = [
        [InlineKeyboardButton("Make a Move", callback_data="move_checkers")],
        [InlineKeyboardButton("Game Rules", callback_data="checkers_rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎮 Checkers Game\n\n"
        f"{board_text}\n"
        f"{status_text}\n\n"
        f"Last move: {move_text}\n\n"
        f"Use the button below to make a move or type a move in the format: A3-B4",
        reply_markup=reply_markup
    )

async def handle_checkers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks for checkers game."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    data = query.data
    
    if data == "checkers_rules":
        # Show the rules in a new message to avoid disturbing the game
        rules_text = (
            "♟️ *CHECKERS GAME RULES & FAQ* ♟️\n\n"
            
            "*Basic Rules:*\n"
            "• Pieces move diagonally on dark squares\n"
            "• Regular pieces can only move forward\n"
            "• Kings can move forward or backward\n"
            "• Capture by jumping over opponent pieces\n"
            "• Multiple jumps in one turn are allowed\n"
            "• Reach opponent's end to become a King\n\n"
            
            "*How to Play:*\n"
            "• Make moves using the format: `A3-B4`\n"
            "• A3 is the starting position (column A, row 3)\n"
            "• B4 is the destination (column B, row 4)\n"
            "• You can also use the 'Make a Move' button\n\n"
            
            "*FAQ:*\n"
            "• *Q: Who goes first?*\n"
            "  A: White (bottom pieces) always goes first\n\n"
            "• *Q: Is capturing mandatory?*\n"
            "  A: No, capturing is optional in this version\n\n"
            "• *Q: How do I get a King?*\n"
            "  A: Reach the opposite end of the board\n\n"
            "• *Q: How do I know if I'm winning?*\n"
            "  A: Try to capture more opponent pieces\n\n"
            "• *Q: How do I end the game?*\n"
            "  A: Use `/endcheckers` to terminate the game"
        )
        
        keyboard = [
            [InlineKeyboardButton("Back to Game", callback_data="checkers_back_to_game")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=rules_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    elif data == "checkers_back_to_game":
        # Remove the rules message
        await query.message.delete()
        return
    
    elif data.startswith("join_checkers:"):
        # Handle joining a game
        creator_id = int(data.split(":")[1])
        
        if chat_id not in active_games:
            await query.edit_message_text(
                "This game is no longer available."
            )
            return
        
        game = active_games[chat_id]
        
        if game.user_id1 == user_id:
            await query.edit_message_text(
                "You can't join your own game!"
            )
            return
        
        if game.user_id2 is not None:
            await query.edit_message_text(
                "Someone has already joined this game."
            )
            return
        
        # Join the game
        game.user_id2 = user_id
        game.state = GameState.WAITING_FOR_MOVE
        
        # Show the initial board
        board_text = game.get_board_as_string()
        status_text = game.get_game_status()
        
        # Create the move button
        keyboard = [
            [InlineKeyboardButton("Make a Move", callback_data="move_checkers")],
            [InlineKeyboardButton("Game Rules", callback_data="checkers_rules")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎮 {query.from_user.first_name} has joined the game of Checkers!\n\n"
            f"{board_text}\n"
            f"{status_text}\n\n"
            f"Use the button below to make a move or type a move in the format: A3-B4",
            reply_markup=reply_markup
        )
    
    elif data == "move_checkers":
        # Show dialog for making a move
        if chat_id not in active_games:
            await query.edit_message_text(
                "This game is no longer available."
            )
            return
        
        game = active_games[chat_id]
        
        # Check if it's game over
        if game.state == GameState.GAME_OVER:
            await query.edit_message_text(
                f"This game is already over. {game.get_game_status()}\n"
                f"Start a new game with /checkers."
            )
            return
        
        # Show current board and prompt for move
        board_text = game.get_board_as_string()
        status_text = game.get_game_status()
        
        await context.bot.send_message(
            chat_id=user_id,  # Send as private message to the user
            text=f"🎮 Checkers Game\n\n"
                 f"{board_text}\n"
                 f"{status_text}\n\n"
                 f"Enter your move in the format: A3-B4"
        )
        
        # Update the original message to show waiting for a move
        current_player = "Player 1 (White)" if game.current_turn.name == "WHITE" else "Player 2 (Black)"
        await query.edit_message_text(
            f"🎮 Checkers Game\n\n"
            f"{board_text}\n"
            f"{status_text}\n\n"
            f"Waiting for {current_player} to make a move..."
        )

# Function to handle checkers move messages in private chat
async def handle_checkers_move_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle potential checkers move messages in private chat.
    Returns True if message was a checkers move, False otherwise.
    """
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Check if the message looks like a checkers move (e.g., "A3-B4")
    move_pattern = re.compile(r'^[A-Ha-h][1-8]-[A-Ha-h][1-8]$')
    if not move_pattern.match(message_text.strip()):
        return False
    
    # Find active games for this user
    user_games = []
    for chat_id, game in active_games.items():
        if game.user_id1 == user_id or game.user_id2 == user_id:
            user_games.append((chat_id, game))
    
    if not user_games:
        await update.message.reply_text("You don't have any active checkers games.")
        return True
    
    if len(user_games) == 1:
        # Only one active game, make the move
        chat_id, game = user_games[0]
        
        # Check if it's this user's turn
        is_user_turn = False
        if game.current_turn.name == "WHITE" and game.user_id1 == user_id:
            is_user_turn = True
        elif game.current_turn.name == "BLACK" and game.user_id2 == user_id:
            is_user_turn = True
        
        if not is_user_turn:
            await update.message.reply_text("It's not your turn!")
            return True
        
        # Process the move
        move_text = message_text.strip()
        
        # Parse and validate the move
        from_pos, to_pos = game.parse_move(move_text)
        if from_pos is None or to_pos is None:
            await update.message.reply_text(
                "Invalid move format. Please use the format A3-B4."
            )
            return True
        
        # Make the move
        if not game.make_move(from_pos, to_pos):
            await update.message.reply_text(
                "Invalid move. Please try again."
            )
            return True
        
        # Update the game display
        board_text = game.get_board_as_string()
        status_text = game.get_game_status()
        
        # Send updated board to the user
        await update.message.reply_text(
            f"🎮 Checkers Game\n\n"
            f"{board_text}\n"
            f"{status_text}\n\n"
            f"Your move: {move_text}"
        )
        
        # Also update the game in the original chat
        # Create the move button
        keyboard = [
            [InlineKeyboardButton("Make a Move", callback_data="move_checkers")],
            [InlineKeyboardButton("Game Rules", callback_data="checkers_rules")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎮 Checkers Game Update\n\n"
                 f"{board_text}\n"
                 f"{status_text}\n\n"
                 f"Last move: {move_text}\n\n"
                 f"Use the button below to make your move:",
            reply_markup=reply_markup
        )
        
        return True
    else:
        # Multiple active games, ask the user to specify
        games_text = "You have multiple active games. Please specify which game you want to make a move in:\n\n"
        for i, (chat_id, game) in enumerate(user_games, 1):
            opponent_id = game.user_id2 if game.user_id1 == user_id else game.user_id1
            opponent_type = "AI" if opponent_id is None else f"User {opponent_id}"
            games_text += f"{i}. Game in chat {chat_id} against {opponent_type}\n"
        
        games_text += "\nPlease use /move [game_number] [your_move] to make a move."
        await update.message.reply_text(games_text)
        return True