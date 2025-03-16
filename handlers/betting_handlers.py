"""
Betting game handlers for the Telegram bot.
"""
import logging
import re
import random
from typing import Optional, Tuple, List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from betting_game import (
    BettingGame, GameType, GameState, PlayerMove,
    create_betting_game, get_betting_game, remove_betting_game
)
from wallet_system import (
    get_balance, add_funds, deduct_funds, create_bet, join_bet, cancel_bet, settle_bet,
    reset_wallet, admin_set_balance, admin_add_balance, admin_remove_balance, admin_list_all_wallets
)

# Default bet amount for quick commands
DEFAULT_BET_AMOUNT = 100

logger = logging.getLogger(__name__)

# Button callbacks
BTN_JOIN_GAME = "join_betting_game"
BTN_MAKE_MOVE = "betting_game_move"
BTN_CANCEL_GAME = "cancel_betting_game"

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show wallet balance and commands.
    Format: /wallet
    """
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    
    help_text = (
        f"💰 *Your Virtual Wallet*\n\n"
        f"Current Balance: *{balance}* credits\n\n"
        f"*Commands:*\n"
        f"• `/wallet` - View your balance\n"
        f"• `/resetwallet` - Reset your balance to default\n"
        f"• `/bet dice <amount> [solo]` - Dice roll game\n"
        f"• `/bet coin <amount> [solo]` - Coin flip game\n"
        f"• `/bet number <amount> [solo]` - Number guessing game\n"
        f"• `/bet rps <amount> [solo]` - Rock-paper-scissors\n\n"
        f"*Single Player:* Add 'solo' to play against the bot\n"
        f"Example: `/bet dice 100 solo`\n\n"
        f"*Note:* This is a virtual wallet for testing purposes only. No real money is involved."
    )
    
    # Add crypto betting information
    crypto_text = (
        f"\n\n💎 *Crypto Betting (REAL Money)*\n"
        f"You can now bet with real cryptocurrency using @cctip_bot!\n"
        f"• `/cryptobet dice <amount> <crypto>` - Dice with crypto\n"
        f"• `/cryptobet coin <amount> <crypto>` - Coin flip with crypto\n"
        f"• `/cryptobet number <amount> <crypto>` - Number game with crypto\n"
        f"• `/cryptobet rps <amount> <crypto>` - RPS with crypto\n\n"
        f"Supported cryptocurrencies: DOGE, TRX, USDT, BNB\n"
        f"Example: `/cryptobet dice 1 doge`"
    )
    help_text += crypto_text
    
    # Add admin commands for the special admin user
    if user_id == 1159603709:
        admin_text = (
            f"\n\n*🔐 Admin Commands:*\n"
            f"• `/adminsetbalance <user_id> <amount>` - Set a user's balance\n"
            f"• `/adminaddbalance <user_id> <amount>` - Add to a user's balance\n"
            f"• `/adminremovebalance <user_id> <amount>` - Remove from a user's balance\n"
            f"• `/adminlistwallets` - List all wallet balances\n"
        )
        help_text += admin_text
    
    await update.message.reply_markdown(help_text)

async def reset_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Reset wallet balance to default.
    Format: /resetwallet
    """
    user_id = update.effective_user.id
    success, new_balance = reset_wallet(user_id)
    
    await update.message.reply_markdown(
        f"💰 Your wallet has been reset!\n\n"
        f"New Balance: *{new_balance}* credits"
    )

# Admin commands
async def admin_set_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin command to set a user's balance to a specific amount.
    Format: /adminsetbalance <user_id> <amount>
    """
    admin_id = update.effective_user.id
    
    # Check arguments
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /adminsetbalance <user_id> <amount>\n"
            "Example: /adminsetbalance 123456789 1000"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("User ID and amount must be numbers.")
        return
    
    success, message = admin_set_balance(admin_id, target_user_id, amount)
    
    if success:
        await update.message.reply_markdown(f"✅ {message}")
    else:
        await update.message.reply_markdown(f"❌ {message}")

async def admin_add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin command to add to a user's balance.
    Format: /adminaddbalance <user_id> <amount>
    """
    admin_id = update.effective_user.id
    
    # Check arguments
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /adminaddbalance <user_id> <amount>\n"
            "Example: /adminaddbalance 123456789 500"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("User ID and amount must be numbers.")
        return
    
    success, message = admin_add_balance(admin_id, target_user_id, amount)
    
    if success:
        await update.message.reply_markdown(f"✅ {message}")
    else:
        await update.message.reply_markdown(f"❌ {message}")

async def admin_remove_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin command to remove from a user's balance.
    Format: /adminremovebalance <user_id> <amount>
    """
    admin_id = update.effective_user.id
    
    # Check arguments
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /adminremovebalance <user_id> <amount>\n"
            "Example: /adminremovebalance 123456789 200"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("User ID and amount must be numbers.")
        return
    
    success, message = admin_remove_balance(admin_id, target_user_id, amount)
    
    if success:
        await update.message.reply_markdown(f"✅ {message}")
    else:
        await update.message.reply_markdown(f"❌ {message}")

async def admin_list_wallets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin command to list all wallet balances.
    Format: /adminlistwallets
    """
    admin_id = update.effective_user.id
    
    success, wallet_data = admin_list_all_wallets(admin_id)
    
    if not success:
        await update.message.reply_text("You don't have permission to view wallet data.")
        return
    
    # Format the wallet data
    if not wallet_data:
        await update.message.reply_text("No wallet data available.")
        return
    
    # Sort wallets by balance (highest first)
    sorted_wallets = sorted(wallet_data.items(), key=lambda x: x[1], reverse=True)
    
    # Prepare message in chunks to avoid message size limits
    wallet_text = "💰 *Wallet Balances*\n\n"
    current_chunk = wallet_text
    
    for user_id, balance in sorted_wallets:
        line = f"User ID: `{user_id}` - Balance: *{balance}* credits\n"
        
        # If adding this line would make the message too long, send the current chunk
        if len(current_chunk) + len(line) > 4000:
            await update.message.reply_markdown(current_chunk)
            current_chunk = ""
        
        current_chunk += line
    
    # Send the final chunk if it has any content
    if current_chunk:
        await update.message.reply_markdown(current_chunk)

async def bet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start a betting game.
    Format: /bet <game_type> <amount> [solo]
    Examples: 
      /bet dice 100
      /bet coin 50 solo
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if we have arguments
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Please specify a game type and bet amount.\n"
            "Example: /bet dice 100\n"
            "For single player: /bet dice 100 solo\n\n"
            "Available games: dice, coin, number, rps"
        )
        return
    
    # Parse game type and bet amount
    game_type_str = context.args[0].lower()
    try:
        bet_amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Bet amount must be a number.")
        return
    
    # Check if this is a single-player game
    single_player = False
    if len(context.args) > 2 and context.args[2].lower() in ["solo", "single", "sp", "s"]:
        single_player = True
    
    # Validate bet amount
    if bet_amount <= 0:
        await update.message.reply_text("Bet amount must be greater than 0.")
        return
    
    # Check if user has enough balance
    user_balance = get_balance(user_id)
    if user_balance < bet_amount:
        await update.message.reply_markdown(
            f"❌ You don't have enough credits!\n\n"
            f"Your Balance: *{user_balance}* credits\n"
            f"Bet Amount: *{bet_amount}* credits\n\n"
            f"Use `/wallet` to check your balance."
        )
        return
    
    # Determine game type
    game_type = None
    if game_type_str == "dice":
        game_type = GameType.DICE_ROLL
    elif game_type_str == "coin":
        game_type = GameType.COIN_FLIP
    elif game_type_str == "number":
        game_type = GameType.NUMBER_GUESS
    elif game_type_str in ["rps", "rock", "paper", "scissors"]:
        game_type = GameType.ROCK_PAPER_SCISSORS
    else:
        await update.message.reply_text(
            "Invalid game type. Available games: dice, coin, number, rps"
        )
        return
    
    # Deduct the bet amount from the user's balance
    success, new_balance = deduct_funds(user_id, bet_amount)
    if not success:
        await update.message.reply_text(f"Error deducting funds. Please try again.")
        return
    
    # Create the betting game (with single player option if specified)
    game = create_betting_game(game_type, user_id, bet_amount, single_player)
    
    # Store the creator's username if available
    username = update.message.from_user.username
    if username:
        game.player_usernames[user_id] = username
    
    # For multiplayer games, create the bet in the wallet system
    if not single_player:
        # Create the corresponding bet in the wallet system (funds already deducted)
        success, message = create_bet(game.game_id, user_id, bet_amount)
        if not success:
            # Refund the user if bet creation fails
            add_funds(user_id, bet_amount)
            remove_betting_game(game.game_id)
            await update.message.reply_text(f"Error creating bet: {message}")
            return
        
        # Create buttons for joining the game
        keyboard = [
            [InlineKeyboardButton("Join Game", callback_data=f"{BTN_JOIN_GAME}:{game.game_id}")],
            [InlineKeyboardButton("Cancel Game", callback_data=f"{BTN_CANCEL_GAME}:{game.game_id}")]
        ]
    else:
        # Create appropriate game buttons for single player game
        keyboard = []
        
        if game_type == GameType.DICE_ROLL:
            # Dice game - player just rolls
            keyboard = [[InlineKeyboardButton("🎲 Roll Dice", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:roll")]]
        
        elif game_type == GameType.COIN_FLIP:
            # Coin flip - player guesses heads or tails
            keyboard = [
                [
                    InlineKeyboardButton("Heads", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:heads"),
                    InlineKeyboardButton("Tails", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:tails")
                ]
            ]
            
        elif game_type == GameType.NUMBER_GUESS:
            # Number guessing - provide number buttons 1-10
            row1 = [InlineKeyboardButton(str(i), callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:{i}") for i in range(1, 6)]
            row2 = [InlineKeyboardButton(str(i), callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:{i}") for i in range(6, 11)]
            keyboard = [row1, row2]
            
        elif game_type == GameType.ROCK_PAPER_SCISSORS:
            # Rock Paper Scissors - provide RPS buttons
            keyboard = [
                [
                    InlineKeyboardButton("🪨 Rock", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:rock"),
                    InlineKeyboardButton("📄 Paper", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:paper"),
                    InlineKeyboardButton("✂️ Scissors", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:scissors")
                ]
            ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send game info
    await update.message.reply_markdown(
        game.get_status_text(),
        reply_markup=reply_markup
    )

async def handle_betting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle callbacks for betting games.
    Returns True if callback was processed, False otherwise.
    """
    query = update.callback_query
    if not query:
        return False
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    # Check if this is a betting game callback
    if not any(callback_data.startswith(prefix) for prefix in [BTN_JOIN_GAME, BTN_MAKE_MOVE, BTN_CANCEL_GAME, "refresh"]):
        return False
    
    # Extract game_id from callback data
    game_id = None
    if callback_data.startswith(BTN_JOIN_GAME):
        _, game_id = callback_data.split(":", 1)
    elif callback_data.startswith(BTN_MAKE_MOVE):
        parts = callback_data.split(":", 2)
        if len(parts) >= 2:
            game_id = parts[1]
    elif callback_data.startswith(BTN_CANCEL_GAME):
        _, game_id = callback_data.split(":", 1)
    elif callback_data.startswith("refresh"):
        _, game_id = callback_data.split(":", 1)
    
    # For non-join actions, check if user is part of the game
    if game_id and not callback_data.startswith(BTN_JOIN_GAME):
        game = get_betting_game(game_id)
        if game and user_id not in game.players:
            # Silently acknowledge the callback without changing the message
            await query.answer("You're not part of this game", show_alert=True)
            return True
    
    # Process the callback
    await query.answer()
    
    if callback_data.startswith(BTN_JOIN_GAME):
        # Join a betting game
        _, game_id = callback_data.split(":", 1)
        return await process_join_game(query, game_id, user_id)
    
    elif callback_data.startswith(BTN_MAKE_MOVE):
        # Make a move in a betting game
        parts = callback_data.split(":", 2)
        if len(parts) < 3:
            await query.edit_message_text("Invalid move format.")
            return True
        
        _, game_id, move = parts
        # Check if the game exists and the user is in it
        game = get_betting_game(game_id)
        if not game:
            await query.answer("This game no longer exists.", show_alert=True)
            return True
            
        # Check if the user has already made a move
        if user_id in game.player_moves:
            # Get the player's move description
            player_move = game.player_moves.get(user_id)
            move_description = ""
            
            if game.game_type == GameType.DICE_ROLL:
                move_description = f"rolled a 🎲 {player_move}"
            elif game.game_type == GameType.COIN_FLIP:
                move_str = player_move.capitalize() if hasattr(player_move, 'capitalize') else str(player_move).capitalize()
                move_description = f"chose {move_str}"
            elif game.game_type == GameType.NUMBER_GUESS:
                move_description = f"picked the number {player_move}"
            elif game.game_type == GameType.ROCK_PAPER_SCISSORS:
                move_name = player_move.value.capitalize() if hasattr(player_move, 'value') else str(player_move).capitalize()
                move_description = f"chose {move_name}"
                
            # Show a meaningful popup
            await query.answer(f"You've already {move_description}! Wait for the game to complete.", show_alert=True)
            
            # Refresh the UI to ensure it reflects the correct state
            keyboard = create_game_controls(game, user_id)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    game.get_status_text(),
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Error updating game UI: {e}")
                
            return True
            
        return await process_make_move(query, game_id, user_id, move, context)
    
    elif callback_data.startswith(BTN_CANCEL_GAME):
        # Cancel a betting game
        _, game_id = callback_data.split(":", 1)
        return await process_cancel_game(query, game_id, user_id)
    
    elif callback_data.startswith("refresh"):
        # Refresh game status
        _, game_id = callback_data.split(":", 1)
        return await process_refresh_game(query, game_id, user_id)
    
    return False

async def process_join_game(query, game_id: str, user_id: int) -> bool:
    """Process a request to join a betting game."""
    game = get_betting_game(game_id)
    if not game:
        await query.edit_message_text("This game no longer exists.")
        return True
        
    # Store username for better display if available
    if hasattr(query.from_user, 'username') and query.from_user.username:
        game.player_usernames[user_id] = query.from_user.username
    
    # Store message info for updating all players
    message_info = (query.message.chat_id, query.message.message_id)
    game.player_messages[user_id] = message_info
    
    # Check if user is already in the game
    if user_id in game.players:
        # Instead of editing the whole message, just show a popup notification
        # This is cleaner and doesn't disrupt the game UI
        
        # Different message for creator vs joiner
        status_msg = "You're already in this game!"
        if user_id == game.creator_id:
            status_msg = "You created this game. Wait for another player to join."
        
        # Just show a notification popup
        await query.answer(status_msg, show_alert=True)
        
        # Don't try to update the message interface - just show the alert
        # This prevents "message not modified" errors when there are no changes
        # The UI will update naturally when the user takes another action
        # Simply return after showing the popup alert
        
        return True
    
    # Check if game is still accepting players
    if game.state != GameState.WAITING_FOR_PLAYER:
        # Just acknowledge the query but don't change anything for non-participants
        await query.answer("This game is no longer accepting players", show_alert=True)
        return True
    
    # Check if user has enough balance and join the bet
    success, message = join_bet(game_id, user_id, game.bet_amount)
    if not success:
        await query.edit_message_text(
            f"{game.get_status_text()}\n\nError joining game: {message}"
        )
        return True
    
    # Add player to the game
    game.add_player(user_id)
    
    # Store the player's identification details
    # Username for @mentions
    username = query.from_user.username
    if username:
        game.player_usernames[user_id] = username
        
    # First name for direct Telegram mention by ID
    if hasattr(query.from_user, 'first_name') and query.from_user.first_name:
        game.player_names[user_id] = query.from_user.first_name
        
    # Full name for more complete identification
    full_name = query.from_user.first_name
    if hasattr(query.from_user, 'last_name') and query.from_user.last_name:
        full_name += f" {query.from_user.last_name}"
    game.player_full_names[user_id] = full_name
    
    # Update the message with game controls for this player
    keyboard = create_game_controls(game, user_id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Now the game has two players and has moved to WAITING_FOR_MOVES state
    # We need to update both player's messages
    
    # Update this player's message (the player who just joined)
    await query.edit_message_text(
        f"🚨 *YOUR TURN* - MAKE YOUR MOVE BELOW! 🚨\n\n{game.get_status_text()}\n\nYou have joined the game! Make your move now.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    # Update the first player's message to let them know a second player has joined
    # and they need to make a move
    creator_id = game.creator_id
    if creator_id != user_id and creator_id in game.player_messages:
        try:
            chat_id, message_id = game.player_messages[creator_id]
            creator_keyboard = create_game_controls(game, creator_id)
            creator_reply_markup = InlineKeyboardMarkup(creator_keyboard)
            
            # Get joiner's name for the notification
            joiner_name = "Someone"
            if user_id in game.player_usernames:
                joiner_name = f"@{game.player_usernames[user_id]}"
            elif user_id in game.player_names:
                joiner_name = game.player_names[user_id]
            elif user_id in game.player_full_names:
                joiner_name = game.player_full_names[user_id]
                
            # Create attention-grabbing message
            await query.bot.edit_message_text(
                f"🚨 *YOUR TURN* - MAKE YOUR MOVE BELOW! 🚨\n\n{game.get_status_text()}\n\n{joiner_name} has joined! It's your turn to make a move now.",
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=creator_reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Error updating creator's message: {e}")
    
    return True

async def process_make_move(query, game_id: str, user_id: int, move_str: str, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
    """Process a move in a betting game."""
    game = get_betting_game(game_id)
    if not game:
        await query.edit_message_text("This game no longer exists.")
        return True
    
    # Check if user is in the game
    if user_id not in game.players:
        # Just acknowledge the query but don't change anything for non-participants
        await query.answer("You're not part of this game", show_alert=True)
        return True
    
    # Check if user already made a move
    if user_id in game.player_moves:
        # Get the player's move and format it nicely
        move = game.player_moves.get(user_id)
        move_description = ""
        
        if game.game_type == GameType.DICE_ROLL:
            move_description = f"rolled a 🎲 {move}"
        elif game.game_type == GameType.COIN_FLIP:
            move_str = move.capitalize() if hasattr(move, 'capitalize') else str(move).capitalize()
            move_description = f"chose {move_str}"
        elif game.game_type == GameType.NUMBER_GUESS:
            move_description = f"picked the number {move}"
        elif game.game_type == GameType.ROCK_PAPER_SCISSORS:
            move_name = move.value.capitalize() if hasattr(move, 'value') else str(move).capitalize()
            move_description = f"chose {move_name}"
            
        # Count how many players have moved
        players_moved = len(game.player_moves)
        total_players = len(game.players)
        
        # Show a popup message indicating they've already made their move
        popup_message = f"You've already {move_description}! Wait for other players to complete their moves."
        
        if players_moved == total_players:
            popup_message = f"You've already {move_description}! All players have moved. Game results will be shown shortly."
            
        # Just use a popup notification instead of editing the message
        await query.answer(popup_message, show_alert=True)
        return True
    
    # Check if game is waiting for moves
    if game.state != GameState.WAITING_FOR_MOVES:
        await query.edit_message_text(
            f"{game.get_status_text()}\n\nThis game is not accepting moves right now."
        )
        return True
    
    # Parse the move based on game type
    parsed_move = None
    if game.game_type == GameType.DICE_ROLL:
        # For dice, we roll automatically
        parsed_move = random.randint(1, 6)
    elif game.game_type == GameType.COIN_FLIP:
        if move_str not in ["heads", "tails"]:
            await query.edit_message_text(
                f"{game.get_status_text()}\n\nInvalid move. Choose heads or tails."
            )
            return True
        parsed_move = move_str
    elif game.game_type == GameType.NUMBER_GUESS:
        try:
            parsed_move = int(move_str)
            if parsed_move < 1 or parsed_move > 10:
                await query.edit_message_text(
                    f"{game.get_status_text()}\n\nInvalid number. Choose between 1 and 10."
                )
                return True
        except ValueError:
            await query.edit_message_text(
                f"{game.get_status_text()}\n\nInvalid number. Choose between 1 and 10."
            )
            return True
    elif game.game_type == GameType.ROCK_PAPER_SCISSORS:
        if move_str not in ["rock", "paper", "scissors"]:
            await query.edit_message_text(
                f"{game.get_status_text()}\n\nInvalid move. Choose rock, paper, or scissors."
            )
            return True
        parsed_move = PlayerMove(move_str)
    
    # Make the move
    success = game.make_move(user_id, parsed_move)
    if not success:
        await query.edit_message_text(
            f"{game.get_status_text()}\n\nFailed to make the move."
        )
        return True
        
    # Reload the game to get the updated state
    game = get_betting_game(game_id)
    
    # Store this message's chat_id and message_id for the current player
    # This will be used to update all players when the game state changes
    message_info = (query.message.chat_id, query.message.message_id)
    game.player_messages[user_id] = message_info
    
    # Create the appropriate keyboard for this specific user
    # This keeps the UI clean for the player who just moved
    # Verify game is not None before calling create_game_controls
    if game:
        keyboard = create_game_controls(game, user_id)
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    else:
        # If game is None, we can't create controls, provide a simple fallback
        reply_markup = None
    
    # Add instructions for each player based on their move status
    instructions = ""
    if game.state == GameState.WAITING_FOR_MOVES:
        # Prepare a message with instructions for each player
        players_moved = len(game.player_moves)
        total_players = len(game.players)
        
        if players_moved < total_players:
            # Some players still need to make moves
            if user_id in game.player_moves:
                # Keep it minimal for players who have already moved
                instructions = "Your move has been recorded. Use the button below to check the game result once all players have moved."
            else:
                instructions = "It's your turn to make a move. Please use the buttons below."
    
    # If all players have made their moves, update all players' game views and determine the winner immediately
    # Make sure game is not None before accessing its properties
    if game and len(game.player_moves) == len(game.players):
        # All players have moved, game should be over
        # Only determine the winner if it's not already determined
        if game.state != GameState.GAME_OVER:
            game._determine_winner()
            game.state = GameState.GAME_OVER
            
            # Since this is the code path where the game just ended because all players moved,
            # we should immediately skip to the settlement part to show results
            # The next if statement will handle the settlement
    
    # If game is over, settle the bet (and check if game exists)
    if game and game.state == GameState.GAME_OVER:
        try:
            # Handle tie game case
            if game.is_tie:
                # Handle tie in single player mode
                if game.single_player:
                    # Add the bet amount back to the player
                    add_funds(user_id, game.bet_amount)
                    await query.edit_message_text(
                        f"{game.get_status_text()}\n\n🔄 It's a tie! Your {game.bet_amount} credits have been refunded.",
                        parse_mode="Markdown"
                    )
                    # Remove the game
                    remove_betting_game(game_id)
                    return True
                
                # Handle tie in multiplayer mode - use settle_bet with None for winner_id to refund everyone
                else:
                    success, message, amount = settle_bet(game_id, None)  # None indicates a tie
                    if success:
                        # Update all players with the tie result
                        tie_announcement = "🔄 It's a tie! All bets have been refunded."
                        
                        # Update all players with the final result
                        for player_id, message_info in game.player_messages.items():
                            if player_id != user_id:  # Skip the current user, they're handled by the query
                                try:
                                    chat_id, message_id = message_info
                                    await context.bot.edit_message_text(
                                        f"{game.get_status_text()}\n\n{tie_announcement}",
                                        chat_id=chat_id,
                                        message_id=message_id,
                                        parse_mode="Markdown"
                                    )
                                except Exception as e:
                                    print(f"Error updating player {player_id}: {e}")
                        
                        # Update the current player's message
                        await query.edit_message_text(
                            f"{game.get_status_text()}\n\n{tie_announcement}",
                            parse_mode="Markdown"
                        )
                        # Remove the game
                        remove_betting_game(game_id)
                        return True
                    else:
                        await query.edit_message_text(
                            f"{game.get_status_text()}\n\nError settling tie game: {message}",
                            parse_mode="Markdown"
                        )
                        return True
            
            # Handle winner cases
            winner_id = game.winner_id
            
            # Special handling for single-player games against bot
            if game.single_player and winner_id == -1:
                # Bot won, no need to add funds to bot
                await query.edit_message_text(
                    f"{game.get_status_text()}\n\n🤖 Bot has won this round! Better luck next time!",
                    parse_mode="Markdown"
                )
                # Remove the game
                remove_betting_game(game_id)
                return True
                
            # Human player won in single-player mode
            elif game.single_player and winner_id != -1:
                # Calculate total pot (2x bet amount since bot also "bet")
                total_pot = game.bet_amount * 2
                # Add winnings to the player
                add_funds(winner_id, total_pot)
                
                # Get player's username for the winner announcement
                winner_name = f"@{game.player_usernames.get(winner_id, 'Player')}" if winner_id in game.player_usernames else f"Player {winner_id}"
                await query.edit_message_text(
                    f"{game.get_status_text()}\n\n🏆 {winner_name} has won {total_pot} credits! 🏆",
                    parse_mode="Markdown"
                )
                # Remove the game
                remove_betting_game(game_id)
                return True
                
            # Regular multiplayer game
            else:
                success, message, amount = settle_bet(game_id, winner_id)
                if success:
                    # Get winner username for direct mention
                    winner_name = "Unknown"
                    if winner_id == -1:
                        winner_name = "🤖 Bot"
                    elif winner_id in game.player_usernames:
                        winner_name = f"@{game.player_usernames[winner_id]}"
                    else:
                        winner_name = f"Player {winner_id}"
                    
                    # Create a custom message that mentions the winner by username
                    winner_announcement = f"🏆 {winner_name} has won {amount} credits! 🏆"
                    
                    # Update all players with the final result including winner mention
                    for player_id, message_info in game.player_messages.items():
                        if player_id != user_id:  # Skip the current user, they're handled by the query
                            try:
                                chat_id, message_id = message_info
                                await context.bot.edit_message_text(
                                    f"{game.get_status_text()}\n\n{winner_announcement}",
                                    chat_id=chat_id,
                                    message_id=message_id,
                                    parse_mode="Markdown"
                                )
                            except Exception as e:
                                print(f"Error updating player {player_id}: {e}")
                    
                    # Update the current player's message
                    await query.edit_message_text(
                        f"{game.get_status_text()}\n\n{winner_announcement}",
                        parse_mode="Markdown"
                    )
                    # Remove the game
                    remove_betting_game(game_id)
                    return True
                else:
                    await query.edit_message_text(
                        f"{game.get_status_text()}\n\nError settling bet: {message}",
                        parse_mode="Markdown"
                    )
                    return True
        except Exception as e:
            # Log the error for debugging
            print(f"Error handling game completion: {e}")
            # Try to show a simple error message to the user
            try:
                await query.answer(f"An error occurred while processing the game result. Please try again.", show_alert=True)
            except:
                pass
            return True
    else:
        # Game is still in progress
        # Include the instructions in the message if they exist
        # Make sure game exists before getting its status text
        if game:
            message_text = game.get_status_text()
            if instructions:
                message_text += f"\n\n{instructions}"
        else:
            # Fallback message if game is none
            message_text = "Game information is no longer available."
        
        # Update current player's message
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Update all other players to show that this player has moved
        # Only proceed if game is not None
        if game:
            for player_id, message_info in game.player_messages.items():
                if player_id != user_id:  # Skip the current user, they're handled by the query
                    try:
                        chat_id, message_id = message_info
                        # Create player-specific controls for each player
                        player_keyboard = create_game_controls(game, player_id)
                        player_reply_markup = InlineKeyboardMarkup(player_keyboard) if player_keyboard else None
                        
                        # Create player-specific message
                        player_message = game.get_status_text()
                        
                        # Add a clear instruction message at the top for the second player
                        if player_id not in game.player_moves:
                            player_message = "🚨 *YOUR TURN* - MAKE YOUR MOVE BELOW! 🚨\n\n" + player_message
                        
                        # Create a personalized message including who made the move
                        mover_name = "Someone"
                        # Try to get the proper name for the player who moved
                        if user_id in game.player_full_names:
                            mover_name = game.player_full_names[user_id]
                        elif user_id in game.player_names:
                            mover_name = game.player_names[user_id]
                        elif user_id in game.player_usernames:
                            mover_name = f"@{game.player_usernames[user_id]}"
                            
                        # Create a proper mention with user's ID for notifications
                        # Format: [User Name](tg://user?id=123456789)
                        mover_mention = f"[{mover_name}](tg://user?id={user_id})"
                        
                        # Different message for players who have moved vs haven't moved
                        if player_id in game.player_moves:
                            # Don't mention "check game result" button - it's been removed from the interface
                            player_message += "\n\nYour move has been recorded. Results will be shown automatically when all players have moved."
                        else:
                            # Show who made a move with proper mention by ID
                            move_description = ""
                            move = game.player_moves.get(user_id)
                            if game.game_type == GameType.DICE_ROLL:
                                move_description = f"rolled a 🎲 {move}"
                            elif game.game_type == GameType.COIN_FLIP:
                                move_str = move.capitalize() if hasattr(move, 'capitalize') else str(move).capitalize()
                                move_description = f"chose {move_str}"
                            elif game.game_type == GameType.NUMBER_GUESS:
                                move_description = f"picked the number {move}"
                            elif game.game_type == GameType.ROCK_PAPER_SCISSORS:
                                move_name = move.value.capitalize() if hasattr(move, 'value') else str(move).capitalize()
                                move_description = f"chose {move_name}"
                            
                            # Get the current player's name/username for personalized message
                            player_name = "Unknown Player"
                            if player_id in game.player_full_names:
                                player_name = game.player_full_names[player_id]
                            elif player_id in game.player_names:
                                player_name = game.player_names[player_id]
                            elif player_id in game.player_usernames:
                                player_name = f"@{game.player_usernames[player_id]}"
                            
                            player_message += f"\n\n{mover_mention} has {move_description}. It's {player_name}'s turn now!"
                        
                        await context.bot.edit_message_text(
                            player_message,
                            chat_id=chat_id,
                            message_id=message_id,
                            reply_markup=player_reply_markup,
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        print(f"Error updating player {player_id}: {e}")
    
    return True

async def process_cancel_game(query, game_id: str, user_id: int) -> bool:
    """Process a request to cancel a betting game."""
    game = get_betting_game(game_id)
    if not game:
        await query.edit_message_text("This game no longer exists.")
        return True
    
    # Only the creator can cancel the game
    if user_id != game.creator_id:
        # Just acknowledge the query but don't change anything for non-creators
        await query.answer("Only the game creator can cancel this game", show_alert=True)
        return True
    
    # Handle single-player games differently
    if game.single_player:
        # Refund the bet amount to the creator
        add_funds(user_id, game.bet_amount)
        
        # Remove the game
        remove_betting_game(game_id)
        await query.edit_message_text(
            f"Game {game_id} has been canceled. Your {game.bet_amount} credits have been refunded."
        )
    else:
        # Cancel the bet in the wallet system (for multiplayer games)
        success, message = cancel_bet(game_id, user_id)
        if success:
            # Remove the game
            remove_betting_game(game_id)
            await query.edit_message_text(
                f"Game {game_id} has been canceled. {message}"
            )
        else:
            await query.edit_message_text(
                f"{game.get_status_text()}\n\nError canceling game: {message}"
            )
    
    return True
    
async def process_refresh_game(query, game_id: str, user_id: int) -> bool:
    """Process a request to refresh a betting game status."""
    game = get_betting_game(game_id)
    if not game:
        await query.answer("This game no longer exists.", show_alert=True)
        return True
    
    # Check if user is in the game
    if user_id not in game.players:
        # Just acknowledge the query but don't change anything for non-participants
        await query.answer("You're not part of this game", show_alert=True)
        return True
    
    # Get current game status information    
    players_moved = len(game.player_moves)
    total_players = len(game.players)
    
    # Store this message's chat_id and message_id for the current player
    # This ensures we have the latest message info for updates
    message_info = (query.message.chat_id, query.message.message_id)
    game.player_messages[user_id] = message_info
    
    # Always update the UI to reflect the current game state, regardless of popup message
    keyboard = create_game_controls(game, user_id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Determine what status information to show in popup alert
    status_popup = ""
    
    # Create different popup messages based on game state
    if game.state == GameState.WAITING_FOR_MOVES:
        # Check if user has already made a move
        if user_id in game.player_moves:
            # Player already moved - show simple status in popup
            move = game.player_moves.get(user_id)
            
            # Format move description based on game type
            if game.game_type == GameType.DICE_ROLL:
                move_desc = f"You rolled a 🎲 {move}"
            elif game.game_type == GameType.COIN_FLIP:
                move_str = move if not move else move.capitalize()
                move_desc = f"You chose {move_str}"
            elif game.game_type == GameType.NUMBER_GUESS:
                move_desc = f"You picked number {move}"
            elif game.game_type == GameType.ROCK_PAPER_SCISSORS:
                if hasattr(move, 'value'):
                    move_str = move.value.capitalize()
                else:
                    move_str = str(move).capitalize() if move else "unknown"
                move_desc = f"You chose {move_str}"
            else:
                move_desc = "You made your move"
            
            # Game status information
            if players_moved == total_players:
                status_popup = f"Game Status: {move_desc}. All players have moved! Game will resolve shortly."
            else:
                status_popup = f"Game Status: {move_desc}. Waiting for other player to move ({players_moved}/{total_players} players ready)."
                
            # Show popup alert
            await query.answer(status_popup, show_alert=True)
            
            # Update the message text & UI to show current game state
            status_msg = f"You've already made your move. Waiting for other players ({players_moved}/{total_players})."
            await query.edit_message_text(
                f"{game.get_status_text()}\n\n{status_msg}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            # Player hasn't moved yet - prompt them to make a move
            status_popup = f"Game Status: It's your turn to make a move ({players_moved}/{total_players} players ready)."
            await query.answer(status_popup, show_alert=True)
            
            # Update UI with move options
            status_msg = "🚨 YOUR TURN - MAKE A MOVE NOW! 🚨\n\nIt's your turn to make a move. Please select one of the options below."
            await query.edit_message_text(
                f"{game.get_status_text()}\n\n{status_msg}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    elif game.state == GameState.GAME_OVER:
        # Game is over - show status in popup alert
        status_popup = f"Game is over! Winner: {game.winner_id}"
        if game.winner_id in game.player_usernames:
            winner_name = f"@{game.player_usernames[game.winner_id]}"
            status_popup = f"Game over! Winner: {winner_name}"
        
        await query.answer(status_popup, show_alert=True)
        
        # Update to show final game state
        await query.edit_message_text(
            game.get_status_text(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # Other states (waiting for player)
        status_popup = f"Game Status: {game.state.name}. {players_moved}/{total_players} players have moved."
        await query.answer(status_popup, show_alert=True)
        
        # Update UI to match current state
        await query.edit_message_text(
            game.get_status_text(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return True

def create_game_controls(game: BettingGame, user_id: int) -> List[List[InlineKeyboardButton]]:
    """
    Create appropriate controls for the current game state.
    
    This function creates a custom interface for each player based on:
    1. The current game state
    2. Whether they are the creator
    3. Whether they have made their move already
    
    Each player has their own view of the game.
    """
    keyboard = []
    
    if game.state == GameState.WAITING_FOR_PLAYER:
        # Always show Join Game button when the game is waiting for players
        # This ensures other players can join even if the creator has viewed their own game
        keyboard = [
            [InlineKeyboardButton("Join Game", callback_data=f"{BTN_JOIN_GAME}:{game.game_id}")],
            [InlineKeyboardButton("Cancel Game", callback_data=f"{BTN_CANCEL_GAME}:{game.game_id}")]
        ]
        
        # If user is already in the game, don't show them anything special
        # Instead, when they try to join, we'll show them an alert message
    
    elif game.state == GameState.WAITING_FOR_MOVES:
        # For ALL move buttons, include the player status info
        players_moved = len(game.player_moves)
        total_players = len(game.players)
        status_text = f"{players_moved}/{total_players} players have moved"
        
        # Common status button
        status_button = [InlineKeyboardButton(status_text, callback_data="none")]
        
        # Much simpler interface - show player buttons
        players_list = list(game.players)
        player1_id = players_list[0] if len(players_list) > 0 else None
        player2_id = players_list[1] if len(players_list) > 1 else None
        
        # Get usernames if available
        player1_name = f"@{game.player_usernames.get(player1_id, 'Player 1')}" if player1_id else "Player 1"
        player2_name = f"@{game.player_usernames.get(player2_id, 'Player 2')}" if player2_id else "Player 2"
        
        # Show if players have moved
        player1_status = "✅ Made move" if player1_id in game.player_moves else "⏳ Waiting"
        player2_status = "✅ Made move" if player2_id in game.player_moves else "⏳ Waiting"
        
        # Create buttons for each player
        player1_button = InlineKeyboardButton(f"{player1_name}: {player1_status}", callback_data="none")
        player2_button = InlineKeyboardButton(f"{player2_name}: {player2_status}", callback_data="none")
        
        # Show different UI based on whether user has made their move and game state
        if user_id not in game.player_moves and game.state == GameState.WAITING_FOR_MOVES:
            # User hasn't made a move yet and game is waiting for moves
            # Create multiple move options based on game type
            if game.game_type == GameType.DICE_ROLL:
                # For dice, simple single button
                move_button = InlineKeyboardButton("🎲 Roll Dice", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:roll")
                move_buttons = [[move_button]]
            elif game.game_type == GameType.COIN_FLIP:
                # For coin flip, show both options directly
                heads_button = InlineKeyboardButton("Heads", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:heads")
                tails_button = InlineKeyboardButton("Tails", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:tails")
                move_buttons = [[heads_button, tails_button]]
            elif game.game_type == GameType.ROCK_PAPER_SCISSORS:
                # For RPS, show all three options
                rock_button = InlineKeyboardButton("Rock 👊", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:rock")
                paper_button = InlineKeyboardButton("Paper 🖐", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:paper")
                scissors_button = InlineKeyboardButton("Scissors ✂️", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:scissors")
                move_buttons = [[rock_button], [paper_button], [scissors_button]]
            elif game.game_type == GameType.NUMBER_GUESS:
                # For number guess, show 5 options in 2 rows
                move_buttons = [
                    [
                        InlineKeyboardButton("1️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:1"),
                        InlineKeyboardButton("2️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:2"),
                        InlineKeyboardButton("3️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:3"),
                        InlineKeyboardButton("4️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:4"),
                        InlineKeyboardButton("5️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:5"),
                    ],
                    [
                        InlineKeyboardButton("6️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:6"),
                        InlineKeyboardButton("7️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:7"),
                        InlineKeyboardButton("8️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:8"),
                        InlineKeyboardButton("9️⃣", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:9"),
                        InlineKeyboardButton("🔟", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:10"),
                    ]
                ]
            else:
                # Default fallback for unknown game types
                move_button = InlineKeyboardButton("Make Move", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:default")
                move_buttons = [[move_button]]
                
            # Start with player status buttons
            keyboard = [
                [player1_button], 
                [player2_button]
            ]
            
            # Add game instruction
            your_turn_button = InlineKeyboardButton("▶️ Your Turn - Choose Your Move ▶️", callback_data="none")
            keyboard.append([your_turn_button])
            
            # Add all move buttons
            keyboard.extend(move_buttons)
            
            # Add refresh button at the bottom
            keyboard.append([InlineKeyboardButton("↻ Refresh", callback_data=f"refresh:{game.game_id}")])
        else:
            # Either user already made their move or game is not in the waiting for moves state
            # Show the player status and a refresh button only - no move buttons
            keyboard = [
                [player1_button], 
                [player2_button],
                [InlineKeyboardButton("↻ Refresh Status", callback_data=f"refresh:{game.game_id}")]
            ]
    
    # Add cancel button if game is not over, but only in certain states
    # In WAITING_FOR_PLAYER, it's already added above
    # In WAITING_FOR_MOVES, only show Cancel button for creator on their main game view (not after refresh)
    if (game.state == GameState.WAITING_FOR_MOVES and 
        game.creator_id == user_id and 
        user_id not in game.player_moves):
        keyboard.append([InlineKeyboardButton("Cancel Game", callback_data=f"{BTN_CANCEL_GAME}:{game.game_id}")])
    
    return keyboard

# Direct game command handlers
async def dice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Quick command to play a dice game against the bot.
    Format: /dice [amount]
    Default amount: 100 credits
    """
    # Set up bet amount (default or specified)
    bet_amount = DEFAULT_BET_AMOUNT
    if context.args:
        try:
            bet_amount = int(context.args[0])
            if bet_amount <= 0:
                await update.message.reply_text("Bet amount must be greater than 0.")
                return
        except ValueError:
            await update.message.reply_text("Bet amount must be a number.")
            return
    
    # Prepare arguments for the bet command
    context.args = ["dice", str(bet_amount), "solo"]
    await bet_command(update, context)

async def coin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Quick command to play a coin flip game against the bot.
    Format: /coin [amount]
    Default amount: 100 credits
    """
    # Set up bet amount (default or specified)
    bet_amount = DEFAULT_BET_AMOUNT
    if context.args:
        try:
            bet_amount = int(context.args[0])
            if bet_amount <= 0:
                await update.message.reply_text("Bet amount must be greater than 0.")
                return
        except ValueError:
            await update.message.reply_text("Bet amount must be a number.")
            return
    
    # Prepare arguments for the bet command
    context.args = ["coin", str(bet_amount), "solo"]
    await bet_command(update, context)

async def number_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Quick command to play a number guessing game against the bot.
    Format: /number [amount]
    Default amount: 100 credits
    """
    # Set up bet amount (default or specified)
    bet_amount = DEFAULT_BET_AMOUNT
    if context.args:
        try:
            bet_amount = int(context.args[0])
            if bet_amount <= 0:
                await update.message.reply_text("Bet amount must be greater than 0.")
                return
        except ValueError:
            await update.message.reply_text("Bet amount must be a number.")
            return
    
    # Prepare arguments for the bet command
    context.args = ["number", str(bet_amount), "solo"]
    await bet_command(update, context)

async def rps_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Quick command to play rock-paper-scissors against the bot.
    Format: /rps [amount]
    Default amount: 100 credits
    """
    # Set up bet amount (default or specified)
    bet_amount = DEFAULT_BET_AMOUNT
    if context.args:
        try:
            bet_amount = int(context.args[0])
            if bet_amount <= 0:
                await update.message.reply_text("Bet amount must be greater than 0.")
                return
        except ValueError:
            await update.message.reply_text("Bet amount must be a number.")
            return
    
    # Prepare arguments for the bet command
    context.args = ["rps", str(bet_amount), "solo"]
    await bet_command(update, context)