from config import Config
import chess
import chess.engine
import pygame
import math
import sys
from collections import defaultdict


class Game:
    def __init__(self, board=chess.Board()) -> None:
        pygame.init()
        pygame.display.set_caption("Chess")
        self.clock = pygame.time.Clock()
        self.config = Config()
        self.surface = pygame.Surface(self.config.board_dimensions)
        self.screen = pygame.display.set_mode(self.config.screen_dimensions)
        self.evaluation_bar = pygame.Surface(self.config.evaluation_bar_dimensions)
        self.pieces_imgs = self.load_pieces()

        self.board = board
        self.highlighted_squares = []
        self.source_square = None
        self.target_squares = []

    def reset_square(self, selected_sq):
        file_index = chess.square_file(selected_sq)
        rank_index = 7 - chess.square_rank(selected_sq)
        color = (
            self.config.theme.squares.light
            if (file_index + rank_index) % 2 == 0
            else self.config.theme.squares.dark
        )
        rect = (
            file_index * self.config.square_size,
            (rank_index) * self.config.square_size,
            self.config.square_size,
            self.config.square_size,
        )
        pygame.draw.rect(self.surface, color, rect)

    def color_square(self, selected_sq):
        file_index = chess.square_file(selected_sq)
        rank_index = 7 - chess.square_rank(selected_sq)
        color = (
            self.config.theme.highlights.light
            if (file_index + rank_index) % 2 == 0
            else self.config.theme.highlights.dark
        )
        rect = (
            file_index * self.config.square_size,
            (rank_index) * self.config.square_size,
            self.config.square_size,
            self.config.square_size,
        )
        pygame.draw.rect(self.surface, color, rect)

    def mark_square(self, selected_sq, capture=False):
        file_index = chess.square_file(selected_sq)
        rank_index = 7 - chess.square_rank(selected_sq)
        color = (
            self.config.theme.moves.light
            if (file_index + rank_index) % 2 == 0
            else self.config.theme.moves.dark
        )
        if capture:
            center = (
                file_index * self.config.square_size + self.config.square_size // 2,
                rank_index * self.config.square_size + self.config.square_size // 2,
            )
            pygame.draw.circle(
                self.surface, color, center, 
                radius=self.config.square_size // 2,
                width=self.config.square_size // 20,
            )
        else:
            rect = (
                file_index * self.config.square_size,
                (rank_index) * self.config.square_size,
                self.config.square_size,
                self.config.square_size,
            )
            pygame.draw.rect(
                self.surface, color, rect, width=self.config.square_size // 20
            )

    def draw_move(self, target_sq):
        file_index = chess.square_file(target_sq)
        rank_index = 7 - chess.square_rank(target_sq)

        color = (
            self.config.theme.moves.dark
            if (file_index + rank_index) % 2 == 0
            else self.config.theme.moves.light
        )
        center = (
            file_index * self.config.square_size + self.config.square_size // 2,
            rank_index * self.config.square_size + self.config.square_size // 2,
        )
        pygame.draw.circle(self.surface, color, center, self.config.square_size // 10)

    def get_possible_moves(self, event):
        possible_moves = defaultdict(list)

        for pos in list(self.board.legal_moves):
            possible_moves[pos.from_square].append(pos.to_square)

        selected_file_index = (event.pos[0] - self.config.evaluation_bar_dimensions[0]) // self.config.square_size
        selected_rank_index = 7 - event.pos[1] // self.config.square_size

        selected_square = chess.square(selected_file_index, selected_rank_index)

        if selected_square == self.source_square:
            self.source_square = None
            self.target_squares = []

        elif selected_square in possible_moves.keys():
            self.source_square = selected_square
            self.target_squares = possible_moves[selected_square]

    def move(self, event):
        selected_file_index = (event.pos[0] - self.config.evaluation_bar_dimensions[0]) // self.config.square_size
        selected_rank_index = 7 - event.pos[1] // self.config.square_size
        selected_square = chess.square(selected_file_index, selected_rank_index)

        if selected_square in self.target_squares:
            self.board.push(chess.Move(self.source_square, selected_square))

            self.source_square = None
            self.target_squares = []

    def get_highlighted_squares(self, event):
        selected_file_index = (event.pos[0] - self.config.evaluation_bar_dimensions[0]) // self.config.square_size
        selected_rank_index = 7 - event.pos[1] // self.config.square_size

        selected_square = chess.square(selected_file_index, selected_rank_index)

        if selected_square not in self.highlighted_squares:
            self.highlighted_squares.append(selected_square)
        else:
            self.highlighted_squares.remove(selected_square)

    def event_handler(self, event):
        if event.button == 3:
            self.get_highlighted_squares(event)

        if event.button == 1:
            self.highlighted_squares = []
            self.get_possible_moves(event)
            self.move(event)

    def load_pieces(self):
        pieces_types = ["p", "n", "b", "r", "q", "k"]
        pieces_colors = ["w", ""]
        pieces_imgs = {}
        for t in pieces_types:
            for c in pieces_colors:
                pieces_imgs[c + t] = pygame.transform.smoothscale(
                    pygame.image.load(f"imgs/{c+t}.png"),
                    (self.config.square_size, self.config.square_size),
                )
        return pieces_imgs

    def draw_board(self):
        for square in range(64):
            file_index = chess.square_file(square)
            rank_index = 7 - chess.square_rank(square)
            self.reset_square(square)

            if square in self.highlighted_squares:
                self.color_square(square)

            if square == self.source_square:
                self.mark_square(square)

            if square in self.target_squares:
                if self.board.piece_at(square):
                    self.mark_square(square, capture=True)
                else:
                    self.draw_move(square)

            if (
                self.board.is_check()
                and self.board.piece_at(square)
                and chess.piece_symbol(self.board.piece_at(square).piece_type) == "k"
                and self.board.piece_at(square).color == self.board.turn
            ):
                self.color_square(square)

            # row coordinates
            if file_index == 0:
                color = (
                    self.config.theme.squares.dark
                    if rank_index % 2 == 0
                    else self.config.theme.squares.light
                )
                lbl = self.config.font.render(str(8 - rank_index), 1, color)
                lbl_pos = (10, 5 + rank_index * self.config.square_size)
                self.surface.blit(lbl, lbl_pos)

            # col coordinates
            if rank_index == 7:
                color = (
                    self.config.theme.squares.dark
                    if (file_index + rank_index) % 2 == 0
                    else self.config.theme.squares.light
                )
                lbl = self.config.font.render(chess.FILE_NAMES[file_index], 1, color)
                lbl_pos = (
                    file_index * self.config.square_size + self.config.square_size - 20,
                    self.config.board_dimensions[0] - 30,
                )
                self.surface.blit(lbl, lbl_pos)

    def draw_pieces(self):
        if self.board is not None:
            for square in range(64):
                file_index = chess.square_file(square)
                rank_index = 7 - chess.square_rank(square)
                piece = self.board.piece_at(square)
                if piece:
                    piece_color = "w" if piece.color else ""
                    piece_type = chess.piece_symbol(piece.piece_type)
                    img = self.pieces_imgs[piece_color + piece_type]
                    img_center = (
                        file_index * self.config.square_size
                        + self.config.square_size // 2,
                        rank_index * self.config.square_size
                        + self.config.square_size // 2,
                    )
                    self.surface.blit(img, img.get_rect(center=img_center))

    # def evaluation(self, engine):
    #     info = engine.analyse(self.board, chess.engine.Limit(time=0.1))
    #     score = eval(str(info['score'].white())) * 0.01
    #     lbl = self.config.small_font.render(str(round(score,1)), 1, (0,255,0))
    #     lbl_pos = (10, 380)
    #     rect = (
    #         0, 0, 
    #         self.config.evaluation_bar_dimensions[0],
    #         self.config.evaluation_bar_dimensions[1],
    #     )
    #     pygame.draw.rect(self.evaluation_bar, (0, 0, 0), rect)
        
    #     bar_height = (score) * 20
        
    #     rect = (
    #         0, self.config.evaluation_bar_dimensions[1]//2 - bar_height, 
    #         self.config.evaluation_bar_dimensions[0],
    #         self.config.evaluation_bar_dimensions[1]//2 + bar_height,
    #     )
    #     pygame.draw.rect(self.evaluation_bar, (255, 255, 255), rect)
    #     self.evaluation_bar.blit(lbl, lbl_pos)
        

    def run(self, engine) -> None:
        # pygame.time.set_timer(pygame.USEREVENT, 1000)
        
        # while not self.board.is_game_over():
        while True:
            self.draw_board()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.event_handler(event)
                elif event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                # elif event.type == pygame.USEREVENT:
                #     # when the reload timer runs out, reset it
                #     self.evaluation(engine)
            self.draw_pieces()
            self.clock.tick(60)
            # self.screen.blit(self.evaluation_bar, (0, 0))
            self.screen.blit(self.surface, (40, 0))
            pygame.display.update()


if __name__ == "__main__":
    engine = chess.engine.SimpleEngine.popen_uci('stockfish/stockfish-windows-x86-64-avx2.exe')
    game = Game()
    game.run(engine)
