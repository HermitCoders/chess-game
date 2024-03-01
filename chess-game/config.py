import pygame
import os

# from sound import Sound
from theme import Theme


class Config:

    def __init__(self):
        self.themes = []
        self._add_themes()
        self.idx = 0
        self.theme = self.themes[self.idx]
        self.screen_dimensions = (1200, 800)
        self.board_dimensions = (800, 800)
        self.square_size = self.board_dimensions[0] // 8
        self.font = pygame.font.SysFont("arial", self.square_size // 4, bold=True)
        self.small_font = pygame.font.SysFont("arial", self.square_size // 6, bold=True)
        self.evaluation_bar_dimensions = (30, 800)
        self.freespace_dimensions = (370, 800)

        # self.move_sound = Sound(
        #     os.path.join('assets/sounds/move.wav'))
        # self.capture_sound = Sound(
        #     os.path.join('assets/sounds/capture.wav'))

    def change_theme(self):
        self.idx += 1
        self.idx %= len(self.themes)
        self.theme = self.themes[self.idx]

    def _add_themes(self):
        # light_sq, dark_sq, light_hl, dark_hl, light_moves, dark_moves
        gray = Theme(
            (230, 230, 230),
            (160, 160, 160),
            (210, 50, 50),
            (180, 50, 50),
            (50, 50, 50),
            (50, 50, 50),
        )

        self.themes = [gray]
