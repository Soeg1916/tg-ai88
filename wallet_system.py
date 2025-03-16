"""
Wallet system for tracking user balances in the Telegram bot.
This is a virtual wallet system for testing purposes only - no real money is involved.
"""
import json
import os
import logging
from typing import Dict, Tuple, Optional, List

# Constants
DEFAULT_BALANCE = 1000  # Default starting balance
WALLET_FILE = "user_wallets.json"

# Data structures
wallets = {}  # {user_id: balance}
active_bets = {}  # {bet_id: {creator_id, amount, participants: {user_id: amount}}}

logger = logging.getLogger(__name__)

def load_wallets() -> None:
    """Load wallet data from file."""
    global wallets, active_bets
    
    if os.path.exists(WALLET_FILE):
        try:
            with open(WALLET_FILE, 'r') as f:
                data = json.load(f)
                wallets = data.get('wallets', {})
                active_bets = data.get('active_bets', {})
                
                # Convert string keys to integers for user IDs
                wallets = {int(k): v for k, v in wallets.items()}
                active_bets = {
                    k: {
                        'creator_id': int(v['creator_id']),
                        'amount': v['amount'],
                        'participants': {int(p): a for p, a in v['participants'].items()}
                    } 
                    for k, v in active_bets.items()
                }
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading wallet data: {e}")
            # Initialize empty data
            wallets = {}
            active_bets = {}

def save_wallets() -> None:
    """Save wallet data to file."""
    data = {
        'wallets': wallets,
        'active_bets': active_bets
    }
    
    try:
        with open(WALLET_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving wallet data: {e}")

def get_balance(user_id: int) -> int:
    """Get the current balance for a user."""
    if user_id not in wallets:
        wallets[user_id] = DEFAULT_BALANCE
        save_wallets()
    
    return wallets[user_id]

def add_funds(user_id: int, amount: int) -> Tuple[bool, int]:
    """
    Add funds to a user's wallet.
    
    Args:
        user_id: The user ID
        amount: The amount to add
        
    Returns:
        Tuple of (success, new_balance)
    """
    if amount <= 0:
        return False, get_balance(user_id)
    
    if user_id not in wallets:
        wallets[user_id] = DEFAULT_BALANCE
    
    wallets[user_id] += amount
    save_wallets()
    
    return True, wallets[user_id]

def deduct_funds(user_id: int, amount: int) -> Tuple[bool, int]:
    """
    Deduct funds from a user's wallet.
    
    Args:
        user_id: The user ID
        amount: The amount to deduct
        
    Returns:
        Tuple of (success, new_balance)
    """
    if amount <= 0:
        return False, get_balance(user_id)
    
    if user_id not in wallets:
        wallets[user_id] = DEFAULT_BALANCE
    
    if wallets[user_id] < amount:
        return False, wallets[user_id]
    
    wallets[user_id] -= amount
    save_wallets()
    
    return True, wallets[user_id]

def create_bet(bet_id: str, user_id: int, amount: int) -> Tuple[bool, str]:
    """
    Create a new bet.
    
    Args:
        bet_id: The unique ID for this bet
        user_id: The user ID creating the bet
        amount: The amount to bet
        
    Returns:
        Tuple of (success, message)
    """
    # Check if bet ID already exists
    if bet_id in active_bets:
        return False, "A bet with this ID already exists."
    
    # Check if user has enough balance
    if get_balance(user_id) < amount:
        return False, "You don't have enough credits for this bet."
    
    # Deduct funds
    success, _ = deduct_funds(user_id, amount)
    if not success:
        return False, "Failed to deduct funds."
    
    # Create bet
    active_bets[bet_id] = {
        'creator_id': user_id,
        'amount': amount,
        'participants': {
            user_id: amount
        }
    }
    save_wallets()
    
    return True, "Bet created successfully."

def join_bet(bet_id: str, user_id: int, amount: int) -> Tuple[bool, str]:
    """
    Join an existing bet.
    
    Args:
        bet_id: The unique ID for this bet
        user_id: The user ID joining the bet
        amount: The amount to bet
        
    Returns:
        Tuple of (success, message)
    """
    # Check if bet exists
    if bet_id not in active_bets:
        return False, "This bet doesn't exist."
    
    # Check if user is already in the bet
    if user_id in active_bets[bet_id]['participants']:
        return False, "You're already participating in this bet."
    
    # Check if the amounts match
    if active_bets[bet_id]['amount'] != amount:
        return False, f"The bet amount is {active_bets[bet_id]['amount']}, not {amount}."
    
    # Check if user has enough balance
    if get_balance(user_id) < amount:
        return False, "You don't have enough credits for this bet."
    
    # Deduct funds
    success, _ = deduct_funds(user_id, amount)
    if not success:
        return False, "Failed to deduct funds."
    
    # Add user to bet
    active_bets[bet_id]['participants'][user_id] = amount
    save_wallets()
    
    return True, "You've joined the bet!"

def cancel_bet(bet_id: str, user_id: int) -> Tuple[bool, str]:
    """
    Cancel a bet and refund all participants.
    
    Args:
        bet_id: The bet ID to cancel
        user_id: The user ID requesting cancellation (must be the creator)
        
    Returns:
        Tuple of (success, message)
    """
    # Check if bet exists
    if bet_id not in active_bets:
        return False, "This bet doesn't exist."
    
    # Check if user is the creator
    if active_bets[bet_id]['creator_id'] != user_id:
        return False, "Only the bet creator can cancel this bet."
    
    # Refund all participants
    for participant_id, amount in active_bets[bet_id]['participants'].items():
        add_funds(participant_id, amount)
    
    # Remove the bet
    del active_bets[bet_id]
    save_wallets()
    
    return True, "Bet cancelled and all funds refunded."

def settle_bet(bet_id: str, winner_id: int) -> Tuple[bool, str, int]:
    """
    Settle a bet by declaring a winner who gets all the funds.
    
    Args:
        bet_id: The bet ID to settle
        winner_id: The winning user ID
        
    Returns:
        Tuple of (success, message, winning_amount)
    """
    # Check if bet exists
    if bet_id not in active_bets:
        return False, "This bet doesn't exist.", 0
    
    # Check if winner is a participant
    if winner_id not in active_bets[bet_id]['participants']:
        return False, "The winner is not a participant in this bet.", 0
    
    # Calculate total pot
    total_pot = sum(active_bets[bet_id]['participants'].values())
    
    # Add winnings to winner
    add_funds(winner_id, total_pot)
    
    # Remove the bet
    del active_bets[bet_id]
    save_wallets()
    
    return True, f"Congratulations! You won {total_pot} credits!", total_pot

def reset_wallet(user_id: int) -> Tuple[bool, int]:
    """
    Reset a user's wallet to the default starting balance.
    
    Args:
        user_id: The user ID
        
    Returns:
        Tuple of (success, new_balance)
    """
    wallets[user_id] = DEFAULT_BALANCE
    save_wallets()
    
    return True, DEFAULT_BALANCE

# Load data when module is imported
load_wallets()