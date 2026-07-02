import os

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QPushButton
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import QSize
import chess

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


class PromotionDialog(QDialog):
    PROMOTION_PIECES = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]

    def __init__(self, color: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose promotion")
        self.setModal(True)
        self.selected_piece = chess.QUEEN  # fallback if closed without a choice

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        for piece_type in self.PROMOTION_PIECES:
            button = QPushButton()
            button.setFixedSize(70, 70)
            pixmap = QPixmap(
                os.path.join(
                    ASSETS_DIR,
                    "pieces",
                    "{}{}.png".format(
                        "w" if color else "b", chess.piece_symbol(piece_type)
                    ),
                )
            )
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(60, 60))
            button.clicked.connect(
                lambda checked, p=piece_type: self._choose(p)
            )
            layout.addWidget(button)

        self.setLayout(layout)

    def _choose(self, piece_type):
        self.selected_piece = piece_type
        self.accept()