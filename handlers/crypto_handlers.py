"""
Cryptocurrency integration handlers for the Telegram Bot.
This provides integration with @cctip_bot for real cryptocurrency betting
using a proxy account payment system.
"""
import re
import time
import logging
import uuid
from typing import Tuple, Dict, Optional, List
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from betting_game import GameType, create_betting_game, get_betting_game, remove_betting_game
from wallet_system import add_funds, deduct_funds, create_bet, settle_bet, get_balance

# Constants for crypto integration
CCTIP_BOT_USERNAME = "cctip_bot"
VERIFIED_TRANSACTIONS = {}  # Store verified transactions {tx_hash: details}
PENDING_BETS = {}  # Store pending bets waiting for payment {bet_id: bet_details}

# The proxy account receiving all payments (this should be the admin's username without @ symbol)
PROXY_ACCOUNT = "gpt_92lbot"  # Change this to the admin's username without @ symbol

# Supported cryptocurrencies and their minimum values (in USD)
SUPPORTED_CRYPTOCURRENCIES = {
    "doge": 1.0,    # Min $1 of Dogecoin
    "trx": 1.0,     # Min $1 of Tron
    "usdt": 1.0,    # Min $1 of USDT
    "bnb": 1.0,     # Min $1 of BNB
}

logger = logging.getLogger(__name__)

async def crypto_bet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start a crypto betting game using real cryptocurrency via @cctip_bot.
    Format: /cryptobet <game_type> <amount> <crypto>
    Examples: 
      /cryptobet dice 1 doge
      /cryptobet coin 5 usdt
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    
    # Check if we have enough arguments
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Please specify a game type, bet amount, and cryptocurrency.\n"
            "Example: /cryptobet dice 1 doge\n\n"
            f"Available games: dice, coin, number, rps\n"
            f"Supported cryptocurrencies: {', '.join(SUPPORTED_CRYPTOCURRENCIES.keys())}"
        )
        return
    
    # Parse args
    game_type_str = context.args[0].lower()
    
    try:
        bet_amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Bet amount must be a number.")
        return
    
    crypto = context.args[2].lower()
    
    # Validate crypto
    if crypto not in SUPPORTED_CRYPTOCURRENCIES:
        await update.message.reply_text(
            f"Unsupported cryptocurrency. Please use one of: {', '.join(SUPPORTED_CRYPTOCURRENCIES.keys())}"
        )
        return
    
    # Check minimum bet amount
    min_amount = SUPPORTED_CRYPTOCURRENCIES[crypto]
    if bet_amount < min_amount:
        await update.message.reply_text(
            f"Minimum bet amount for {crypto.upper()} is {min_amount} {crypto.upper()}"
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
    
    # Create a unique identifier for this bet
    timestamp = int(time.time())
    bet_id = f"crypto_{game_type_str}_{user_id}_{timestamp}"
    
    # Generate the tip message for cctip_bot
    if not username:
        await update.message.reply_text("You need to have a Telegram username to use crypto betting.")
        return
    
    # We'll create a betting game with a special ID that we can track
    multiplier = 2  # This could vary based on game type or other rules
    
    # Create the message text that will instruct how to pay
    # We'll use the proxy account (admin) to receive the tip with a unique ID in the memo
    tip_command = f"/tip @{PROXY_ACCOUNT} {bet_amount} {crypto} crypto_{game_type_str}_{user_id}_{timestamp}"
    
    # Create plain text version to avoid markdown parsing issues
    tip_text = (
        f"🎮 Crypto Betting Game: {game_type_str.upper()}\n\n"
        f"To place a bet of {bet_amount} {crypto.upper()}, send this command:\n\n"
        f"{tip_command}\n\n"
        f"💰 Potential Winnings: {bet_amount * multiplier} {crypto.upper()}\n\n"
        f"After sending the tip, the game will start automatically.\n"
        f"Note: This uses real cryptocurrency via @{CCTIP_BOT_USERNAME}."
    )
    
    # Create a button to open chat with cctip_bot
    keyboard = [
        [InlineKeyboardButton("Open @cctip_bot", url=f"https://t.me/{CCTIP_BOT_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store the pending bet details
    message = await update.message.reply_text(
        tip_text,
        reply_markup=reply_markup
    )
    
    # Store pending bet information
    PENDING_BETS[f"{chat_id}_{message.message_id}"] = {
        "bet_id": bet_id,
        "user_id": user_id,
        "game_type": game_type,
        "amount": bet_amount,
        "crypto": crypto,
        "timestamp": timestamp,
        "status": "pending"
    }
    
    logger.info(f"Created pending crypto bet: {bet_id} for user {user_id}")

async def handle_possible_crypto_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if a message is a confirmed payment from cctip_bot and process it.
    Returns True if the message was a crypto payment, False otherwise.
    """
    message = update.effective_message
    
    # Check if message is from cctip_bot or mentions cctip_bot
    if not message or not message.text:
        return False
    
    is_from_cctip = message.from_user and message.from_user.username == CCTIP_BOT_USERNAME
    mentions_cctip = f"@{CCTIP_BOT_USERNAME}" in message.text
    
    if not (is_from_cctip or mentions_cctip):
        return False
    
    # Look for tip confirmation patterns
    # Example: "✅ @user1 tipped @user2 1.0 DOGE ($0.12)"
    tip_pattern = r"✅\s+@(\w+)\s+tipped\s+@(\w+)\s+([\d\.]+)\s+([A-Z]+)"
    match = re.search(tip_pattern, message.text)
    
    if match:
        sender = match.group(1)
        recipient = match.group(2)
        amount = float(match.group(3))
        crypto = match.group(4).lower()
        
        # Check if the recipient is our proxy account
        if recipient.lower() == PROXY_ACCOUNT.lower():
            # Try to extract the bet_id from the message
            # Expecting format like "✅ @user1 tipped @proxy_account 1.0 DOGE ($0.12) crypto_dice_123456789_1616161616"
            msg_parts = message.text.split()
            bet_id = None
            
            # Look for the bet_id in the message
            for part in msg_parts:
                if part.startswith("crypto_"):
                    bet_id = part.strip()
                    break
            
            if bet_id:
                # Process the payment - we trust the cctip_bot confirmation
                # Extract the user_id from the bet_id directly (format: crypto_game_type_user_id_timestamp)
                try:
                    parts = bet_id.split('_')
                    if len(parts) >= 4:
                        # Process the payment regardless of whether we have a pending bet
                        # This allows for more flexibility in handling payments
                        await process_crypto_payment(
                            context,
                            sender=sender,
                            bet_id=bet_id,
                            amount=amount,
                            crypto=crypto,
                            message=message
                        )
                    else:
                        logger.warning(f"Invalid bet_id format: {bet_id}")
                except Exception as e:
                    logger.error(f"Error processing crypto payment: {e}")
                    await message.reply_text("Error processing payment. Please contact support.")
                return True
    
    return False

async def process_crypto_payment(context, sender: str, bet_id: str, amount: float, 
                                crypto: str, message) -> None:
    """Process a verified crypto payment and start the appropriate game."""
    logger.info(f"Processing crypto payment from @{sender}: {amount} {crypto} for bet_id {bet_id}")
    
    # Extract details from bet_id
    # Format: crypto_<game_type>_<user_id>_<timestamp>
    parts = bet_id.split('_')
    
    if len(parts) < 4:
        await message.reply_text("Invalid bet ID format. Payment cannot be processed.")
        return
    
    game_type_str = parts[1]
    user_id = int(parts[2])
    
    # Add virtual funds to user's wallet based on the crypto amount
    # For simplicity, we're using a 1:100 ratio (1 DOGE = 100 credits)
    virtual_amount = int(amount * 100)
    success, new_balance = add_funds(user_id, virtual_amount)
    
    if not success:
        await message.reply_text("Error processing payment. Please contact support.")
        return
    
    # Store the transaction
    tx_hash = f"{sender}_{crypto}_{amount}_{int(time.time())}"
    VERIFIED_TRANSACTIONS[tx_hash] = {
        "bet_id": bet_id,
        "sender": sender,
        "amount": amount,
        "crypto": crypto,
        "virtual_amount": virtual_amount,
        "timestamp": datetime.now(),
        "status": "processed"
    }
    
    # Create the game
    game_type = None
    if game_type_str == "dice":
        game_type = GameType.DICE_ROLL
    elif game_type_str == "coin":
        game_type = GameType.COIN_FLIP
    elif game_type_str == "number":
        game_type = GameType.NUMBER_GUESS
    elif game_type_str in ["rps", "rock", "paper", "scissors"]:
        game_type = GameType.ROCK_PAPER_SCISSORS
    
    # Create the betting game (single player vs. bot)
    game = create_betting_game(game_type, user_id, virtual_amount, single_player=True)
    
    # Create appropriate game buttons
    keyboard = []
    
    if game_type == GameType.DICE_ROLL:
        # Dice game - player just rolls
        keyboard = [[InlineKeyboardButton("🎲 Roll Dice", callback_data=f"betting_game_move:{game.game_id}:roll")]]
    
    elif game_type == GameType.COIN_FLIP:
        # Coin flip - player guesses heads or tails
        keyboard = [
            [
                InlineKeyboardButton("Heads", callback_data=f"betting_game_move:{game.game_id}:heads"),
                InlineKeyboardButton("Tails", callback_data=f"betting_game_move:{game.game_id}:tails")
            ]
        ]
        
    elif game_type == GameType.NUMBER_GUESS:
        # Number guessing - provide number buttons 1-10
        row1 = [InlineKeyboardButton(str(i), callback_data=f"betting_game_move:{game.game_id}:{i}") for i in range(1, 6)]
        row2 = [InlineKeyboardButton(str(i), callback_data=f"betting_game_move:{game.game_id}:{i}") for i in range(6, 11)]
        keyboard = [row1, row2]
        
    elif game_type == GameType.ROCK_PAPER_SCISSORS:
        # Rock Paper Scissors - provide RPS buttons
        keyboard = [
            [
                InlineKeyboardButton("🪨 Rock", callback_data=f"betting_game_move:{game.game_id}:rock"),
                InlineKeyboardButton("📄 Paper", callback_data=f"betting_game_move:{game.game_id}:paper"),
                InlineKeyboardButton("✂️ Scissors", callback_data=f"betting_game_move:{game.game_id}:scissors")
            ]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send acknowledgment and game start using plain text
    await message.reply_text(
        f"💰 Received {amount} {crypto.upper()} from @{sender}!\n"
        f"Added {virtual_amount} credits to your wallet.\n\n"
        f"🎮 Starting {game_type_str.upper()} game\n"
        f"Your bet: {virtual_amount} credits\n"
        f"Potential win: {virtual_amount * 2} credits",
        reply_markup=reply_markup
    )

async def crypto_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show information about crypto betting.
    Format: /cinfo
    """
    # Create a comprehensive guide to crypto betting
    crypto_info_text = """
🪙 **CRYPTO BETTING GUIDE** 🪙

Welcome to real cryptocurrency betting through Telegram! This system allows you to bet with actual cryptocurrency (DOGE, TRX, USDT, BNB) on various games.

📱 **GETTING STARTED**
1. First, you need a Telegram username (required for tipping)
2. You need a balance in @cctip_bot (create an account if you don't have one)

🎮 **AVAILABLE GAMES**
• `/cryptobet dice <amount> <crypto>` - Roll a dice, 4-6 wins
• `/cryptobet coin <amount> <crypto>` - Flip a coin, guess heads/tails
• `/cryptobet number <amount> <crypto>` - Guess a number between 1-10
• `/cryptobet rps <amount> <crypto>` - Play Rock-Paper-Scissors

💰 **SUPPORTED CRYPTOCURRENCIES**
• DOGE (Dogecoin) - min 1.0 DOGE
• TRX (Tron) - min 1.0 TRX
• USDT (Tether) - min 1.0 USDT
• BNB (Binance Coin) - min 1.0 BNB

🎯 **HOW TO PLAY**
1. Send a command like: `/cryptobet dice 1 doge`
2. The bot will generate a special tip command
3. Send that command to @cctip_bot (button provided)
4. Once the payment is confirmed in the group chat, your game starts automatically
5. Make your move using the buttons that appear
6. Win or lose, the results are instant!

💸 **CONVERSION RATE**
• 1 crypto unit = 100 credits in the game
• Example: 1 DOGE = 100 betting credits

⚠️ **IMPORTANT NOTES**
• All bets are final and non-refundable
• Cryptocurrency values fluctuate; bet responsibly
• The system uses @cctip_bot for all transactions
• Admin account receives crypto payments via proxy system
• All game results are provably fair and random

Have fun and good luck! 🍀
"""
    
    # Create a button to open cctip_bot
    keyboard = [
        [InlineKeyboardButton("Setup @cctip_bot", url=f"https://t.me/{CCTIP_BOT_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the information
    try:
        await update.message.reply_text(
            crypto_info_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        # Fallback to plain text if markdown fails
        await update.message.reply_text(
            crypto_info_text.replace("**", "").replace("*", ""),
            reply_markup=reply_markup
        )

def register_crypto_handlers(application):
    """Register all crypto-related handlers."""
    from telegram.ext import CommandHandler, MessageHandler, filters
    
    # Add crypto bet command
    application.add_handler(CommandHandler("cryptobet", crypto_bet_command))
    
    # Add crypto info command
    application.add_handler(CommandHandler("cinfo", crypto_info_command))
    
    # Add handler to detect cctip_bot payments - this needs to be checked before 
    # the regular message handler for AI responses
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            lambda update, context: handle_possible_crypto_payment(update, context),
            block=False  # Allow other handlers to process if this returns False
        )
    )