from PyQt6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QApplication
)
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtCore import Qt, QRect
import chess
import chess.engine
import chess.pgn

from board import ChessBoard
from info import MovesRecord, EvaluationBar, EngineLines
import time

class GameFrame(QFrame):
    def __init__(self, parent, engine):
        super().__init__(parent)

        self.parent = parent
        self.engine = engine
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
                self.moves_record.update_moves_record()

            self.board.previous_sq_idx = square_index
        else:
            print("Mouse click is outside the frame's visible area")

        eval, move_num = self.evaluation()
        self.evaluation_bar.update_engine_evaluation(eval)
        if not self.board.board.is_checkmate():
            self.engine_lines.update_engine_lines(eval, move_num)
        else:
            self.engine_lines.table_widget.clearContents()

    def evaluation(self):
        info = self.engine.analyse(
            self.board.board, chess.engine.Limit(time=0.1), multipv=5
        )
        move_index = self.board.board.ply()
        return info, move_index
    
    def import_pgn(self, pgn_path):
        with open(pgn_path) as pgn:
            game = chess.pgn.read_game(pgn)
            self.board.board = game.board()
            for move in game.mainline_moves():
                self.board.previous_board = self.board.board.copy()
                
                self.board.board.push(move)
                self.board.move_made = True
                self.board.set_move_type(move)
                self.board.update_pieces(self.board.board)
                # self.board.board = self.board.next_board
                self.moves_record.update_moves_record()
                
                QApplication.processEvents()
                                
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.import_pgn("./games/lichess_pgn_2024.02.04_Quadrogroth_vs_Ka2sa.uTuihpsM.pgn")
        elif event.key() == Qt.Key.Key_Left:
            print("Left")
            self.board.previous_board = self.board.board.copy()
            
            popped_move = self.board.board.pop()
            self.popped_moves.append(popped_move)
            self.board.move_made = True
            # self.board.set_move_type(move)
            self.board.update_pieces(self.board.board)
            
            # print()
        elif event.key() == Qt.Key.Key_Right:
            print("Right")
            self.board.previous_board = self.board.board.copy()
            
            popped_move = self.popped_moves.pop()
            self.board.board.push(popped_move)
            self.board.move_made = True
            # self.board.set_move_type(move)
            self.board.update_pieces(self.board.board)

            
