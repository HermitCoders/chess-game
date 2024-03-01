from config import Config
import chess
import chess.engine
import pygame
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
        self.freespace = pygame.Surface(self.config.freespace_dimensions)
        self.freespace.fill((60, 60, 60))
        self.pieces_imgs = self.load_pieces()

        self.board = board
        self.highlighted_squares = []
        self.source_square = None
        self.target_squares = []
        self.promotion_squares = []
        self.promotion_source_squares = []
        self.move_stack = []

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
                self.surface,
                color,
                center,
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
        possible_promotions = defaultdict(list)

        for pos in list(self.board.legal_moves):
            if pos.promotion:
                possible_promotions[pos.from_square].append(pos.to_square)
            possible_moves[pos.from_square].append(pos.to_square)

        try:
            selected_square = self.get_selected_square(event)
        except:
            return

        if selected_square == self.source_square:
            self.source_square = None
            self.target_squares = []

        elif selected_square in possible_moves.keys():
            self.source_square = selected_square
            self.target_squares = possible_moves[selected_square]

        if selected_square in possible_promotions.keys():
            self.promotion_source_squares = selected_square
            self.promotion_squares = possible_promotions[selected_square]

    def move(self, event):
        try:
            selected_square = self.get_selected_square(event)
        except:
            return

        if (
            selected_square in self.target_squares
            and selected_square in self.promotion_squares
            and self.source_square == self.promotion_source_squares
        ):
            self.board.push(
                chess.Move(self.source_square, selected_square, promotion=5)
            )
            self.promotion_source_squares = None
            self.promotion_squares = []
            self.source_square = None
            self.target_squares = []

        if selected_square in self.target_squares:
            self.board.push(chess.Move(self.source_square, selected_square))
            self.source_square = None
            self.target_squares = []

    def get_selected_square(self, event):
        if event.pos[0] <= self.config.board_dimensions[0]:
            selected_file_index = event.pos[0] // self.config.square_size
            selected_rank_index = 7 - event.pos[1] // self.config.square_size

            selected_square = chess.square(selected_file_index, selected_rank_index)

            return selected_square
        else:
            return

    def get_highlighted_squares(self, event):
        try:
            selected_square = self.get_selected_square(event)
        except:
            return

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
                label = self.config.font.render(str(8 - rank_index), 1, color)
                label_pos = (5, 2 + rank_index * self.config.square_size)
                self.surface.blit(label, label_pos)

            # col coordinates
            if rank_index == 7:
                color = (
                    self.config.theme.squares.dark
                    if (file_index + rank_index) % 2 == 0
                    else self.config.theme.squares.light
                )
                label = self.config.font.render(chess.FILE_NAMES[file_index], 1, color)
                label_pos = (
                    file_index * self.config.square_size + self.config.square_size - 15,
                    self.config.board_dimensions[0] - 30,
                )
                self.surface.blit(label, label_pos)

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

    def draw_eval_bar(self, best_line):
        score = best_line["score"].white()
        depth = best_line["depth"]
        label = self.config.font.render(f"{str(score):<30}", 1, (255, 255, 255))
        label_pos = (
            self.config.freespace_dimensions[0] // 64,
            self.config.freespace_dimensions[1] // 64,
        )
        label1 = self.config.small_font.render(
            f"SF 16 - Depth{depth}", 1, (255, 255, 255)
        )
        label1_pos = (
            self.config.freespace_dimensions[0] // 1.5,
            self.config.freespace_dimensions[1] // 48,
        )
        rect = (
            0,
            0,
            self.config.freespace_dimensions[0],
            self.config.freespace_dimensions[1] // 16,
        )
        pygame.draw.rect(self.freespace, (40, 40, 40), rect)
        self.freespace.blit(label, label_pos)
        self.freespace.blit(label1, label1_pos)

        rect = (
            0,
            0,
            self.config.evaluation_bar_dimensions[0],
            self.config.evaluation_bar_dimensions[1],
        )
        pygame.draw.rect(self.evaluation_bar, (20, 20, 20), rect)

        try:
            bar_height = score.score() // 2
        except:
            bar_height = self.config.evaluation_bar_dimensions[1] // 2

        rect = (
            0,
            self.config.evaluation_bar_dimensions[1] // 2 - bar_height,
            self.config.evaluation_bar_dimensions[0],
            self.config.evaluation_bar_dimensions[1] // 2 + bar_height,
        )
        pygame.draw.rect(self.evaluation_bar, (240, 240, 240), rect)

    def display_evaluation(self, info):
        sorted_info = sorted(info, key=lambda d: d["score"].white(), reverse=True)
        rect = (
            0,
            self.config.freespace_dimensions[1] // 16,
            self.config.freespace_dimensions[0],
            3 * self.config.freespace_dimensions[1] // 32,
        )
        pygame.draw.rect(self.freespace, (50, 50, 50), rect)

        i = 0
        for eval in sorted_info[:3]:
            score = eval["score"].white()
            pv = eval["pv"]
            if len(pv) > 3:
                mapped_pv = " ".join(
                    f"{j+1}. {m.uci()[:2]} {m.uci()[2:]} " for j, m in enumerate(pv)
                )[:50]
                # print(score, i, mapped_pv)
                label = self.config.small_font.render(
                    f"{str(score):^7} | {mapped_pv}", 1, (255, 255, 255)
                )
                label_pos = (
                    self.config.freespace_dimensions[0] // 64,
                    (i + 2) * self.config.freespace_dimensions[1] // 32
                    + self.config.freespace_dimensions[1] // 256,
                )
                self.freespace.blit(label, label_pos)
                i += 1

        self.draw_eval_bar(sorted_info[0])

        pygame.draw.line(
            self.freespace,
            (100, 100, 100),
            (0, self.config.freespace_dimensions[1] // 16),
            (
                self.config.freespace_dimensions[0],
                self.config.freespace_dimensions[1] // 16,
            ),
        )

        pygame.draw.line(
            self.freespace,
            (100, 100, 100),
            (
                0,
                self.config.freespace_dimensions[1] // 16
                + 3 * self.config.freespace_dimensions[1] // 32,
            ),
            (
                self.config.freespace_dimensions[0],
                self.config.freespace_dimensions[1] // 16
                + 3 * self.config.freespace_dimensions[1] // 32,
            ),
        )

        pygame.draw.line(
            self.evaluation_bar,
            (20, 20, 20),
            (self.config.evaluation_bar_dimensions[0], 0),
            (
                self.config.evaluation_bar_dimensions[0],
                self.config.evaluation_bar_dimensions[1],
            ),
            width=5,
        )
        pygame.draw.line(
            self.evaluation_bar,
            (20, 20, 20),
            (0, 0),
            (0, self.config.evaluation_bar_dimensions[1]),
            width=3,
        )

    def evaluation(self, engine):
        info = engine.analyse(self.board, chess.engine.Limit(time=0.1), multipv=3)
        self.display_evaluation(info)
        self.display_move_stack()

    def display_move_stack(self):
        if self.board.move_stack:
            pass
            # print(self.board.move_stack)
            # for move in self.board.move_stack:
            #     str_move = move.uci()
            #     sq = chess.parse_square(str_move[2:])
            #     piece = self.board.piece_at(sq)
            #     piece_symbol = chess.piece_symbol(piece.piece_type)
            #     print(piece_symbol)
                # print(piece_symbol)
            # uci = self.board.move_stack[0].uci()
            # chess.Board.fen(uci)
            
        # if len(moves) % 2 == 0:
        #     for m in moves:
        #         move = chess.Move.from_uci(m)
        #         piece = self.board.piece_at(move[:2])
        #         piece_type = chess.piece_symbol(piece.piece_type)
        #         print(piece_type, move[2:])
            
            

    def run(self, engine) -> None:
        pygame.time.set_timer(pygame.USEREVENT, 250)

        running = True
        # while not self.board.is_game_over():
        while running:
            self.draw_board()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.event_handler(event)
                elif event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    engine.quit()
                    sys.exit()
                elif event.type == pygame.USEREVENT:
                    self.evaluation(engine)

            self.draw_pieces()
            self.clock.tick(60)
            self.screen.blit(self.surface, (0, 0))
            self.screen.blit(self.evaluation_bar, (800, 0))
            self.screen.blit(self.freespace, (830, 0))
            pygame.display.update()


if __name__ == "__main__":
    engine = chess.engine.SimpleEngine.popen_uci(
        "stockfish/stockfish-windows-x86-64-avx2.exe"
    )
    game = Game()
    game.run(engine)
