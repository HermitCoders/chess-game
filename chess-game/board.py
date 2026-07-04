from PyQt6.QtWidgets import QFrame, QGridLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from collections import defaultdict
import chess

from piece import PieceItem
from promotion_dialog import PromotionDialog

from PyQt6.QtGui import QPainter, QPen, QColor, QPolygonF, QPainterPath, QPainterPathStroker
from PyQt6.QtCore import QRectF, QPointF
import math

class MoveHintWidget(QWidget):
    def __init__(self, parent, is_capture, size):
        super().__init__(parent)
        self.is_capture = is_capture
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(0, 0, 0, 60)

        if self.is_capture:
            pen = QPen(color, 5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            inset = 3
            painter.drawEllipse(QRectF(inset, inset, self.width() - inset * 2, self.height() - inset * 2))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(self.rect())

class BestMoveArrow(QWidget):
    RANK_STYLES = [
        (46, 139, 87, 130, 16, 42),   # primary: deep emerald, thick, full-size head
        (46, 139, 87, 75, 10, 30),    # 2nd: lighter, thinner
        (46, 139, 87, 40, 6, 22),     # 3rd: lightest, thinnest
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.arrows = []  # list of (from_point, to_point)

    def set_arrows(self, arrows):
        self.arrows = arrows
        self.update()

    def clear_arrow(self):
        if self.arrows:
            self.arrows = []
            self.update()

    def paintEvent(self, event):
        if not self.arrows:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw weaker/lighter lines first, primary suggestion last, so
        # the primary arrow always sits visually on top.
        for (p1, p2), style in reversed(list(zip(self.arrows, self.RANK_STYLES))):
            r, g, b, alpha, pen_width, arrow_len = style
            color = QColor(r, g, b, alpha)
            arrow_half_width = math.pi / 5

            # Knight moves (delta of 1 and 2 in perpendicular
            # directions) are drawn as a bent L-shape, matching the
            # lichess/chess.com convention, rather than a straight
            # diagonal line that doesn't reflect how the piece
            # actually travels.
            dx = round((p2.x() - p1.x()) / self.parent().SQUARE_SIZE)
            dy = round((p2.y() - p1.y()) / self.parent().SQUARE_SIZE)
            is_knight_move = {abs(dx), abs(dy)} == {1, 2}

            path_points = [p1]
            if is_knight_move:
                bend = QPointF(p1.x(), p2.y()) if abs(dy) > abs(dx) else QPointF(p2.x(), p1.y())
                path_points.append(bend)
            path_points.append(p2)

            final_p1 = path_points[-2]
            angle = math.atan2(p2.y() - final_p1.y(), p2.x() - final_p1.x())
            shaft_end = QPointF(
                p2.x() - (arrow_len * 0.5) * math.cos(angle),
                p2.y() - (arrow_len * 0.5) * math.sin(angle),
            )

            line_path = QPainterPath()
            line_path.moveTo(path_points[0])
            for point in path_points[1:-1]:
                line_path.lineTo(point)
            line_path.lineTo(shaft_end)

            stroker = QPainterPathStroker()
            stroker.setWidth(pen_width)
            stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
            stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            shaft_path = stroker.createStroke(line_path)

            tip = p2
            base1 = QPointF(
                p2.x() - arrow_len * math.cos(angle - arrow_half_width),
                p2.y() - arrow_len * math.sin(angle - arrow_half_width),
            )
            base2 = QPointF(
                p2.x() - arrow_len * math.cos(angle + arrow_half_width),
                p2.y() - arrow_len * math.sin(angle + arrow_half_width),
            )
            head_path = QPainterPath()
            head_path.addPolygon(QPolygonF([tip, base1, base2]))
            head_path.closeSubpath()

            combined = shaft_path.united(head_path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawPath(combined)

class ChessBoard(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.SQUARE_SIZE = 85
        self.SQUARES_NUMBER = 64
        # self.board = chess.Board("rnbqkbnr/pp1p1ppp/8/2pPp3/8/8/PPP1PPPP/RNBQKBNR w KQkq c6 0 1")
        self.board = chess.Board()
        self.previous_board = None
        self.flipped = False

        self.square_colors = {"light": "#e6e6e6", "dark": "#a6a6a6"}
        # self.square_colors = {"light": "#d9c9a8", "dark": "#6f6558"}
        self.check_colors = {"light": "#e2514c", "dark": "#d74840"}
        self.highlight_colors = {"light": "#00e6b8", "dark": "#00cca3"}
        self.selected_colors = {"light": "#b0c8dd", "dark": "#85a8c4"}
        self.last_move_colors = {"light": "#b0c8dd", "dark": "#85a8c4"}

        self.highlighted_squares = set()
        self.selected_squares = set()
        self.last_move_squares = set()
        self.checked_squares = set()
        self.previous_sq_idx = None
        self.possible_moves = None
        self.possible_promotions = None
        self.move_made = False
        self.pieces_items = {}
        self.move_hint_widgets = []

        self.setContentsMargins(0, 0, 0, 0)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.draw_board()
        self.draw_pieces()

        self.best_move_arrow_widget = BestMoveArrow(self)
        self.best_move_arrow_widget.setGeometry(0, 0, self.SQUARE_SIZE * 8, self.SQUARE_SIZE * 8)
        self.best_move_arrow_widget.raise_()

        self.setLayout(self.layout)

    def draw_board(self):
        for sqr_index in range(self.SQUARES_NUMBER):
            square = QWidget(self)
            square.setFixedSize(self.SQUARE_SIZE, self.SQUARE_SIZE)
            square.setObjectName(chess.SQUARE_NAMES[sqr_index])
            self.set_square_style(sqr_index)
            col, row = self.get_square_coords(sqr_index)
            self.layout.addWidget(square, row, col)
            self._add_square_label(square, sqr_index, col, row)

    def _add_square_label(self, square, sqr_index, col, row):
        file_letter = chess.FILE_NAMES[chess.square_file(sqr_index)]
        rank_number = chess.RANK_NAMES[chess.square_rank(sqr_index)]
        color = self.get_square_color(sqr_index)
        label_color = self.square_colors["dark"] if color == "light" else self.square_colors["light"]
        label_style = f"color: {label_color}; font-size: 11px; font-weight: bold; background: transparent;"

        # Attach to the true chess rank-1 / a-file squares (not the
        # flip-adjusted screen position) so labels move to the opposite
        # screen edge when the board is flipped, rather than staying
        # pinned to the same physical corner regardless of orientation.
        if chess.square_rank(sqr_index) == 0:  # rank 1 -- file letter
            file_label = QLabel(file_letter, square)
            file_label.setStyleSheet(label_style)
            file_label.adjustSize()
            # A 180-degree board flip mirrors BOTH axes within the
            # square, not just one -- unflipped sits bottom-right,
            # flipped sits top-left.
            if self.flipped:
                x, y = 4, 2
            else:
                x = self.SQUARE_SIZE - file_label.width() - 4
                y = self.SQUARE_SIZE - file_label.height() - 2
            file_label.move(x, y)
            file_label.show()

        if chess.square_file(sqr_index) == 0:  # a-file -- rank number
            rank_label = QLabel(rank_number, square)
            rank_label.setStyleSheet(label_style)
            rank_label.adjustSize()
            # Same 180-degree mirroring -- unflipped sits top-left,
            # flipped sits bottom-right.
            if self.flipped:
                x = self.SQUARE_SIZE - rank_label.width() - 4
                y = self.SQUARE_SIZE - rank_label.height() - 2
            else:
                x, y = 4, 2
            rank_label.move(x, y)
            rank_label.show()

    def draw_pieces(self):
        for sqr_index in range(self.SQUARES_NUMBER):
            col, row = self.get_square_coords(sqr_index)
            piece: PieceItem = self.board.piece_at(sqr_index)
            if piece:
                piece_label = PieceItem(self, piece)
                self.layout.addWidget(piece_label, row, col)
                self.pieces_items[sqr_index] = piece_label

    def update_pieces(self, next_board):
        for sqr_index in range(self.SQUARES_NUMBER):
            if self.previous_board.piece_at(sqr_index) != next_board.piece_at(sqr_index):
                col, row = self.get_square_coords(sqr_index)

                old_piece: PieceItem = self.pieces_items.get(sqr_index)
                if old_piece:
                    self.layout.removeWidget(old_piece)
                    del self.pieces_items[sqr_index]
                    old_piece.deleteLater()
                    old_piece.setParent(None)

                piece: chess.Piece = next_board.piece_at(sqr_index)
                if piece:
                    piece_label = PieceItem(self, piece)
                    self.layout.addWidget(piece_label, row, col)
                    self.pieces_items[sqr_index] = piece_label

        self.best_move_arrow_widget.raise_()
        self._update_check_highlight(next_board)

    def _update_check_highlight(self, board):
        self.uncheck_all()
        if board.is_check():
            king_square = board.king(board.turn)
            if king_square is not None:
                self.set_square_style(king_square, "check")
                self.checked_squares.add(king_square)
    
    def show_last_move(self, move):
        for sqr_index in self.last_move_squares:
            self.set_square_style(sqr_index)
        self.last_move_squares = set()

        if move is not None:
            self.set_square_style(move.from_square, "last_move")
            self.set_square_style(move.to_square, "last_move")

    def get_square_coords(self, square_index):
        col = chess.square_file(square_index)
        row = 7 - chess.square_rank(square_index)
        if self.flipped:
            col = 7 - col
            row = 7 - row
        return col, row

    def get_square_color(self, square_index):
        col, row = self.get_square_coords(square_index)
        return "light" if row % 2 == col % 2 else "dark"

    def set_square_style(self, square_index, square_style=None):
        square = self.findChild(QWidget, chess.SQUARE_NAMES[square_index])
        color = self.get_square_color(square_index)
        if square_style == "last_move":
            style = f"background-color: {self.last_move_colors[color]}"
            self.last_move_squares.add(square_index)
        elif square_style == "selected":
            style = f"background-color: {self.selected_colors[color]}"
            self.selected_squares.add(square_index)
        elif square_style == "highlight":
            if square_index not in self.highlighted_squares:
                style = f"background-color: {self.highlight_colors[color]}"
                self.highlighted_squares.add(square_index)
            else:
                style = f"background-color: {self.square_colors[color]}"
                self.highlighted_squares.remove(square_index)
        elif square_style == "check":
            style = f"background-color: {self.check_colors[color]}"
        else:
            style = f"background-color: {self.square_colors[color]}"
        square.setStyleSheet(style)

    def unhighlight_all(self):
        for sqr_index in self.highlighted_squares.union(self.selected_squares):
            self.set_square_style(sqr_index)
        self.highlighted_squares = set()
        self.selected_squares = set()
        self._clear_move_hints()

    def uncheck_all(self):
        for sqr_index in self.checked_squares:
            self.set_square_style(sqr_index)
        self.checked_squares = set()

    def get_possible_moves(self):
        possible_moves = defaultdict(list)
        possible_promotions = defaultdict(list)

        for pos in list(self.board.legal_moves):
            if pos.promotion:
                possible_promotions[pos.from_square].append(pos.to_square)
            possible_moves[pos.from_square].append(pos.to_square)

        self.possible_moves = possible_moves
        self.possible_promotions = possible_promotions

    def mouse_position_to_square_index(self, mouse_position):
        col = int(mouse_position.x() // self.SQUARE_SIZE)
        row = 7 - int(mouse_position.y() // self.SQUARE_SIZE)
        if self.flipped:
            col = 7 - col
            row = 7 - row
        square_index = chess.square(col, row)
        return square_index

    def draw_possible_moves(self, square_index):
        self.get_possible_moves()
        self._clear_move_hints()
        if square_index in self.possible_moves:
            self.set_square_style(square_index, "selected")
            for sq_idx in self.possible_moves[square_index]:
                is_capture = self.board.piece_at(sq_idx) is not None
                self._add_move_hint(sq_idx, is_capture)
            
    def _clear_move_hints(self):
        for widget in self.move_hint_widgets:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        self.move_hint_widgets = []

    def _add_move_hint(self, square_index, is_capture):
        square = self.findChild(QWidget, chess.SQUARE_NAMES[square_index])
        size = self.SQUARE_SIZE if is_capture else self.SQUARE_SIZE // 3
        hint = MoveHintWidget(square, is_capture, size)
        hint.move((self.SQUARE_SIZE - size) // 2, (self.SQUARE_SIZE - size) // 2)
        hint.show()
        self.move_hint_widgets.append(hint)
    
    def square_center(self, square_index):
        col, row = self.get_square_coords(square_index)
        x = col * self.SQUARE_SIZE + self.SQUARE_SIZE / 2
        y = row * self.SQUARE_SIZE + self.SQUARE_SIZE / 2
        return QPointF(x, y)

    def show_best_move_arrows(self, moves):
        if not moves:
            self.best_move_arrow_widget.clear_arrow()
            return
        arrows = [
            (self.square_center(move.from_square), self.square_center(move.to_square))
            for move in moves
        ]
        self.best_move_arrow_widget.set_arrows(arrows)

    def clear_best_move_arrow(self):
        self.best_move_arrow_widget.clear_arrow()

    def move_piece(self, square_index):
        if (
            self.previous_sq_idx in self.possible_moves.keys()
            and square_index in self.possible_moves[self.previous_sq_idx]
        ):
            if (
                self.previous_sq_idx in self.possible_promotions.keys()
                and square_index in self.possible_promotions[self.previous_sq_idx]
            ):
                dialog = PromotionDialog(self.board.turn, self)
                dialog.exec()
                move = chess.Move(
                    self.previous_sq_idx, square_index, promotion=dialog.selected_piece
                )
            else:
                move = chess.Move(self.previous_sq_idx, square_index)
            self.previous_board = self.board.copy()
            self.board.push(move)
            self.move_made = True
            self.update_pieces(self.board)
        else:
            self.move_made = False
    
    def flip_board(self):
        self.flipped = not self.flipped
        self._rebuild_board_ui()

    def _rebuild_board_ui(self):
        # Remove every existing child widget (squares, labels, pieces)
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.pieces_items = {}
        self.draw_board()
        self.draw_pieces()
        self._reapply_persistent_highlights()
        self.best_move_arrow_widget.raise_()
        self.update()

    def _reapply_persistent_highlights(self):
        """draw_board() resets every square widget to its default
        style, silently dropping any last-move/check highlighting
        that was active before a full rebuild (e.g. flipping the
        board). Re-paint them here using the square indices we were
        already tracking -- they're absolute chess squares, not
        screen positions, so they're still valid after a flip."""
        for sqr_index in list(self.last_move_squares):
            self.set_square_style(sqr_index, "last_move")
        for sqr_index in list(self.checked_squares):
            self.set_square_style(sqr_index, "check")
