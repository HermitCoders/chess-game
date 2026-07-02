import os

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QApplication
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import chess

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
STARTING_COUNTS = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1}
DISPLAY_ORDER = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]


def compute_captured(board):
    """Derive captured pieces per side by comparing current piece
    counts to the starting position. Returns (missing_white,
    missing_black), each the raw list of piece types that side has
    lost (not net-cancelled against the opponent)."""
    missing_white = []
    missing_black = []
    for piece_type, starting_count in STARTING_COUNTS.items():
        white_on_board = len(board.pieces(piece_type, chess.WHITE))
        black_on_board = len(board.pieces(piece_type, chess.BLACK))
        missing_white.extend([piece_type] * (starting_count - white_on_board))
        missing_black.extend([piece_type] * (starting_count - black_on_board))
    return missing_white, missing_black


def material_value(piece_types):
    return sum(PIECE_VALUES[p] for p in piece_types)


class CapturedPiecesTray(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(32)
        self.setStyleSheet("background-color: transparent;")

        self.icon_layout = QHBoxLayout()
        self.icon_layout.setSpacing(0)

        self.material_label = QLabel("")
        self.material_label.setStyleSheet(
            "color: #8a8a8a; font-family: Menlo; font-size: 13px;"
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.addLayout(self.icon_layout)
        outer.addWidget(self.material_label)
        outer.addStretch()

    def update_captured(self, captured_types, piece_color, material_lead):
        while self.icon_layout.count():
            item = self.icon_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        sorted_types = sorted(captured_types, key=DISPLAY_ORDER.index)

        previous_type = None
        for piece_type in sorted_types:
            icon = QLabel()
            icon.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            icon.setStyleSheet("background: transparent;")
            pixmap = QPixmap(
                os.path.join(
                    ASSETS_DIR,
                    "pieces",
                    "{}{}.png".format(
                        "w" if piece_color else "b", chess.piece_symbol(piece_type)
                    ),
                )
            )
            device_ratio = QApplication.primaryScreen().devicePixelRatio()
            target_size = int(24 * device_ratio)
            scaled = pixmap.scaled(
                target_size, target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            scaled.setDevicePixelRatio(device_ratio)
            icon.setPixmap(scaled)

            if previous_type is not None:
                gap = -14 if piece_type == previous_type else 2
                self.icon_layout.addSpacing(gap)

            self.icon_layout.addWidget(icon)
            previous_type = piece_type

        self.material_label.setText(f"+{material_lead}" if material_lead > 0 else "")
