"""
Betting game implementation for the Telegram Bot.
This allows users to bet virtual credits against each other in different games.
"""
import random
import string
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set, Any

class GameType(Enum):
    DICE_ROLL = "dice_roll"
    COIN_FLIP = "coin_flip"
    NUMBER_GUESS = "number_guess"
    ROCK_PAPER_SCISSORS = "rock_paper_scissors"

class GameState(Enum):
    WAITING_FOR_PLAYER = 0
    WAITING_FOR_MOVES = 1
    GAME_OVER = 2

class PlayerMove(Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"

# Store active betting games: {game_id: BettingGame}
active_betting_games = {}

def generate_game_id() -> str:
    """Generate a unique game ID."""
    chars = string.ascii_uppercase + string.digits
    while True:
        game_id = ''.join(random.choice(chars) for _ in range(6))
        if game_id not in active_betting_games:
            return game_id
        # In the extremely unlikely case of a collision, try again

class BettingGame:
    def __init__(self, game_type: GameType, creator_id: int, bet_amount: int, single_player: bool = False):
        """
        Initialize a betting game.
        
        Args:
            game_type: The type of game
            creator_id: The user ID of the game creator
            bet_amount: The amount to bet
            single_player: Whether this is a single-player game vs the bot
        """
        self.game_id = generate_game_id()
        self.game_type = game_type
        self.creator_id = creator_id
        self.single_player = single_player
        self.bet_amount = bet_amount
        self.players = {creator_id}  # Set of player IDs
        self.player_moves = {}  # {player_id: move}
        self.results = {}  # {player_id: result}
        self.winner_id = None
        
        # For single-player games, add a bot player automatically
        if single_player:
            self.players.add(-1)  # -1 represents the bot
            self.state = GameState.WAITING_FOR_MOVES
        else:
            self.state = GameState.WAITING_FOR_PLAYER
        
        # Specific game settings
        if game_type == GameType.NUMBER_GUESS:
            self.target_number = random.randint(1, 10)
        
    def add_player(self, player_id: int) -> bool:
        """
        Add a player to the game.
        
        Args:
            player_id: The user ID to add
            
        Returns:
            bool: Whether the player was successfully added
        """
        if player_id in self.players:
            return False
            
        if self.state != GameState.WAITING_FOR_PLAYER:
            return False
            
        self.players.add(player_id)
        
        # For most games, we only need two players
        if len(self.players) >= 2:
            self.state = GameState.WAITING_FOR_MOVES
            
        return True
    
    def make_move(self, player_id: int, move: Any) -> bool:
        """
        Record a player's move.
        
        Args:
            player_id: The player making the move
            move: The move (depends on game type)
            
        Returns:
            bool: Whether the move was valid and recorded
        """
        if player_id not in self.players:
            return False
            
        if self.state != GameState.WAITING_FOR_MOVES:
            return False
            
        # Record the move
        self.player_moves[player_id] = move
        
        # Check if all players have made their moves
        if len(self.player_moves) == len(self.players):
            self._determine_winner()
            self.state = GameState.GAME_OVER
            
        return True
    
    def _determine_winner(self) -> None:
        """Determine the winner based on the game type and moves."""
        if self.game_type == GameType.DICE_ROLL:
            # Highest roll wins
            max_roll = -1
            winner = None
            
            for player_id, roll in self.player_moves.items():
                self.results[player_id] = roll
                if roll > max_roll:
                    max_roll = roll
                    winner = player_id
            
            # Handle ties (very unlikely with multiple dice)
            winners = [p for p, r in self.player_moves.items() if r == max_roll]
            if len(winners) == 1:
                self.winner_id = winners[0]
            # In case of a tie, the creator wins (for simplicity)
            else:
                self.winner_id = self.creator_id
                
        elif self.game_type == GameType.COIN_FLIP:
            # The player who guessed correctly wins
            result = random.choice(["heads", "tails"])
            
            for player_id, guess in self.player_moves.items():
                self.results[player_id] = "Correct" if guess == result else "Wrong"
                if guess == result:
                    self.winner_id = player_id
            
            # If nobody guessed correctly, the creator wins (for simplicity)
            if not self.winner_id:
                self.winner_id = self.creator_id
                
        elif self.game_type == GameType.NUMBER_GUESS:
            # Closest guess to the target number wins
            closest_diff = float('inf')
            winner = None
            
            for player_id, guess in self.player_moves.items():
                diff = abs(guess - self.target_number)
                self.results[player_id] = guess
                
                if diff < closest_diff:
                    closest_diff = diff
                    winner = player_id
                    
            self.winner_id = winner
                
        elif self.game_type == GameType.ROCK_PAPER_SCISSORS:
            # Standard rock-paper-scissors rules
            if len(self.players) != 2:
                # Rock-paper-scissors only works with exactly 2 players
                self.winner_id = self.creator_id
                return
                
            # Get the two player IDs
            player_ids = list(self.players)
            p1, p2 = player_ids[0], player_ids[1]
            
            # Get their moves
            move1 = self.player_moves.get(p1, PlayerMove.ROCK)
            move2 = self.player_moves.get(p2, PlayerMove.ROCK)
            
            # Record results
            self.results[p1] = move1
            self.results[p2] = move2
            
            # Determine winner
            if move1 == move2:
                # Tie: creator wins
                self.winner_id = self.creator_id
            elif (move1 == PlayerMove.ROCK and move2 == PlayerMove.SCISSORS) or \
                 (move1 == PlayerMove.SCISSORS and move2 == PlayerMove.PAPER) or \
                 (move1 == PlayerMove.PAPER and move2 == PlayerMove.ROCK):
                # Player 1 wins
                self.winner_id = p1
            else:
                # Player 2 wins
                self.winner_id = p2
    
    def get_status_text(self) -> str:
        """Get a text description of the current game state."""
        game_name = self.game_type.value.replace("_", " ").title()
        
        if self.state == GameState.WAITING_FOR_PLAYER:
            return (
                f"🎮 *{game_name} Betting Game*\n\n"
                f"Game ID: `{self.game_id}`\n"
                f"Bet Amount: {self.bet_amount} credits\n"
                f"Status: Waiting for opponent\n\n"
                f"Use the buttons below to join this game!"
            )
            
        elif self.state == GameState.WAITING_FOR_MOVES:
            players_moved = len(self.player_moves)
            total_players = len(self.players)
            
            return (
                f"🎮 *{game_name} Betting Game*\n\n"
                f"Game ID: `{self.game_id}`\n"
                f"Bet Amount: {self.bet_amount} credits\n"
                f"Status: Waiting for players to make moves\n"
                f"Moves Made: {players_moved}/{total_players}\n\n"
                f"Use the buttons below to make your move!"
            )
            
        elif self.state == GameState.GAME_OVER:
            result_text = ""
            
            # Format the results based on game type
            if self.game_type == GameType.DICE_ROLL:
                for player_id, roll in self.results.items():
                    player_name = f"Player {player_id}"
                    winner_mark = "🏆 " if player_id == self.winner_id else ""
                    result_text += f"{winner_mark}{player_name}: Rolled {roll}\n"
                    
            elif self.game_type == GameType.COIN_FLIP:
                for player_id, result in self.results.items():
                    player_name = f"Player {player_id}"
                    winner_mark = "🏆 " if player_id == self.winner_id else ""
                    result_text += f"{winner_mark}{player_name}: {result}\n"
                    
            elif self.game_type == GameType.NUMBER_GUESS:
                result_text += f"Target Number: {self.target_number}\n\n"
                for player_id, guess in self.results.items():
                    player_name = f"Player {player_id}"
                    winner_mark = "🏆 " if player_id == self.winner_id else ""
                    result_text += f"{winner_mark}{player_name}: Guessed {guess}\n"
                    
            elif self.game_type == GameType.ROCK_PAPER_SCISSORS:
                for player_id, move in self.results.items():
                    player_name = f"Player {player_id}"
                    winner_mark = "🏆 " if player_id == self.winner_id else ""
                    result_text += f"{winner_mark}{player_name}: {move.value}\n"
            
            # Determine winnings
            total_pot = self.bet_amount * len(self.players)
            
            # If we don't have a winner (which shouldn't happen but just in case),
            # default to the creator
            if self.winner_id is None:
                self.winner_id = self.creator_id
            
            return (
                f"🎮 *{game_name} Betting Game - FINISHED*\n\n"
                f"Game ID: `{self.game_id}`\n"
                f"Results:\n{result_text}\n"
                f"Winner: Player {self.winner_id}\n"
                f"Winnings: {total_pot} credits\n"
            )
        
        # Default case (should never reach here, but added to satisfy the return type)
        return f"🎮 *{game_name} Betting Game*\n\nGame ID: `{self.game_id}`\nStatus: Unknown state"

def create_betting_game(game_type: GameType, creator_id: int, bet_amount: int, single_player: bool = False) -> BettingGame:
    """
    Create a new betting game.
    
    Args:
        game_type: The type of game to create
        creator_id: The user ID of the creator
        bet_amount: The amount to bet
        single_player: Whether this is a single-player game versus the bot
        
    Returns:
        The newly created BettingGame
    """
    game = BettingGame(game_type, creator_id, bet_amount, single_player)
    active_betting_games[game.game_id] = game
    
    # If single player, add bot move automatically
    if single_player:
        # Bot makes a move based on game type
        if game_type == GameType.DICE_ROLL:
            bot_move = random.randint(1, 6)
        elif game_type == GameType.COIN_FLIP:
            bot_move = random.choice(["heads", "tails"])
        elif game_type == GameType.NUMBER_GUESS:
            bot_move = random.randint(1, 10)
        elif game_type == GameType.ROCK_PAPER_SCISSORS:
            bot_move = random.choice([
                PlayerMove.ROCK, 
                PlayerMove.PAPER, 
                PlayerMove.SCISSORS
            ])
        else:
            bot_move = None
            
        if bot_move is not None:
            game.make_move(-1, bot_move)  # -1 is the bot's ID
    
    return game

def get_betting_game(game_id: str) -> Optional[BettingGame]:
    """Get a betting game by ID."""
    return active_betting_games.get(game_id)

def remove_betting_game(game_id: str) -> bool:
    """Remove a betting game by ID."""
    if game_id in active_betting_games:
        del active_betting_games[game_id]
        return True
    return False