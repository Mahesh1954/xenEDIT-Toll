import tkinter as tk
from tkinter import colorchooser, filedialog
from PIL import Image, ImageDraw, ImageOps
import io

class XenEdit:
    def __init__(self, root):
        self.root = root
        self.root.title("xenEDIT Tool - Ubuntu Edition")
        self.root.geometry("1200x800")

        self.brush_color = "black"
        self.brush_size = 3
        self.current_tool = "pencil"
        self.eraser_on = False
        self.start_x = None
        self.start_y = None
        self.temp_shape = None
        self.undo_stack = []
        self.redo_stack = []
        self.crop_start = None
        self.crop_rect = None

        self.canvas = tk.Canvas(self.root, bg="white", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.setup_ui()
        self.bind_events()

    def setup_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.X)

        buttons = [
            ("Color", self.choose_color),
            ("Pencil", lambda: self.set_tool("pencil")),
            ("Eraser", lambda: self.set_tool("eraser")),
            ("Line", lambda: self.set_tool("line")),
            ("Rect", lambda: self.set_tool("rect")),
            ("Oval", lambda: self.set_tool("oval")),
            ("Triangle", lambda: self.set_tool("triangle")),
            ("Arrow", lambda: self.set_tool("arrow")),
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Crop", self.crop_tool),
            ("Export", self.export_image),
        ]

        for (txt, cmd) in buttons:
            tk.Button(top, text=txt, command=cmd).pack(side=tk.LEFT)

        self.size_slider = tk.Scale(top, from_=1, to=50, orient=tk.HORIZONTAL, label="Size")
        self.size_slider.set(self.brush_size)
        self.size_slider.pack(side=tk.LEFT)

    def bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_motion)
        self.canvas.bind("<ButtonRelease-1>", self.finish_draw)

    def choose_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.brush_color = color
            self.eraser_on = False

    def set_tool(self, tool):
        self.current_tool = tool
        self.eraser_on = (tool == "eraser")

    def start_draw(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.temp_shape = None

    def draw_motion(self, event):
        x, y = event.x, event.y
        color = "white" if self.eraser_on else self.brush_color
        width = self.size_slider.get()

        if self.current_tool == "pencil" or self.eraser_on:
            self.canvas.create_line(self.start_x, self.start_y, x, y,
                                    fill=color, width=width, capstyle=tk.ROUND, smooth=True)
            self.start_x, self.start_y = x, y
        elif self.current_tool in ("line", "rect", "oval", "triangle", "arrow"):
            if self.temp_shape:
                self.canvas.delete(self.temp_shape)

            if self.current_tool == "line":
                self.temp_shape = self.canvas.create_line(self.start_x, self.start_y, x, y,
                                                          fill=color, width=width)
            elif self.current_tool == "rect":
                self.temp_shape = self.canvas.create_rectangle(self.start_x, self.start_y, x, y,
                                                               outline=color, width=width)
            elif self.current_tool == "oval":
                self.temp_shape = self.canvas.create_oval(self.start_x, self.start_y, x, y,
                                                          outline=color, width=width)
            elif self.current_tool == "triangle":
                mid_x = (self.start_x + x) // 2
                self.temp_shape = self.canvas.create_polygon(self.start_x, y, x, y, mid_x, self.start_y,
                                                             outline=color, fill='', width=width)
            elif self.current_tool == "arrow":
                self.temp_shape = self.canvas.create_line(self.start_x, self.start_y, x, y,
                                                          arrow=tk.LAST, fill=color, width=width)

    def finish_draw(self, event):
        if self.current_tool != "pencil" and self.temp_shape:
            self.capture_state()
            self.temp_shape = None
        else:
            self.capture_state()

    def capture_state(self):
        self.canvas.update()
        ps = self.canvas.postscript(colormode='color')
        self.undo_stack.append(ps)
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.redraw_from_postscript(self.undo_stack[-1])

    def redo(self):
        if self.redo_stack:
            ps = self.redo_stack.pop()
            self.undo_stack.append(ps)
            self.redraw_from_postscript(ps)

    def redraw_from_postscript(self, ps_data):
        self.canvas.delete("all")
        img = Image.open(io.BytesIO(ps_data.encode('utf-8')))
        self.tk_img = tk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_img)

    def crop_tool(self):
        self.set_tool("crop")
        self.canvas.bind("<ButtonPress-1>", self.start_crop)
        self.canvas.bind("<B1-Motion>", self.draw_crop_box)
        self.canvas.bind("<ButtonRelease-1>", self.finish_crop)

    def start_crop(self, event):
        self.crop_start = (event.x, event.y)
        if self.crop_rect:
            self.canvas.delete(self.crop_rect)

    def draw_crop_box(self, event):
        if self.crop_start:
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)
            self.crop_rect = self.canvas.create_rectangle(self.crop_start[0], self.crop_start[1],
                                                          event.x, event.y,
                                                          outline='red', dash=(5, 2))

    def finish_crop(self, event):
        if self.crop_start:
            x1, y1 = self.crop_start
            x2, y2 = event.x, event.y
            self.crop_area(x1, y1, x2, y2)

    def crop_area(self, x1, y1, x2, y2):
        ps = self.canvas.postscript(colormode='color')
        img = Image.open(io.BytesIO(ps.encode('utf-8')))
        cropped = img.crop((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        self.canvas.delete("all")
        self.tk_img = tk.PhotoImage(cropped)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_img)
        self.capture_state()

    def export_image(self):
        file = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG files", "*.png"),
                                                       ("JPEG files", "*.jpg"),
                                                       ("PDF files", "*.pdf")])
        if file:
            ps = self.canvas.postscript(colormode='color')
            img = Image.open(io.BytesIO(ps.encode('utf-8')))
            if file.endswith(".pdf"):
                img.save(file, "PDF", resolution=100.0)
            else:
                img.save(file)
            print(f"Image exported to {file}")

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = XenEdit(root)
    root.mainloop()
