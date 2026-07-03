from PyQt6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QApplication,
    QFileDialog,
    QMessageBox,
    QProgressBar,
)
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtCore import Qt, QRect, QThread, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QSoundEffect
import chess
import chess.engine
import chess.pgn
import os
import logging

logger = logging.getLogger(__name__)

from board import ChessBoard
from info import MovesRecord, EvaluationBar, EngineLines, ChessEngine
from move_tree import MoveTree
from captured_tray import CapturedPiecesTray, compute_captured, material_value

GAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "games")


class GameFrame(QFrame):
    request_evaluation = pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        self.setStyleSheet("background-color: #262626")

        self.board = ChessBoard(self)
        self.board.setFixedSize(680, 680)

        self.evaluation_bar = EvaluationBar(self)
        self.evaluation_bar.setFixedSize(30, 780)

        self.top_tray = CapturedPiecesTray()
        self.bottom_tray = CapturedPiecesTray()

        board_column_layout = QVBoxLayout()
        board_column_layout.setContentsMargins(50, 10, 50, 10)
        board_column_layout.setSpacing(8)
        board_column_layout.addWidget(self.top_tray)
        board_column_layout.addWidget(self.board)
        board_column_layout.addWidget(self.bottom_tray)

        board_column_widget = QWidget()
        board_column_widget.setStyleSheet("background-color: #363636;")
        board_column_widget.setLayout(board_column_layout)
        board_column_widget.setFixedWidth(680 + 50 + 50)
        board_column_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.engine_lines = EngineLines(self)
        self.engine_lines.setFixedSize(300, 90)

        self.moves_record = MovesRecord(self)
        self.moves_record.setFixedSize(300, 680)
        self.moves_record.on_move_clicked = self.jump_to_move
        
        self.move_tree: MoveTree = MoveTree(self.board.board)
        
        self.white_name = "White"
        self.black_name = "Black"

        self._update_captured_trays()

        self._last_top_moves = []

        sounds_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sounds")
        self.move_sound = QSoundEffect()
        self.move_sound.setSource(QUrl.fromLocalFile(os.path.join(sounds_dir, "Move.wav")))
        self.move_sound.setVolume(0.5)

        self.capture_sound = QSoundEffect()
        self.capture_sound.setSource(QUrl.fromLocalFile(os.path.join(sounds_dir, "Capture.wav")))
        self.capture_sound.setVolume(0.5)

        self.notify_sound = QSoundEffect()
        self.notify_sound.setSource(QUrl.fromLocalFile(os.path.join(sounds_dir, "GenericNotify.wav")))
        self.notify_sound.setVolume(0.5)

        # Create a thread for the engine
        self.chess_engine = ChessEngine()
        self.thread: QThread = QThread(self)
        self.chess_engine.moveToThread(self.thread)

        self.request_evaluation.connect(self.chess_engine.evaluate)

        self.chess_engine.evaluation_result.connect(self.handle_evaluation_result)
        self._engine_busy = False
        self._eval_pending = False
        self.thread.finished.connect(self.thread.quit)

        self.thinking_bar = QProgressBar()
        self.thinking_bar.setRange(0, 0)  # indeterminate mode
        self.thinking_bar.setFixedHeight(4)
        self.thinking_bar.setMaximumHeight(4)
        self.thinking_bar.setTextVisible(False)
        self.thinking_bar.setStyleSheet(
            "QProgressBar {background-color: #262626; border: none; margin: 0px; padding: 0px;} "
            "QProgressBar::chunk {background-color: #5dcaa5;}"
        )

        # Right side panel
        right_vbox_layout = QVBoxLayout()
        right_vbox_layout.setContentsMargins(0, 0, 0, 0)
        right_vbox_layout.setSpacing(0)
        right_vbox_layout.addWidget(self.engine_lines)
        right_vbox_layout.addSpacing(3)
        right_vbox_layout.addWidget(self.thinking_bar)
        right_vbox_layout.addSpacing(3)
        right_vbox_layout.addWidget(self.moves_record)

        right_vbox_widget = QWidget()
        right_vbox_widget.setLayout(right_vbox_layout)
        right_vbox_widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        # Game layout
        game_layout = QHBoxLayout()
        game_layout.setContentsMargins(0, 0, 0, 0)
        game_layout.setSpacing(10)
        game_layout.addWidget(self.evaluation_bar)
        game_layout.addWidget(board_column_widget)
        game_layout.addWidget(right_vbox_widget)
        game_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        game_widget = QWidget()
        game_widget.setLayout(game_layout)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(game_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setLayout(main_layout)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def request_eval(self):
        if self._engine_busy:
            self._eval_pending = True
            return
        self._engine_busy = True
        self.engine_lines.set_thinking(True)
        self.thinking_bar.setStyleSheet(
            "QProgressBar {background-color: #262626; border: none; margin: 0px; padding: 0px;} "
            "QProgressBar::chunk {background-color: #5dcaa5;}"
        )
        self.request_evaluation.emit(self.board.board.copy())

    def handle_evaluation_result(self, board, result):
        try:
            if board.fen() == self.board.board.fen():
                self.evaluation_bar.update_engine_evaluation(result)
                if not board.is_checkmate():
                    self.engine_lines.update_engine_lines(result, board)
                    top_moves = []
                    for eval_dict in result[:3]:
                        line = eval_dict.get("pv", "")
                        if line:
                            top_moves.append(line[0])
                    self._last_top_moves = top_moves
                    self.board.show_best_move_arrows(top_moves)
                else:
                    self.engine_lines.table_widget.clearContents()
                    self.board.clear_best_move_arrow()
        finally:
            self._engine_busy = False
            self.engine_lines.set_thinking(False)
            self.thinking_bar.setStyleSheet(
                "QProgressBar {background-color: #262626; border: none; margin: 0px; padding: 0px;} "
                "QProgressBar::chunk {background-color: #262626;}"
            )
            if self._eval_pending:
                self._eval_pending = False
                self.request_eval()

    def _import_variations(self, pgn_node, tree_node):
        """Recursively walk a python-chess GameNode tree and rebuild it
        as our own MoveTree, preserving every variation from the PGN
        file (not just the mainline)."""
        variations = pgn_node.variations
        if not variations:
            return

        # Sidelines must be added while tree_node's current position
        # still matches pgn_node (i.e. before the mainline move below
        # advances it), since add_variant keys off the current position.
        sideline_children = []
        for child in variations[1:]:
            board_before = pgn_node.board()
            tree_node.add_variant(child.move, board_before)
            sideline_children.append((child, tree_node.get_variant()))

        mainline_child = variations[0]
        tree_node.add_main(mainline_child.move)

        for child, variant_node in sideline_children:
            self._import_variations(child, variant_node)

        self._import_variations(mainline_child, tree_node)

    def import_pgn(self, pgn_path):
        with open(pgn_path) as pgn:
            game = chess.pgn.read_game(pgn)

        if game is None:
            print(f"Could not read a game from {pgn_path}")
            return

        self.white_name = game.headers.get("White", "White")
        self.black_name = game.headers.get("Black", "Black")

        self.board.board = game.board()
        self.move_tree = MoveTree(self.board.board)
        self._import_variations(game, self.move_tree)

        if self.move_tree._main_line:
            self.move_tree._current_move = len(self.move_tree._main_line) - 1

        self.sync_board_to_tree()
        self._on_position_changed()
    
    def new_game(self):
        reply = QMessageBox.question(
            self,
            "New Game",
            "Start a new game? This will discard the current game and any analysis.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.white_name = "White"
        self.black_name = "Black"
        self.board.board = chess.Board()
        self.board.flipped = False
        self.board._rebuild_board_ui()
        self.move_tree = MoveTree(self.board.board)
        self._on_position_changed()

    def sync_board_to_tree(self):
        """Rebuild the physical board to match wherever self.move_tree
        currently points. Needed after move_up()/move_down(), since those
        only swap which tree node is "current" without touching the board.
        """
        self.board.previous_board = self.board.board.copy()
        self.board.board = self.move_tree.get_board()
        self.board.uncheck_all()
        self.board.update_pieces(self.board.board)
    
    def _on_position_changed(self):
        """Call after self.move_tree changes (a move was made, or we
        navigated/jumped elsewhere in the tree) to keep the moves
        panel and engine evaluation in sync with the new position."""
        self._last_top_moves = []
        self.board.clear_best_move_arrow()
        self.moves_record.render_from_tree(self.move_tree)
        self.request_eval()
        self._update_captured_trays()

    def _update_captured_trays(self):
        missing_white, missing_black = compute_captured(self.board.board)
        material_lead = material_value(missing_black) - material_value(missing_white)

        white_tray_data = (self.white_name, missing_white, chess.WHITE, max(-material_lead, 0))
        black_tray_data = (self.black_name, missing_black, chess.BLACK, max(material_lead, 0))

        # White sits at the bottom normally, top when flipped -- keep
        # each tray showing whichever color is actually on that side
        # of the board right now.
        top_data, bottom_data = (
            (black_tray_data, white_tray_data)
            if self.board.flipped
            else (white_tray_data, black_tray_data)
        )

        for tray, (name, missing, color, lead) in ((self.top_tray, top_data), (self.bottom_tray, bottom_data)):
            tray.set_name(name)
            tray.update_captured(missing, color, lead)
    
    def _check_game_end(self, board):
        if board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition() or board.is_seventyfive_moves():
            self.notify_sound.play()
        if board.is_checkmate():
            winner = "White" if not board.turn else "Black"
            QMessageBox.information(self, "Checkmate", f"Checkmate -- {winner} wins!")
        elif board.is_stalemate():
            QMessageBox.information(self, "Stalemate", "Stalemate -- the game is a draw.")
        elif board.is_insufficient_material():
            QMessageBox.information(self, "Draw", "Draw -- insufficient material to checkmate.")
        elif board.can_claim_threefold_repetition():
            QMessageBox.information(self, "Draw", "Draw by threefold repetition.")
        elif board.is_seventyfive_moves():
            QMessageBox.information(self, "Draw", "Draw -- 75 moves without a capture or pawn move.")

    def jump_to_move(self, node, move_index):
        node._current_move = move_index
        node.select_path_to_root()
        self.move_tree = node
        self.sync_board_to_tree()
        self._on_position_changed()

    def mousePressEvent(self, event: QMouseEvent):
        global_pos = self.mapToGlobal(event.pos())

        rect = QRect(
            self.board.mapToGlobal(self.board.rect().topLeft()), self.board.size()
        )
        if rect.contains(global_pos):
            # The mouse click is within the frame's visible area
            local_pos = self.board.mapFromGlobal(global_pos)
            square_index = self.board.mouse_position_to_square_index(local_pos)

            if event.buttons() == Qt.MouseButton.RightButton:
                self.board.set_square_style(square_index, "highlight")

            elif event.buttons() == Qt.MouseButton.LeftButton:
                self.board.unhighlight_all()
                self.board.draw_possible_moves(square_index)
                
                was_capture = self.board.board.piece_at(square_index) is not None
                self.board.move_piece(square_index)
                if self.board.move_made:
                    the_move = self.board.board.peek()
                    if was_capture:
                        self.capture_sound.play()
                    else:
                        self.move_sound.play()
                    if self.move_tree.get_next_move() is None:
                        self.move_tree.add_main(the_move)
                    elif self.move_tree.get_next_move() == the_move:
                        self.move_tree.move_forward()
                    else:
                        matched_index = None
                        for i, sibling in enumerate(self.move_tree.get_variants()):
                            if sibling.get_current_move() == the_move:
                                matched_index = i
                                break

                        if matched_index is not None:
                            self.move_tree.select_variant(matched_index)
                            self.move_tree = self.move_tree.move_down()
                            self.sync_board_to_tree()
                        else:
                            self.move_tree.add_variant(the_move, self.board.previous_board)
                            self.move_tree = self.move_tree.move_down()

                    self._on_position_changed()
                    self._check_game_end(self.board.board)
                
            self.board.previous_sq_idx = square_index
        else:
            logger.debug("Mouse click is outside the frame's visible area")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_I:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open PGN", GAMES_DIR, "PGN files (*.pgn);;All files (*)"
            )
            if file_path:
                self.import_pgn(file_path)

        if event.key() == Qt.Key.Key_Left:
            if self.board.board.move_stack:
                if self.move_tree.move_backward() is not None:
                    self.board.uncheck_all()
                    self.board.previous_board = self.board.board.copy()
                    self.board.board.pop()
                    self.board.update_pieces(self.board.board)

                    if self.move_tree._current_move == -1:
                        parent = self.move_tree.move_up()
                        if parent:
                            self.move_tree = parent

                    self._on_position_changed()
                else:
                    logger.debug("End of variation, moving up to parent line")
                    mama = self.move_tree.move_up()
                    if mama:
                        self.move_tree = mama
                        self.sync_board_to_tree()
                        self._on_position_changed()
            else:
                logger.debug("Move stack is empty, nothing to go back to")


        elif event.key() == Qt.Key.Key_Right:
            popped_move = self.move_tree.move_forward()
            if popped_move:
                self.board.uncheck_all()
                self.board.previous_board = self.board.board.copy()
                self.board.board.push(popped_move)
                self.board.move_made = True
                self.board.update_pieces(self.board.board)
                self._on_position_changed()
        
        elif event.key() == Qt.Key.Key_Down:
            child = self.move_tree.move_down()
            if child:
                child._current_move = 0
                self.move_tree = child
                self.sync_board_to_tree()
                self._on_position_changed()
        
        elif event.key() == Qt.Key.Key_Up:
            mama = self.move_tree.move_up()
            if mama:
                self.move_tree = mama 
                self.sync_board_to_tree()
                self._on_position_changed()
                
        elif event.key() == Qt.Key.Key_E:
            self.request_eval()
        
        elif event.key() == Qt.Key.Key_F:
            self.board.flip_board()
            self.engine_lines.refresh_colors()
            self.evaluation_bar.update()
            self._update_captured_trays()
            self.board.show_best_move_arrows(self._last_top_moves)
        
        elif event.key() == Qt.Key.Key_N:
            self.new_game()
