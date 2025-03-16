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
    get_balance, add_funds, deduct_funds, create_bet, join_bet, cancel_bet, settle_bet
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
    
    await update.message.reply_markdown(help_text)

async def reset_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Reset wallet balance to default.
    Format: /resetwallet
    """
    user_id = update.effective_user.id
    success, new_balance = deduct_funds(user_id, get_balance(user_id))
    success, new_balance = add_funds(user_id, 1000)
    
    await update.message.reply_markdown(
        f"💰 Your wallet has been reset!\n\n"
        f"New Balance: *{new_balance}* credits"
    )

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
    if not any(callback_data.startswith(prefix) for prefix in [BTN_JOIN_GAME, BTN_MAKE_MOVE, BTN_CANCEL_GAME]):
        return False
    
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
        return await process_make_move(query, game_id, user_id, move)
    
    elif callback_data.startswith(BTN_CANCEL_GAME):
        # Cancel a betting game
        _, game_id = callback_data.split(":", 1)
        return await process_cancel_game(query, game_id, user_id)
    
    return False

async def process_join_game(query, game_id: str, user_id: int) -> bool:
    """Process a request to join a betting game."""
    game = get_betting_game(game_id)
    if not game:
        await query.edit_message_text("This game no longer exists.")
        return True
    
    # Check if user is already in the game
    if user_id in game.players:
        # Update the message with game controls
        keyboard = create_game_controls(game, user_id)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{game.get_status_text()}\n\nYou're already in this game! {len(game.players)}/2 players have joined.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return True
    
    # Check if game is still accepting players
    if game.state != GameState.WAITING_FOR_PLAYER:
        await query.edit_message_text(
            f"{game.get_status_text()}\n\nThis game is no longer accepting players."
        )
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
    
    # Update the message with game controls
    keyboard = create_game_controls(game, user_id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        game.get_status_text(),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return True

async def process_make_move(query, game_id: str, user_id: int, move_str: str) -> bool:
    """Process a move in a betting game."""
    game = get_betting_game(game_id)
    if not game:
        await query.edit_message_text("This game no longer exists.")
        return True
    
    # Check if user is in the game
    if user_id not in game.players:
        await query.edit_message_text(
            f"{game.get_status_text()}\n\nYou're not part of this game."
        )
        return True
    
    # Check if user already made a move
    if user_id in game.player_moves:
        # Create updated UI with the user's status
        keyboard = create_game_controls(game, user_id)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{game.get_status_text()}\n\nYou've already made your move. Waiting for other players...",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
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
    
    # Update the message with game controls
    keyboard = create_game_controls(game, user_id)
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # If game is over, settle the bet
    if game.state == GameState.GAME_OVER:
        # Ensure we have a valid winner ID (default to creator in case of issues)
        winner_id = game.winner_id if game.winner_id is not None else game.creator_id
        
        # Special handling for single-player games
        if game.single_player and winner_id == -1:
            # Bot won, no need to add funds to bot
            await query.edit_message_text(
                f"{game.get_status_text()}\n\nBetter luck next time! The bot won this round.",
                parse_mode="Markdown"
            )
            # Remove the game
            remove_betting_game(game_id)
        elif game.single_player and winner_id != -1:
            # Human player won in single-player mode
            # Calculate total pot (2x bet amount since bot also "bet")
            total_pot = game.bet_amount * 2
            # Add winnings to the player
            add_funds(winner_id, total_pot)
            await query.edit_message_text(
                f"{game.get_status_text()}\n\nCongratulations! You won {total_pot} credits!",
                parse_mode="Markdown"
            )
            # Remove the game
            remove_betting_game(game_id)
        else:
            # Regular multiplayer game
            success, message, amount = settle_bet(game_id, winner_id)
            if success:
                await query.edit_message_text(
                    f"{game.get_status_text()}\n\n{message}",
                    parse_mode="Markdown"
                )
                # Remove the game
                remove_betting_game(game_id)
            else:
                await query.edit_message_text(
                    f"{game.get_status_text()}\n\nError settling bet: {message}",
                    parse_mode="Markdown"
                )
    else:
        await query.edit_message_text(
            game.get_status_text(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return True

async def process_cancel_game(query, game_id: str, user_id: int) -> bool:
    """Process a request to cancel a betting game."""
    game = get_betting_game(game_id)
    if not game:
        await query.edit_message_text("This game no longer exists.")
        return True
    
    # Only the creator can cancel the game
    if user_id != game.creator_id:
        await query.edit_message_text(
            f"{game.get_status_text()}\n\nOnly the game creator can cancel this game."
        )
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

def create_game_controls(game: BettingGame, user_id: int) -> List[List[InlineKeyboardButton]]:
    """Create appropriate controls for the current game state."""
    keyboard = []
    
    if game.state == GameState.WAITING_FOR_PLAYER:
        # Waiting for another player to join
        # Show join button only if user is not already in the game
        if user_id not in game.players:
            keyboard = [
                [InlineKeyboardButton("Join Game", callback_data=f"{BTN_JOIN_GAME}:{game.game_id}")],
                [InlineKeyboardButton("Cancel Game", callback_data=f"{BTN_CANCEL_GAME}:{game.game_id}")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("Waiting for players...", callback_data="none")],
                [InlineKeyboardButton("Cancel Game", callback_data=f"{BTN_CANCEL_GAME}:{game.game_id}")]
            ]
    
    elif game.state == GameState.WAITING_FOR_MOVES:
        # Check if user has already made a move
        if user_id in game.player_moves:
            keyboard = [
                [InlineKeyboardButton("Waiting for other players...", callback_data="none")]
            ]
        else:
            # Add move buttons based on game type
            if game.game_type == GameType.DICE_ROLL:
                keyboard = [
                    [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:roll")]
                ]
            elif game.game_type == GameType.COIN_FLIP:
                keyboard = [
                    [
                        InlineKeyboardButton("Heads", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:heads"),
                        InlineKeyboardButton("Tails", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:tails")
                    ]
                ]
            elif game.game_type == GameType.NUMBER_GUESS:
                # Create buttons for numbers 1-10
                row1 = []
                row2 = []
                for i in range(1, 11):
                    button = InlineKeyboardButton(str(i), callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:{i}")
                    if i <= 5:
                        row1.append(button)
                    else:
                        row2.append(button)
                keyboard = [row1, row2]
            elif game.game_type == GameType.ROCK_PAPER_SCISSORS:
                keyboard = [
                    [
                        InlineKeyboardButton("Rock", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:rock"),
                        InlineKeyboardButton("Paper", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:paper"),
                        InlineKeyboardButton("Scissors", callback_data=f"{BTN_MAKE_MOVE}:{game.game_id}:scissors")
                    ]
                ]
    
    # Add cancel button if game is not over
    if game.state != GameState.GAME_OVER and game.creator_id == user_id:
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