"""Classic Snake game with a polished Tkinter GUI.

Run:
    python snake_game.py
"""

from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: int
    y: int


class SnakeGame:
    GRID_WIDTH = 28
    GRID_HEIGHT = 20
    CELL_SIZE = 28

    BACKGROUND = "#111827"
    GRID_COLOR = "#1F2937"
    SNAKE_HEAD = "#34D399"
    SNAKE_BODY = "#10B981"
    FOOD_COLOR = "#F87171"
    PANEL_BG = "#0B1220"
    TEXT_COLOR = "#E5E7EB"
    ACCENT = "#60A5FA"

    START_DELAY_MS = 140
    MIN_DELAY_MS = 70
    SPEEDUP_EVERY = 4
    SPEED_STEP_MS = 7

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Snake")
        self.root.configure(bg=self.PANEL_BG)
        self.root.resizable(False, False)

        self.canvas_width = self.GRID_WIDTH * self.CELL_SIZE
        self.canvas_height = self.GRID_HEIGHT * self.CELL_SIZE

        frame = tk.Frame(root, bg=self.PANEL_BG, padx=18, pady=18)
        frame.pack()

        title = tk.Label(
            frame,
            text="🐍 Classic Snake",
            font=("Segoe UI", 22, "bold"),
            bg=self.PANEL_BG,
            fg=self.TEXT_COLOR,
            pady=8,
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w")

        self.canvas = tk.Canvas(
            frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg=self.BACKGROUND,
            highlightthickness=0,
        )
        self.canvas.grid(row=1, column=0, rowspan=3, padx=(0, 16))

        sidebar = tk.Frame(frame, bg=self.PANEL_BG)
        sidebar.grid(row=1, column=1, sticky="n")

        self.score_var = tk.StringVar(value="Score: 0")
        self.best_var = tk.StringVar(value="Best: 0")
        self.state_var = tk.StringVar(value="Press SPACE to start")

        self._info_label(sidebar, self.score_var, 0)
        self._info_label(sidebar, self.best_var, 1)
        self._info_label(sidebar, self.state_var, 2, wrap=190)

        controls = tk.Label(
            sidebar,
            text="Controls\n↑ ↓ ← → or WASD\nSPACE = start/restart",
            font=("Segoe UI", 11),
            justify="left",
            bg=self.PANEL_BG,
            fg="#9CA3AF",
            pady=18,
        )
        controls.grid(row=3, column=0, sticky="w")

        self.restart_btn = tk.Button(
            sidebar,
            text="Restart",
            command=self.restart,
            font=("Segoe UI", 11, "bold"),
            bg=self.ACCENT,
            fg="#0B1220",
            activebackground="#93C5FD",
            activeforeground="#0B1220",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
        )
        self.restart_btn.grid(row=4, column=0, sticky="w")

        self.best_score = 0
        self.after_id: str | None = None

        self.bind_keys()
        self.reset_state()
        self.draw()

    def _info_label(self, parent: tk.Widget, var: tk.StringVar, row: int, wrap: int = 0) -> None:
        label = tk.Label(
            parent,
            textvariable=var,
            font=("Segoe UI", 13, "bold") if row < 2 else ("Segoe UI", 12),
            bg=self.PANEL_BG,
            fg=self.TEXT_COLOR,
            pady=6,
            wraplength=wrap,
            justify="left",
        )
        label.grid(row=row, column=0, sticky="w")

    def bind_keys(self) -> None:
        self.root.bind("<Up>", lambda _: self.set_direction(0, -1))
        self.root.bind("<Down>", lambda _: self.set_direction(0, 1))
        self.root.bind("<Left>", lambda _: self.set_direction(-1, 0))
        self.root.bind("<Right>", lambda _: self.set_direction(1, 0))

        self.root.bind("w", lambda _: self.set_direction(0, -1))
        self.root.bind("s", lambda _: self.set_direction(0, 1))
        self.root.bind("a", lambda _: self.set_direction(-1, 0))
        self.root.bind("d", lambda _: self.set_direction(1, 0))

        self.root.bind("<space>", lambda _: self.space_action())

    def reset_state(self) -> None:
        cx, cy = self.GRID_WIDTH // 2, self.GRID_HEIGHT // 2
        self.snake = [Point(cx, cy), Point(cx - 1, cy), Point(cx - 2, cy)]
        self.direction = (1, 0)
        self.pending_direction = self.direction
        self.food = self.spawn_food()
        self.score = 0
        self.tick_delay = self.START_DELAY_MS
        self.running = False
        self.game_over = False
        self.score_var.set("Score: 0")
        self.best_var.set(f"Best: {self.best_score}")
        self.state_var.set("Press SPACE to start")

    def restart(self) -> None:
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.reset_state()
        self.draw()

    def space_action(self) -> None:
        if self.game_over:
            self.restart()
        if not self.running:
            self.running = True
            self.state_var.set("Good luck!")
            self.tick()

    def set_direction(self, dx: int, dy: int) -> None:
        if self.game_over:
            return
        curr_dx, curr_dy = self.direction
        if (dx, dy) == (-curr_dx, -curr_dy):
            return
        self.pending_direction = (dx, dy)
        if not self.running:
            self.running = True
            self.state_var.set("Good luck!")
            self.tick()

    def spawn_food(self) -> Point:
        occupied = set(self.snake)
        while True:
            p = Point(
                random.randint(0, self.GRID_WIDTH - 1),
                random.randint(0, self.GRID_HEIGHT - 1),
            )
            if p not in occupied:
                return p

    def tick(self) -> None:
        if not self.running:
            return

        self.direction = self.pending_direction
        head = self.snake[0]
        new_head = Point(head.x + self.direction[0], head.y + self.direction[1])

        if (
            new_head.x < 0
            or new_head.x >= self.GRID_WIDTH
            or new_head.y < 0
            or new_head.y >= self.GRID_HEIGHT
            or new_head in self.snake
        ):
            self.running = False
            self.game_over = True
            self.best_score = max(self.best_score, self.score)
            self.best_var.set(f"Best: {self.best_score}")
            self.state_var.set("Game over — press SPACE to restart")
            self.draw()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            self.score_var.set(f"Score: {self.score}")
            self.food = self.spawn_food()
            if self.score % self.SPEEDUP_EVERY == 0:
                self.tick_delay = max(self.MIN_DELAY_MS, self.tick_delay - self.SPEED_STEP_MS)
        else:
            self.snake.pop()

        self.draw()
        self.after_id = self.root.after(self.tick_delay, self.tick)

    def draw(self) -> None:
        self.canvas.delete("all")

        for x in range(0, self.canvas_width + 1, self.CELL_SIZE):
            self.canvas.create_line(x, 0, x, self.canvas_height, fill=self.GRID_COLOR)
        for y in range(0, self.canvas_height + 1, self.CELL_SIZE):
            self.canvas.create_line(0, y, self.canvas_width, y, fill=self.GRID_COLOR)

        fx, fy = self.food.x * self.CELL_SIZE, self.food.y * self.CELL_SIZE
        pad = 5
        self.canvas.create_oval(
            fx + pad,
            fy + pad,
            fx + self.CELL_SIZE - pad,
            fy + self.CELL_SIZE - pad,
            fill=self.FOOD_COLOR,
            outline="",
        )

        for i, part in enumerate(self.snake):
            x1 = part.x * self.CELL_SIZE + 2
            y1 = part.y * self.CELL_SIZE + 2
            x2 = x1 + self.CELL_SIZE - 4
            y2 = y1 + self.CELL_SIZE - 4
            self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=self.SNAKE_HEAD if i == 0 else self.SNAKE_BODY,
                outline="",
            )

        if self.game_over:
            self.canvas.create_rectangle(
                0,
                self.canvas_height // 2 - 46,
                self.canvas_width,
                self.canvas_height // 2 + 46,
                fill="#000000",
                stipple="gray50",
                outline="",
            )
            self.canvas.create_text(
                self.canvas_width // 2,
                self.canvas_height // 2 - 12,
                text="Game Over",
                font=("Segoe UI", 28, "bold"),
                fill="#F9FAFB",
            )
            self.canvas.create_text(
                self.canvas_width // 2,
                self.canvas_height // 2 + 24,
                text="Press SPACE to restart",
                font=("Segoe UI", 14),
                fill="#D1D5DB",
            )


def main() -> None:
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
