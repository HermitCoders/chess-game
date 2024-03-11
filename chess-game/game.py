from PyQt6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QApplication,
)
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtCore import Qt, QRect, QThread
import chess
import chess.engine
import chess.pgn

from board import ChessBoard
from info import MovesRecord, EvaluationBar, EngineLines, ChessEngine
from move_tree import MoveTree


class GameFrame(QFrame):
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
        
        self.move_tree: MoveTree = MoveTree(self.board.board)

        # Create a thread for the engine
        self.chess_engine = ChessEngine()
        self.thread: QThread = QThread(self)
        self.chess_engine.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(
            lambda: self.chess_engine.evaluate(self.board.board)
        )
        self.chess_engine.evaluation_result.connect(self.handle_evaluation_result)
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

    def handle_evaluation_result(self, result):
        self.evaluation_bar.update_engine_evaluation(result)
        if not self.board.board.is_checkmate():
            self.engine_lines.update_engine_lines(result)
        else:
            self.engine_lines.table_widget.clearContents()

    def import_pgn(self, pgn_path):
        with open(pgn_path) as pgn:
            game = chess.pgn.read_game(pgn)
            self.board.board = game.board()
            for move in game.mainline_moves():
                self.move_tree.add_main(move)

                self.board.previous_board = self.board.board.copy()

                self.board.board.push(move)
                self.board.move_made = True
                self.board.update_pieces(self.board.board)
                self.moves_record.update_moves_record()

                QApplication.processEvents()
                
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
                    print(f"Move: {the_move},   Next move: {self.move_tree.get_next_move()}")
                    if self.move_tree.get_next_move() is None:
                        print('idz glowna sciezkom')
                        self.move_tree.add_main(the_move)
                    elif self.move_tree.get_next_move() == the_move:
                        self.move_tree.move_forward()
                    elif self.move_tree.has_variant():
                        variant = self.move_tree.get_variant()
                        if variant.get_next_move() == the_move:
                            self.move_tree = self.move_tree.move_down()
                            self.move_tree.move_forward()

                    else:
                        print('zrup variant')
                        self.move_tree.add_variant(the_move, self.board.previous_board)
                        self.move_tree = self.move_tree.move_down()
                    print("Move tree has variant:", self.move_tree.has_variant())
                    print("Move tree:", self.move_tree.id)
                
                # self.moves_record.update_moves_record()

            self.board.previous_sq_idx = square_index
        else:
            print("Mouse click is outside the frame's visible area")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.import_pgn("./games/TALHAA79_vs_SzachowySmoluch_2024.03.01.pgn")

        if event.key() == Qt.Key.Key_Left:
            if self.board.board.move_stack:
                if self.move_tree.move_backward() is not None:
                    self.board.uncheck_all()
                    self.board.previous_board = self.board.board.copy()
                    self.board.board.pop()
                    
                    # self.board.move_made = True
                    self.board.update_pieces(self.board.board)
                else:
                    print('KONIEC WARIANTU')
                    mama = self.move_tree.move_up()
                    if mama:
                        self.move_tree = mama 
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
        
        elif event.key() == Qt.Key.Key_Down:
            print("D")
            print(self.move_tree.get_string_repr())
        
        elif event.key() == Qt.Key.Key_Up:
            print("U")
            mama = self.move_tree.move_up()
            if mama:
                self.move_tree = mama 
                
        elif event.key() == Qt.Key.Key_E:
            self.thread.started.emit()
        
        moves_num = len(self.board.board.move_stack)
        turns_num = (moves_num - 1) // 2

        if moves_num % 2 == 0:
            self.moves_record.table_widget.setCurrentCell(turns_num, moves_num % 2 + 1)
        else:
            self.moves_record.table_widget.setCurrentCell(turns_num, moves_num % 2 - 1)
