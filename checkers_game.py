"""
Checkers game implementation for Telegram Bot.
"""
import random
from enum import Enum
from typing import List, Tuple, Dict, Optional, Any

class PieceType(Enum):
    EMPTY = 0
    WHITE = 1
    BLACK = 2
    WHITE_KING = 3
    BLACK_KING = 4

class GameState(Enum):
    WAITING_FOR_PLAYER = 0
    WAITING_FOR_MOVE = 1
    GAME_OVER = 2

class CheckersGame:
    def __init__(self, user_id1: int, user_id2: Optional[int] = None):
        """
        Initialize a checkers game.
        If user_id2 is None, the opponent is the bot (AI).
        """
        self.board = self._create_board()
        self.user_id1 = user_id1  # Player 1 (WHITE)
        self.user_id2 = user_id2  # Player 2 (BLACK) or None for AI
        self.current_turn = PieceType.WHITE  # White goes first
        self.state = GameState.WAITING_FOR_PLAYER if user_id2 is None else GameState.WAITING_FOR_MOVE
        self.winner = None
        self.last_move = None
        self.move_history = []
        
    def _create_board(self) -> List[List[PieceType]]:
        """Create the initial checkers board."""
        board = [[PieceType.EMPTY for _ in range(8)] for _ in range(8)]
        
        # Set up black pieces (top of board)
        for row in range(3):
            for col in range(8):
                if (row + col) % 2 == 1:  # Only place on black squares
                    board[row][col] = PieceType.BLACK
        
        # Set up white pieces (bottom of board)
        for row in range(5, 8):
            for col in range(8):
                if (row + col) % 2 == 1:  # Only place on black squares
                    board[row][col] = PieceType.WHITE
                    
        return board
    
    def get_board_as_string(self) -> str:
        """Convert the board to a string representation for display."""
        symbols = {
            PieceType.EMPTY: "⬛" if True else "⬜",  # Black square if empty
            PieceType.WHITE: "⚪",
            PieceType.BLACK: "⚫",
            PieceType.WHITE_KING: "👑⚪",
            PieceType.BLACK_KING: "👑⚫"
        }
        
        # Add column labels (A-H)
        result = "  A B C D E F G H\n"
        
        for row_idx, row in enumerate(self.board):
            result += f"{row_idx+1} "  # Add row labels (1-8)
            
            for col_idx, piece in enumerate(row):
                # Display piece or empty square
                if piece == PieceType.EMPTY:
                    # Alternating squares for the board pattern
                    result += "⬜" if (row_idx + col_idx) % 2 == 0 else "⬛"
                else:
                    result += symbols[piece]
                
                result += " "
            result += "\n"
            
        return result
    
    def get_game_status(self) -> str:
        """Get the current game status as text."""
        if self.state == GameState.GAME_OVER:
            if self.winner == PieceType.WHITE:
                return "Game over! White (Player 1) wins! 🎉"
            elif self.winner == PieceType.BLACK:
                if self.user_id2:
                    return "Game over! Black (Player 2) wins! 🎉"
                else:
                    return "Game over! The AI wins! Try again? 🤖"
            else:
                return "Game over! It's a draw! 🤝"
        else:
            if self.current_turn == PieceType.WHITE:
                return "White's turn (Player 1) ⚪"
            else:
                if self.user_id2:
                    return "Black's turn (Player 2) ⚫"
                else:
                    return "AI is thinking... 🤖"
    
    def is_valid_move(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> bool:
        """Check if a move is valid."""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        # Check if positions are in range
        if not (0 <= from_row < 8 and 0 <= from_col < 8 and 0 <= to_row < 8 and 0 <= to_col < 8):
            return False
        
        # Check if from position has the current player's piece
        piece = self.board[from_row][from_col]
        if self.current_turn == PieceType.WHITE and piece not in [PieceType.WHITE, PieceType.WHITE_KING]:
            return False
        if self.current_turn == PieceType.BLACK and piece not in [PieceType.BLACK, PieceType.BLACK_KING]:
            return False
        
        # Check if to position is empty
        if self.board[to_row][to_col] != PieceType.EMPTY:
            return False
        
        # Check if to position is a diagonal move
        if abs(to_row - from_row) != abs(to_col - from_col):
            return False
        
        # Check movement direction based on piece type (unless it's a king)
        if piece == PieceType.WHITE and to_row > from_row:
            return False  # White can only move up
        if piece == PieceType.BLACK and to_row < from_row:
            return False  # Black can only move down
        
        # Check if it's a regular move (1 square diagonal)
        if abs(to_row - from_row) == 1:
            return True
        
        # Check if it's a jump (2 squares diagonal)
        if abs(to_row - from_row) == 2:
            # Calculate the position of the jumped piece
            jumped_row = (from_row + to_row) // 2
            jumped_col = (from_col + to_col) // 2
            jumped_piece = self.board[jumped_row][jumped_col]
            
            # Check if there's an opponent's piece to jump over
            if self.current_turn == PieceType.WHITE and jumped_piece in [PieceType.BLACK, PieceType.BLACK_KING]:
                return True
            if self.current_turn == PieceType.BLACK and jumped_piece in [PieceType.WHITE, PieceType.WHITE_KING]:
                return True
        
        return False
    
    def get_possible_moves(self, include_jumps_only: bool = False) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Get all possible moves for the current player.
        If include_jumps_only is True, only return moves that involve captures.
        """
        possible_moves = []
        
        # Look for pieces of the current player's color
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                
                # Check if it's the current player's piece
                if (self.current_turn == PieceType.WHITE and piece in [PieceType.WHITE, PieceType.WHITE_KING]) or \
                   (self.current_turn == PieceType.BLACK and piece in [PieceType.BLACK, PieceType.BLACK_KING]):
                    
                    # Check all possible move directions
                    move_directions = []
                    
                    # Regular pieces can only move in certain directions
                    if piece == PieceType.WHITE:
                        move_directions = [(-1, -1), (-1, 1)]  # Up-left, Up-right
                    elif piece == PieceType.BLACK:
                        move_directions = [(1, -1), (1, 1)]  # Down-left, Down-right
                    else:  # Kings can move in all diagonal directions
                        move_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                    
                    # Check regular moves (1 square)
                    if not include_jumps_only:
                        for dr, dc in move_directions:
                            new_row, new_col = row + dr, col + dc
                            if 0 <= new_row < 8 and 0 <= new_col < 8 and self.board[new_row][new_col] == PieceType.EMPTY:
                                possible_moves.append(((row, col), (new_row, new_col)))
                    
                    # Check jump moves (2 squares with a capture)
                    for dr, dc in move_directions:
                        new_row, new_col = row + 2*dr, col + 2*dc
                        jumped_row, jumped_col = row + dr, col + dc
                        
                        if 0 <= new_row < 8 and 0 <= new_col < 8 and self.board[new_row][new_col] == PieceType.EMPTY:
                            jumped_piece = self.board[jumped_row][jumped_col]
                            
                            # Check if jumped piece is an opponent's piece
                            if (self.current_turn == PieceType.WHITE and jumped_piece in [PieceType.BLACK, PieceType.BLACK_KING]) or \
                               (self.current_turn == PieceType.BLACK and jumped_piece in [PieceType.WHITE, PieceType.WHITE_KING]):
                                possible_moves.append(((row, col), (new_row, new_col)))
        
        return possible_moves
    
    def make_move(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> bool:
        """
        Make a move. Returns True if the move was successful.
        """
        if not self.is_valid_move(from_pos, to_pos):
            return False
        
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        # Move the piece
        piece = self.board[from_row][from_col]
        self.board[from_row][from_col] = PieceType.EMPTY
        self.board[to_row][to_col] = piece
        
        # Check if it was a jump (capture)
        captured = False
        if abs(to_row - from_row) == 2:
            # Remove the jumped piece
            jumped_row = (from_row + to_row) // 2
            jumped_col = (from_col + to_col) // 2
            self.board[jumped_row][jumped_col] = PieceType.EMPTY
            captured = True
        
        # Check if a piece should be promoted to king
        if piece == PieceType.WHITE and to_row == 0:
            self.board[to_row][to_col] = PieceType.WHITE_KING
        elif piece == PieceType.BLACK and to_row == 7:
            self.board[to_row][to_col] = PieceType.BLACK_KING
        
        # Log the move
        self.last_move = (from_pos, to_pos)
        self.move_history.append(self.last_move)
        
        # Check if there are additional jumps available from the new position
        additional_jumps = False
        if captured:
            # Check if there are more jumps from the new position
            possible_jumps = []
            
            # Get the possible directions based on piece type
            move_directions = []
            if piece == PieceType.WHITE:
                move_directions = [(-1, -1), (-1, 1)]
            elif piece == PieceType.BLACK:
                move_directions = [(1, -1), (1, 1)]
            else:  # Kings
                move_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            
            # Check each direction for a possible jump
            for dr, dc in move_directions:
                new_row, new_col = to_row + 2*dr, to_col + 2*dc
                jumped_row, jumped_col = to_row + dr, to_col + dc
                
                if 0 <= new_row < 8 and 0 <= new_col < 8 and self.board[new_row][new_col] == PieceType.EMPTY:
                    jumped_piece = self.board[jumped_row][jumped_col]
                    
                    # Check if jumped piece is an opponent's piece
                    if (self.current_turn == PieceType.WHITE and jumped_piece in [PieceType.BLACK, PieceType.BLACK_KING]) or \
                       (self.current_turn == PieceType.BLACK and jumped_piece in [PieceType.WHITE, PieceType.WHITE_KING]):
                        possible_jumps.append(((to_row, to_col), (new_row, new_col)))
            
            additional_jumps = len(possible_jumps) > 0
        
        # If no additional jumps, switch turns
        if not additional_jumps:
            self.current_turn = PieceType.BLACK if self.current_turn == PieceType.WHITE else PieceType.WHITE
            
            # Check if the game is over
            self._check_game_over()
            
            # If it's AI's turn, make the AI move
            if self.current_turn == PieceType.BLACK and self.user_id2 is None and self.state != GameState.GAME_OVER:
                self.make_ai_move()
        
        return True
    
    def make_ai_move(self):
        """Make a move for the AI player."""
        # Always prioritize jumps if available
        possible_moves = self.get_possible_moves(include_jumps_only=True)
        
        # If no jumps are available, get all possible moves
        if not possible_moves:
            possible_moves = self.get_possible_moves()
        
        # If there are no moves, game is over
        if not possible_moves:
            self.state = GameState.GAME_OVER
            self.winner = PieceType.WHITE
            return
        
        # Choose a random move (this can be improved with actual AI logic)
        from_pos, to_pos = random.choice(possible_moves)
        self.make_move(from_pos, to_pos)
    
    def parse_move(self, move_text: str) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """
        Parse a move string in the format "A1-B2" to coordinates.
        Returns (from_pos, to_pos) or (None, None) if invalid format.
        """
        try:
            # Remove any spaces and split on the hyphen
            parts = move_text.replace(" ", "").split("-")
            if len(parts) != 2:
                return None, None
            
            from_str, to_str = parts
            
            # Parse the coordinates (e.g., A1 -> (0, 0))
            from_col = ord(from_str[0].upper()) - ord('A')
            from_row = int(from_str[1]) - 1
            
            to_col = ord(to_str[0].upper()) - ord('A')
            to_row = int(to_str[1]) - 1
            
            # Check if coordinates are in range
            if not (0 <= from_row < 8 and 0 <= from_col < 8 and 0 <= to_row < 8 and 0 <= to_col < 8):
                return None, None
            
            return (from_row, from_col), (to_row, to_col)
            
        except Exception:
            return None, None
    
    def _check_game_over(self):
        """Check if the game is over (one player has no more pieces or moves)."""
        # Count pieces
        white_pieces = 0
        black_pieces = 0
        
        for row in self.board:
            for piece in row:
                if piece in [PieceType.WHITE, PieceType.WHITE_KING]:
                    white_pieces += 1
                elif piece in [PieceType.BLACK, PieceType.BLACK_KING]:
                    black_pieces += 1
        
        # If one player has no pieces, game is over
        if white_pieces == 0:
            self.state = GameState.GAME_OVER
            self.winner = PieceType.BLACK
            return
        
        if black_pieces == 0:
            self.state = GameState.GAME_OVER
            self.winner = PieceType.WHITE
            return
        
        # Check if current player has no moves
        possible_moves = self.get_possible_moves()
        if not possible_moves:
            self.state = GameState.GAME_OVER
            # The player who can't move loses
            self.winner = PieceType.BLACK if self.current_turn == PieceType.WHITE else PieceType.WHITE
            return

# Dictionary to store active games: {chat_id: CheckersGame}
active_games = {}