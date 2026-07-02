from PyQt6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QApplication,
)
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtCore import Qt, QRect, QThread, pyqtSignal
import chess
import chess.engine
import chess.pgn
import os

from board import ChessBoard
from info import MovesRecord, EvaluationBar, EngineLines, ChessEngine
from move_tree import MoveTree

GAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "games")


class GameFrame(QFrame):
    request_evaluation = pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        # self.engine = engine
        self.popped_moves = []

        self.setStyleSheet("background-color: #262626")

        self.evaluation_bar = EvaluationBar(self)
        self.evaluation_bar.setFixedSize(30, 800)

        self.board = ChessBoard(self)
        self.board.setFixedSize(800, 800)

        self.engine_lines = EngineLines(self)
        self.engine_lines.setFixedSize(300, 90)

        self.moves_record = MovesRecord(self)
        self.moves_record.setFixedSize(300, 700)
        self.moves_record.on_move_clicked = self.jump_to_move
        
        self.move_tree: MoveTree = MoveTree(self.board.board)

        # Create a thread for the engine
        self.chess_engine = ChessEngine()
        self.thread: QThread = QThread(self)
        self.chess_engine.moveToThread(self.thread)

        self.request_evaluation.connect(self.chess_engine.evaluate)

        self.chess_engine.evaluation_result.connect(self.handle_evaluation_result)
        self._engine_busy = False
        self._eval_pending = False
        self.thread.finished.connect(self.thread.quit)

        # Right side panel
        right_vbox_layout = QVBoxLayout()
        right_vbox_layout.setContentsMargins(0, 0, 0, 0)
        right_vbox_layout.setSpacing(10)
        right_vbox_layout.addWidget(self.engine_lines)
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
        game_layout.addWidget(self.board)
        game_layout.addWidget(right_vbox_widget)

        game_widget = QWidget()
        game_widget.setLayout(game_layout)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(game_widget)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setLayout(main_layout)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def request_eval(self):
        if self._engine_busy:
            self._eval_pending = True
            return
        self._engine_busy = True
        self.request_evaluation.emit(self.board.board.copy())

    def handle_evaluation_result(self, board, result):
        try:
            if board.fen() == self.board.board.fen():
                self.evaluation_bar.update_engine_evaluation(result)
                if not board.is_checkmate():
                    self.engine_lines.update_engine_lines(result, board)
                else:
                    self.engine_lines.table_widget.clearContents()
        finally:
            self._engine_busy = False
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

        self.board.board = game.board()
        self.move_tree = MoveTree(self.board.board)
        self._import_variations(game, self.move_tree)

        if self.move_tree._main_line:
            self.move_tree._current_move = len(self.move_tree._main_line) - 1

        self.sync_board_to_tree()
        self.moves_record.render_from_tree(self.move_tree)
        self.request_eval()

    def sync_board_to_tree(self):
        """Rebuild the physical board to match wherever self.move_tree
        currently points. Needed after move_up()/move_down(), since those
        only swap which tree node is "current" without touching the board.
        """
        self.board.previous_board = self.board.board.copy()
        self.board.board = self.move_tree.get_board()
        self.board.uncheck_all()
        self.board.update_pieces(self.board.board)
    
    def jump_to_move(self, node, move_index):
        node._current_move = move_index
        node.select_path_to_root()
        self.move_tree = node
        self.sync_board_to_tree()
        self.moves_record.render_from_tree(self.move_tree)
        self.request_eval()

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
                self.board.unframe_all()
                self.board.set_square_style(square_index, "highlight")

            elif event.buttons() == Qt.MouseButton.LeftButton:
                self.board.unhighlight_all()
                self.board.draw_possible_moves(square_index)
                
                self.board.move_piece(square_index)
                if self.board.move_made:
                    the_move = self.board.board.peek()
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

                    self.moves_record.render_from_tree(self.move_tree)
                    self.request_eval()
                

            self.board.previous_sq_idx = square_index
        else:
            print("Mouse click is outside the frame's visible area")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.import_pgn(os.path.join(GAMES_DIR, "lichess_pgn_2024.02.04_Quadrogroth_vs_Ka2sa.uTuihpsM.pgn"))

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

                    self.moves_record.render_from_tree(self.move_tree)
                    self.request_eval()
                else:
                    print('KONIEC WARIANTU')
                    mama = self.move_tree.move_up()
                    if mama:
                        self.move_tree = mama
                        self.sync_board_to_tree()
                        self.moves_record.render_from_tree(self.move_tree)
                        self.request_eval()
            else:
                print('PUSTY MOVESTACK')
            print(self.move_tree._current_move)


        elif event.key() == Qt.Key.Key_Right:
            popped_move = self.move_tree.move_forward()
            if popped_move:
                self.board.uncheck_all()
                self.board.previous_board = self.board.board.copy()
                self.board.board.push(popped_move)
                self.board.move_made = True
                self.board.update_pieces(self.board.board)
                self.moves_record.render_from_tree(self.move_tree)
                self.request_eval()
        
        elif event.key() == Qt.Key.Key_Down:
            print("D")
            child = self.move_tree.move_down()
            if child:
                child._current_move = 0
                self.move_tree = child
                self.sync_board_to_tree()
                self.moves_record.render_from_tree(self.move_tree)
                self.request_eval()
        
        elif event.key() == Qt.Key.Key_Up:
            print("U")
            mama = self.move_tree.move_up()
            if mama:
                self.move_tree = mama 
                self.sync_board_to_tree()
                self.moves_record.render_from_tree(self.move_tree)
                self.request_eval()
                
        elif event.key() == Qt.Key.Key_E:
            self.request_eval()
