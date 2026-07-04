import os

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QApplication, QSizePolicy
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import chess
from functools import lru_cache

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

@lru_cache(maxsize=None)
def _load_piece_pixmap(color, piece_type):
    """Load and scale a captured-piece icon once, then cache it.
    update_captured() used to re-read the PNG from disk and re-run
    SmoothTransformation scaling for every icon on every single
    navigation step, even when nothing about the captured pieces had
    changed -- in a long game with several captures, that's real
    per-keystroke cost that grows as more pieces get captured."""
    pixmap = QPixmap(
        os.path.join(
            ASSETS_DIR,
            "pieces",
            "{}{}.png".format("w" if color else "b", chess.piece_symbol(piece_type)),
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
    return scaled


class CapturedPiecesTray(QWidget):
    def __init__(self):
        super().__init__()
        self._last_state = None
        self.setFixedHeight(32)
        self.setStyleSheet("background-color: transparent;")

        self.name_label = QLabel("")
        self.name_label.setStyleSheet(
            "color: #d0d0d0; font-family: Menlo; font-size: 13px; font-weight: bold;"
        )
        self.name_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.icon_layout = QHBoxLayout()
        self.icon_layout.setSpacing(0)

        self.material_label = QLabel("")
        self.material_label.setStyleSheet(
            "color: #8a8a8a; font-family: Menlo; font-size: 13px;"
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(6)
        outer.addWidget(self.name_label)
        outer.addLayout(self.icon_layout)
        outer.addWidget(self.material_label)
        outer.addStretch()

    def set_name(self, name):
        self.name_label.setText(name)
        self.name_label.adjustSize()

    def update_captured(self, captured_types, piece_color, material_lead):
        sorted_types = tuple(sorted(captured_types, key=DISPLAY_ORDER.index))
        state = (sorted_types, piece_color, material_lead)
        if state == self._last_state:
            # Nothing about this tray's contents actually changed --
            # skip tearing down and rebuilding every icon widget, which
            # is the expensive part and was happening on every single
            # navigation keystroke regardless of whether it was needed.
            return
        self._last_state = state

        while self.icon_layout.count():
            item = self.icon_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        previous_type = None
        for piece_type in sorted_types:
            icon = QLabel()
            icon.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            icon.setStyleSheet("background: transparent;")
            icon.setPixmap(_load_piece_pixmap(piece_color, piece_type))

            if previous_type is not None:
                gap = -14 if piece_type == previous_type else 2
                self.icon_layout.addSpacing(gap)

            self.icon_layout.addWidget(icon)
            previous_type = piece_type

        self.material_label.setText(f"+{material_lead}" if material_lead > 0 else "")
