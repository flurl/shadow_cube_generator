"""
Shadow Cube Generator - A tool for creating and exporting grid-based designs for 3D printing shadow cubes
Copyright (C) 2024 Florian Klug-Göri

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import math
import os
import subprocess

import numpy as np
from solid2 import cube, difference, rotate, scad_render_to_file, translate, union
from stl import mesh
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk



class PreferencesDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Preferences")
        self.geometry("400x400")  # Increased height to accommodate new field
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Load current preferences
        self.cell_size = tk.DoubleVar(value=parent.preferences.get('cell_size', 3.0))
        self.border_thickness = tk.DoubleVar(value=parent.preferences.get('border_thickness', 0.4))
        self.pocket_depth = tk.IntVar(value=parent.preferences.get('pocket_depth', 2))
        self.max_recent_files = tk.IntVar(value=parent.preferences.get('max_recent_files', 5))
        self.openscad_binary = tk.StringVar(value=parent.preferences.get('openscad_binary', ''))
        
        # Create widgets
        self.create_widgets()
        
        # Center the dialog
        self.center_window()
        
    def create_widgets(self):
        # STL Export settings
        cell_frame = ttk.LabelFrame(self, text="STL Export Settings", padding="10")
        cell_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(cell_frame, text="Cell Size (mm):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(cell_frame, textvariable=self.cell_size).grid(row=0, column=1, padx=5)
        
        ttk.Label(cell_frame, text="Border Thickness (mm):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(cell_frame, textvariable=self.border_thickness).grid(row=1, column=1, padx=5)

        ttk.Label(cell_frame, text="Pocket depth:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(cell_frame, textvariable=self.pocket_depth).grid(row=2, column=1, padx=5)
        
        # General settings
        general_frame = ttk.LabelFrame(self, text="General Settings", padding="10")
        general_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(general_frame, text="Max Recent Files:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(general_frame, textvariable=self.max_recent_files).grid(row=0, column=1, padx=5)
        
        # OpenSCAD settings
        openscad_frame = ttk.LabelFrame(self, text="OpenSCAD Settings", padding="10")
        openscad_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(openscad_frame, text="OpenSCAD Binary:").grid(row=0, column=0, sticky=tk.W, pady=5)
        binary_entry = ttk.Entry(openscad_frame, textvariable=self.openscad_binary)
        binary_entry.grid(row=0, column=1, padx=5, sticky=tk.EW)
        ttk.Button(openscad_frame, text="Browse...", command=self.browse_openscad_binary).grid(row=0, column=2, padx=5)
        
        openscad_frame.grid_columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_preferences).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)
        
    def browse_openscad_binary(self):
        file_path = filedialog.askopenfilename(
            title="Select OpenSCAD Binary",
            filetypes=[
                ("OpenSCAD Binary", "openscad*"),
                ("All Executables", "*.exe"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.openscad_binary.set(file_path)
    
    def save_preferences(self):
        try:
            cell_size = float(self.cell_size.get())
            border_thickness = float(self.border_thickness.get())
            pocket_depth = int(self.pocket_depth.get())
            max_recent = int(self.max_recent_files.get())
            openscad_path = self.openscad_binary.get()
            
            if cell_size <= 0 or border_thickness <= 0 or max_recent <= 0:
                raise ValueError("Values must be positive")
            
            if openscad_path and not os.path.isfile(openscad_path):
                raise ValueError("OpenSCAD binary path is invalid")
                
            self.parent.preferences['cell_size'] = cell_size
            self.parent.preferences['border_thickness'] = border_thickness
            self.parent.preferences['pocket_depth'] = pocket_depth
            self.parent.preferences['max_recent_files'] = max_recent
            self.parent.preferences['openscad_binary'] = openscad_path
            self.parent.save_preferences()
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')


class ShadowCubeGenerator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shadow Cube Generator")
        
        # Load preferences
        self.preferences = self.load_preferences()
        
        # Initialize project variables
        self.current_project_path = None
        self.project_modified = False
        self.project_directory = None
        self.project_name = None
        
        # Create menu
        self.create_menu()
        
        # Create main container
        main_container = ttk.Frame(self)
        main_container.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
        
        # Create input frame at the top
        input_frame = ttk.Frame(main_container)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create input field for grid size
        self.input_label = ttk.Label(input_frame, text="Enter a number between 8 and 64:")
        self.input_label.pack(side=tk.LEFT, padx=5)
        
        self.input_field = ttk.Entry(input_frame, width=10)
        self.input_field.pack(side=tk.LEFT, padx=5)
        self.input_field.insert(0, "8")
        self.input_field.bind('<Return>', lambda event: self.generate_grid())
        
        self.generate_button = ttk.Button(input_frame, text="Generate Grid", command=self.generate_grid)
        self.generate_button.pack(side=tk.LEFT, padx=5)
        
        # Create frame for all views
        self.views_frame = ttk.Frame(main_container)
        self.views_frame.pack(expand=True, fill=tk.BOTH)
        
        # Configure grid layout - 2 rows, 2 columns
        self.views_frame.grid_rowconfigure(0, weight=1)
        self.views_frame.grid_rowconfigure(1, weight=1)
        self.views_frame.grid_columnconfigure(0, weight=1)
        self.views_frame.grid_columnconfigure(1, weight=1)
        
        # Create frames for each view in the specified layout
        self.view_frames = {}
        self.grid_canvases = {}
        
        # Create Front view (top left)
        self.view_frames["Front"] = ttk.LabelFrame(self.views_frame, text="Front View")
        self.view_frames["Front"].grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Create Side view (top right)
        self.view_frames["Side"] = ttk.LabelFrame(self.views_frame, text="Side View")
        self.view_frames["Side"].grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # Create Top view (bottom left)
        self.view_frames["Top"] = ttk.LabelFrame(self.views_frame, text="Top View")
        self.view_frames["Top"].grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Initialize grids
        self.grid_cells = {
            "Top": [],
            "Front": [],
            "Side": []
        }
        self.grid_size = 0
        
        # Keep track of exported STL files
        self.exported_stls = {
            "Top": None,
            "Front": None,
            "Side": None
        }
        
        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Update window title
        self.update_title()
        
        # Set minimum window size
        self.minsize(800, 600)
    
    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        self.file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=self.file_menu, underline=0)
        self.file_menu.add_command(label="New Project", command=self.new_project, accelerator="Ctrl+N", underline=0)
        self.file_menu.add_command(label="Open Project...", command=self.open_project, accelerator="Ctrl+O", underline=0)
        self.file_menu.add_command(label="Save Project", command=self.save_project, accelerator="Ctrl+S", underline=0)
        self.file_menu.add_command(label="Save Project As...", command=self.save_project_as, accelerator="Ctrl+Shift+S", underline=0)
        self.file_menu.add_separator()
        
        # Recent files submenu
        self.recent_menu = tk.Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label="Recent Projects", menu=self.recent_menu, underline=0)
        self.update_recent_files_menu()
        
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export with OpenSCAD...", command=self.export_openscad, accelerator="Ctrl+O", underline=0)
        self.file_menu.add_command(label="Export STL files..", command=self.export_grid_stl, accelerator="Ctrl+E", underline=0)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Alt+F4", underline=1)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu, underline=0)
        tools_menu.add_command(label="Generate Grid", command=self.generate_grid, accelerator="Ctrl+G", underline=0)
        tools_menu.add_command(label="Clear Grid", command=self.clear_grid, accelerator="Ctrl+L", underline=0)
        tools_menu.add_command(label="Invert Selection", command=self.invert_selection, accelerator="Ctrl+I", underline=0)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu, underline=0)
        settings_menu.add_command(label="Preferences...", command=self.show_preferences, accelerator="Ctrl+P", underline=0)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu, underline=0)
        help_menu.add_command(label="About", command=self.show_about, accelerator="F1", underline=0)
        
        # Bind keyboard shortcuts
        self.bind_all("<Control-n>", lambda e: self.new_project())
        self.bind_all("<Control-o>", lambda e: self.open_project())
        self.bind_all("<Control-s>", lambda e: self.save_project())
        self.bind_all("<Control-S>", lambda e: self.save_project_as())  # Ctrl+Shift+S
        self.bind_all("<Control-e>", lambda e: self.export_grid_stl())
        self.bind_all("<Control-o>", lambda e: self.export_openscad())
        self.bind_all("<Control-l>", lambda e: self.clear_grid())
        self.bind_all("<Control-i>", lambda e: self.invert_selection())
        self.bind_all("<Control-p>", lambda e: self.show_preferences())
        self.bind_all("<F1>", lambda e: self.show_about())
        self.bind_all("<Control-g>", lambda e: self.generate_grid())
    
    def update_recent_files_menu(self):
        # Clear existing items
        self.recent_menu.delete(0, tk.END)
        
        # Get recent files list
        recent_files = self.preferences.get('recent_files', [])
        
        if recent_files:
            for path in recent_files:
                self.recent_menu.add_command(
                    label=path,
                    command=lambda p=path: self.open_recent_project(p)
                )
            self.recent_menu.add_separator()
            self.recent_menu.add_command(label="Clear Recent", command=self.clear_recent_files)
        else:
            self.recent_menu.add_command(label="(No Recent Projects)", state=tk.DISABLED)
    
    def add_to_recent_files(self, path):
        recent_files = self.preferences.get('recent_files', [])
        max_recent = self.preferences.get('max_recent_files', 5)
        
        # Remove if already exists
        if path in recent_files:
            recent_files.remove(path)
            
        # Add to front of list
        recent_files.insert(0, path)
        
        # Trim list to max size
        recent_files = recent_files[:max_recent]
        
        # Save and update menu
        self.preferences['recent_files'] = recent_files
        self.save_preferences()
        self.update_recent_files_menu()
    
    def clear_recent_files(self):
        self.preferences['recent_files'] = []
        self.save_preferences()
        self.update_recent_files_menu()
    
    def new_project(self):
        if self.project_modified:
            if not self.confirm_discard_changes():
                return
                
        self.grid_cells = {
            "Top": [],
            "Front": [],
            "Side": []
        }
        self.grid_size = 0
        self.current_project_path = None
        self.project_directory = None
        self.project_name = None
        self.project_modified = False
        self.input_field.delete(0, tk.END)
        self.update_title()
        
        # Clear exported STLs tracking
        self.exported_stls = {
            "Top": None,
            "Front": None,
            "Side": None
        }
        
        if hasattr(self, 'grid_canvas') and self.grid_canvas:
            self.grid_canvas.destroy()
        self.grid_canvas = None
    
    def open_project(self):
        if self.project_modified:
            if not self.confirm_discard_changes():
                return
                
        file_path = filedialog.askopenfilename(
            defaultextension=".grid",
            filetypes=[("Grid Project", "*.grid"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.load_project(file_path)
    
    def open_recent_project(self, path):
        if not os.path.exists(path):
            messagebox.showerror("Error", f"Project file not found:\n{path}")
            # Remove from recent files
            recent_files = self.preferences.get('recent_files', [])
            recent_files.remove(path)
            self.preferences['recent_files'] = recent_files
            self.save_preferences()
            self.update_recent_files_menu()
            return
            
        if self.project_modified:
            if not self.confirm_discard_changes():
                return
                
        self.load_project(path)
    
    def load_project(self, file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            self.grid_size = data['grid_size']
            self.grid_cells = data['grid_cells']
            self.current_project_path = file_path
            self.project_name = os.path.splitext(os.path.basename(file_path))[0]
            self.project_directory = os.path.dirname(file_path)
            self.project_modified = False
            
            # Update UI
            self.input_field.delete(0, tk.END)
            self.input_field.insert(0, str(self.grid_size))
            for view in ["Top", "Front", "Side"]:
                self.show_view(view)
            self.update_title()
            
            # Add to recent files
            self.add_to_recent_files(file_path)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project:\n{str(e)}")
    
    def save_project(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".grid",
            filetypes=[("Grid Project", "*.grid"), ("All Files", "*.*")]
        )
        
        if file_path:
            # Update project name and directory
            self.project_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # If file exists, use its directory
            if os.path.exists(file_path):
                self.project_directory = os.path.dirname(file_path)
            else:
                # For new files, create project directory
                project_dir = os.path.dirname(file_path)
                self.project_directory = os.path.join(project_dir, self.project_name)
                os.makedirs(self.project_directory, exist_ok=True)
                # Update file path to be inside project directory
                file_path = os.path.join(self.project_directory, f"{self.project_name}.grid")
            
            self.save_project_to_file(file_path)
    
    def save_project_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".grid",
            filetypes=[("Grid Project", "*.grid"), ("All Files", "*.*")]
        )
        
        if file_path:
            # Update project name
            self.project_name = os.path.splitext(os.path.basename(file_path))[0]
            self.save_project_to_file(file_path)
    
    def save_project_to_file(self, file_path):
        try:
            data = {
                'grid_size': self.grid_size,
                'grid_cells': self.grid_cells
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f)
                
            self.current_project_path = file_path
            self.project_modified = False
            self.update_title()
            
            # Add to recent files
            self.add_to_recent_files(file_path)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project:\n{str(e)}")
    
    def update_title(self):
        title = "Shadow Cube Generator"
        if self.project_name:
            title += f" - {self.project_name}"
        if self.project_modified:
            title += " *"
        self.title(title)
    
    def confirm_discard_changes(self):
        return messagebox.askyesno(
            "Unsaved Changes",
            "You have unsaved changes. Do you want to continue and lose these changes?"
        )
    
    def on_closing(self):
        if self.project_modified:
            if not self.confirm_discard_changes():
                return
        self.quit()
    
    def toggle_cell(self, view, cell, row, col):
        current_fill = self.grid_canvases[view].itemcget(cell, "fill")
        if current_fill == "white":
            self.grid_canvases[view].itemconfig(cell, fill="black")
            self.grid_cells[view][row][col] = True
        else:
            self.grid_canvases[view].itemconfig(cell, fill="white")
            self.grid_cells[view][row][col] = False
        self.project_modified = True
        self.update_title()
    
    def clear_grid(self):
        for view in ["Top", "Front", "Side"]:
            if view in self.grid_canvases:
                for row in range(self.grid_size):
                    for col in range(self.grid_size):
                        self.grid_cells[view][row][col] = False
                self.show_view(view)
    
    def invert_selection(self):
        for view in ["Top", "Front", "Side"]:
            if view in self.grid_canvases:
                for row in range(self.grid_size):
                    for col in range(self.grid_size):
                        self.grid_cells[view][row][col] = not self.grid_cells[view][row][col]
                self.show_view(view)
    
    def show_preferences(self):
        PreferencesDialog(self)
    
    def show_about(self):
        messagebox.showinfo(
            "About Shadow Cube Generator",
            "Shadow Cube Generator v0.1\n\n"
            "A tool for creating and exporting grid-based designs\n"
            "for 3D printing shadow cubes.\n\n"
            "Copyright 2024, Florian Klug-Göri"
            
        )
    
    def load_preferences(self):
        try:
            if os.path.exists('preferences.json'):
                with open('preferences.json', 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {'cell_size': 3.0, 'border_thickness': 0.4, 'pocket_depth': 2}
    
    def save_preferences(self):
        try:
            with open('preferences.json', 'w') as f:
                json.dump(self.preferences, f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save preferences: {str(e)}")
    
    def show_view(self, view):
        if view in self.grid_canvases:
            self.grid_canvases[view].destroy()
        
        canvas_size = min(250, 500 // self.grid_size * self.grid_size)
        self.grid_canvases[view] = tk.Canvas(self.view_frames[view], width=canvas_size, height=canvas_size)
        self.grid_canvases[view].pack(padx=5, pady=5, expand=True)
        
        cell_size = canvas_size // self.grid_size
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                x1 = col * cell_size
                y1 = row * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                cell = self.grid_canvases[view].create_rectangle(x1, y1, x2, y2, outline="black")
                
                # Check if cell is in the border region (2 cells from edges)
                is_border = (row < 2 or row >= self.grid_size - 2 or 
                            col < 2 or col >= self.grid_size - 2)
                
                # Set the fill color and add X for border cells
                if is_border:
                    self.grid_canvases[view].itemconfig(cell, fill="white")
                    # Add X mark in the cell
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    offset = cell_size * 0.3
                    self.grid_canvases[view].create_line(cx - offset, cy - offset, 
                                                    cx + offset, cy + offset, 
                                                    fill="black", width=2)
                    self.grid_canvases[view].create_line(cx - offset, cy + offset, 
                                                    cx + offset, cy - offset, 
                                                    fill="black", width=2)
                else:
                    # Set the fill color based on the stored state for non-border cells
                    if self.grid_cells[view] and len(self.grid_cells[view]) > row:
                        cell_color = "black" if self.grid_cells[view][row][col] else "white"
                        self.grid_canvases[view].itemconfig(cell, fill=cell_color)
                    else:
                        self.grid_canvases[view].itemconfig(cell, fill="white")
                    
                    # Only bind click events for non-border cells
                    self.grid_canvases[view].tag_bind(cell, "<Button-1>", 
                        lambda event, v=view, c=cell, r=row, co=col: self.toggle_cell(v, c, r, co))

    def generate_grid(self):
        try:
            self.grid_size = int(self.input_field.get())
            if not 8 <= self.grid_size <= 64:
                raise ValueError
        except ValueError:
            self.input_field.delete(0, tk.END)
            self.input_field.insert(0, "Invalid input")
            return
        
        # Initialize grid states for all views
        for view in ["Top", "Front", "Side"]:
            # Initialize with border cells marked as True (X)
            self.grid_cells[view] = [[False for _ in range(self.grid_size)] 
                                for _ in range(self.grid_size)]
            # Mark border cells
            # for row in range(self.grid_size):
            #     for col in range(self.grid_size):
            #         if (row < 2 or row >= self.grid_size - 2 or 
            #             col < 2 or col >= self.grid_size - 2):
            #             self.grid_cells[view][row][col] = True
            self.show_view(view)

    
    
    # def export_grid_svg(self):
    #     current_view = self.view_var.get()
    #     # Create an SVG representation of the grid
    #     root = ET.Element("svg", width="500", height="500", viewBox="0 0 500 500")
    #     cell_size = 500 // self.grid_size
    #     for row in range(self.grid_size):
    #         for col in range(self.grid_size):
    #             x = col * cell_size
    #             y = row * cell_size
    #             cell = ET.SubElement(root, "rect", x=str(x), y=str(y), width=str(cell_size), height=str(cell_size), fill=self.grid_canvas.itemcget(self.grid_cells[current_view][row][col], "fill"), stroke="black", stroke_width="1")
        
    #     # Save the SVG file
    #     file_path = filedialog.asksaveasfilename(defaultextension=".svg", filetypes=[("SVG Files", "*.svg")])
    #     if file_path:
    #         tree = ET.ElementTree(root)
    #         tree.write(file_path)
    
        
    def export_grid_stl(self):
        if not self.current_project_path:
            messagebox.showerror("Error", "Please save the project first")
            return

        for current_view in ["Front", "Side", "Top"]:
            # Create the file path within the project directory
            file_path = os.path.join(self.project_directory, f"{current_view}.stl")
            
            try:
                self.create_stl(current_view, file_path)
                self.exported_stls[current_view] = file_path
                messagebox.showinfo("Success", f"Exported {current_view} view to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export {current_view} view:\n{str(e)}")
            
    def create_stl(self, view, file_path):
        # Use preferences for cell size and border thickness
        cell_size = self.preferences.get('cell_size', 3.0)
        border_thickness = self.preferences.get('border_thickness', 0.4)
        extrusion_height = self.grid_size * cell_size

        vertices = []
        faces = []

        for row in range(self.grid_size):
        #for row in range(2):
            for col in range(self.grid_size):
            #for col in range(1):
                cell_type = "black" if self.grid_cells[view][row][col] else "white"
                cell_type = "border" if (row == 0 or col == 0 or row == self.grid_size - 1 or col == self.grid_size - 1) else cell_type
                
                # Calculate cell boundaries
                x_start_outer = col * cell_size
                y_start_outer = row * cell_size
                x_end_outer = x_start_outer + cell_size
                y_end_outer = y_start_outer + cell_size

                x_start_inner = x_start_outer + border_thickness
                y_start_inner = y_start_outer + border_thickness
                x_end_inner = x_end_outer - border_thickness
                y_end_inner = y_end_outer - border_thickness

                # Define all vertices
                start_idx = len(vertices)
                vertices.extend([
                    # Outer shell vertices (0-7)
                    # Bottom
                    (x_start_outer, y_start_outer, 0),  # 0
                    (x_end_outer, y_start_outer, 0),    # 1
                    (x_end_outer, y_end_outer, 0),      # 2
                    (x_start_outer, y_end_outer, 0),    # 3
                    # Top
                    (x_start_outer, y_start_outer, extrusion_height),  # 4
                    (x_end_outer, y_start_outer, extrusion_height),    # 5
                    (x_end_outer, y_end_outer, extrusion_height),      # 6
                    (x_start_outer, y_end_outer, extrusion_height),    # 7

                    # Inner vertices at bottom (8-11)
                    (x_start_inner, y_start_inner, 0),   # 8
                    (x_end_inner, y_start_inner, 0),     # 9
                    (x_end_inner, y_end_inner, 0),       # 10
                    (x_start_inner, y_end_inner, 0),     # 11

                    # Inner vertices at top (12-15)
                    (x_start_inner, y_start_inner, extrusion_height),  # 12
                    (x_end_inner, y_start_inner, extrusion_height),    # 13
                    (x_end_inner, y_end_inner, extrusion_height),      # 14
                    (x_start_inner, y_end_inner, extrusion_height),    # 15

                    # Inner vertices at bottom pocket ceiling (16-19)
                    (x_start_inner, y_start_inner, cell_size * self.preferences.get('pocket_depth', 2) - border_thickness),  # 16
                    (x_end_inner, y_start_inner, cell_size * self.preferences.get('pocket_depth', 2) - border_thickness),    # 17
                    (x_end_inner, y_end_inner, cell_size * self.preferences.get('pocket_depth', 2) - border_thickness),      # 18
                    (x_start_inner, y_end_inner, cell_size * self.preferences.get('pocket_depth', 2) - border_thickness),    # 19

                    # Inner vertices at top pocket floor (20-23)
                    (x_start_inner, y_start_inner, extrusion_height - cell_size * self.preferences.get('pocket_depth', 2) + border_thickness),  # 20
                    (x_end_inner, y_start_inner, extrusion_height - cell_size * self.preferences.get('pocket_depth', 2) + border_thickness),    # 21
                    (x_end_inner, y_end_inner, extrusion_height - cell_size * self.preferences.get('pocket_depth', 2) + border_thickness),      # 22
                    (x_start_inner, y_end_inner, extrusion_height - cell_size * self.preferences.get('pocket_depth', 2) + border_thickness),    # 23
                ])

                
                if cell_type == "border":
                    # border cells
                    faces.extend([
                        # Bottom face
                        [start_idx + 0, start_idx + 1, start_idx + 2],
                        [start_idx + 0, start_idx + 2, start_idx + 3],
                        # Top face
                        [start_idx + 4, start_idx + 5, start_idx + 6],
                        [start_idx + 4, start_idx + 6, start_idx + 7],
                    ])
                else:
                    # Create outer shell faces - same for both black and white cells
                    faces.extend([
                        # Bottom face
                        [start_idx + 0, start_idx + 1, start_idx + 9],
                        [start_idx + 0, start_idx + 9, start_idx + 8],
                        [start_idx + 1, start_idx + 2, start_idx + 10],
                        [start_idx + 1, start_idx + 10, start_idx + 9],
                        [start_idx + 2, start_idx + 3, start_idx + 11],
                        [start_idx + 2, start_idx + 11, start_idx + 10],
                        [start_idx + 3, start_idx + 0, start_idx + 8],
                        [start_idx + 3, start_idx + 8, start_idx + 11],
                        # Top face
                        [start_idx + 4 + 0, start_idx + 4 + 1, start_idx + 4 + 9],
                        [start_idx + 4 + 0, start_idx + 4 + 9, start_idx + 4 + 8],
                        [start_idx + 4 + 1, start_idx + 4 + 2, start_idx + 4 + 10],
                        [start_idx + 4 + 1, start_idx + 4 + 10, start_idx + 4 + 9],
                        [start_idx + 4 + 2, start_idx + 4 + 3, start_idx + 4 + 11],
                        [start_idx + 4 + 2, start_idx + 4 + 11, start_idx + 4 + 10],
                        [start_idx + 4 + 3, start_idx + 4 + 0, start_idx + 4 + 8],
                        [start_idx + 4 + 3, start_idx + 4 + 8, start_idx + 4 + 11],
                        
                    ])
                
                print("row:", row, "col:", col, "type:", cell_type)
                
                if row == 0:
                    #print("N")
                    faces.extend([
                        # north face
                        [start_idx + 0, start_idx + 1, start_idx + 5],
                        [start_idx + 0, start_idx + 5, start_idx + 4],
                    ])
                
                if row == self.grid_size - 1:
                    #print("S")
                    # soutj face
                    faces.extend([
                        [start_idx + 2, start_idx + 3, start_idx + 7],
                        [start_idx + 2, start_idx + 7, start_idx + 6],
                    ])
                    
                if col == 0:
                    #print("W")
                    faces.extend([
                        # west face
                        [start_idx + 3, start_idx + 0, start_idx + 4],
                        [start_idx + 3, start_idx + 4, start_idx + 7],
                    ])
                    
                if col == self.grid_size - 1:
                    #print("E")
                    # east face
                    faces.extend([
                        [start_idx + 1, start_idx + 2, start_idx + 6],
                        [start_idx + 1, start_idx + 6, start_idx + 5],
                    ])
                    
                
                if cell_type == "white":
                    #print("white")
                    faces.extend([
                        # bottom pocket sides
                        [start_idx + 8, start_idx + 17, start_idx + 9],
                        [start_idx + 8, start_idx + 16, start_idx + 17],
                        [start_idx + 9, start_idx + 18, start_idx + 10],
                        [start_idx + 9, start_idx + 17, start_idx + 18],
                        [start_idx + 10, start_idx + 19, start_idx + 11],
                        [start_idx + 10, start_idx + 18, start_idx + 19],
                        [start_idx + 11, start_idx + 16, start_idx + 8],
                        [start_idx + 11, start_idx + 19, start_idx + 16],
                        # bottom pocket floor faces
                        [start_idx + 16, start_idx + 17, start_idx + 18],
                        [start_idx + 16, start_idx + 18, start_idx + 19],
                        
                        # top pocket sides
                        [start_idx + 20, start_idx + 13, start_idx + 21],
                        [start_idx + 20, start_idx + 12, start_idx + 13],
                        [start_idx + 21, start_idx + 14, start_idx + 22],
                        [start_idx + 21, start_idx + 13, start_idx + 14],
                    
                        [start_idx + 22, start_idx + 15, start_idx + 23],
                        [start_idx + 22, start_idx + 14, start_idx + 15],
                        [start_idx + 23, start_idx + 12, start_idx + 20],
                        [start_idx + 23, start_idx + 15, start_idx + 12],
                        # bottom pocket floor faces
                        [start_idx + 20, start_idx + 21, start_idx + 22],
                        [start_idx + 20, start_idx + 22, start_idx + 23],
                    ])
                    
                elif cell_type == "black":
                    #print("black")
                    # Inner faces
                    faces.extend([
                        [start_idx + 8, start_idx + 13, start_idx + 9],
                        [start_idx + 8, start_idx + 12, start_idx + 13],
                        [start_idx + 9, start_idx + 14, start_idx + 10],
                        [start_idx + 9, start_idx + 13, start_idx + 14],
                        [start_idx + 10, start_idx + 15, start_idx + 11],
                        [start_idx + 10, start_idx + 14, start_idx + 15],
                        [start_idx + 11, start_idx + 12, start_idx + 8],
                        [start_idx + 11, start_idx + 15, start_idx + 12],
                    ])
                
#
        # Convert to numpy arrays
        vertices = np.array(vertices)
        faces = np.array(faces)

        # Create the mesh
        grid_mesh = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
        for i, f in enumerate(faces):
            for j in range(3):
                grid_mesh.vectors[i][j] = vertices[f[j]]

         # Store original center
        original_center = np.mean(grid_mesh.vectors.reshape(-1, 3), axis=0)

        if view == "Side":
            grid_mesh.rotate([0.0, 1.0, 0.0], math.radians(90))
            grid_mesh.rotate([1.0, 0.0, 0.0], math.radians(90))
        elif view == "Front":
            grid_mesh.rotate([1.0, 0.0, 0.0], math.radians(-90))
            grid_mesh.rotate([0.0, 1.0, 0.0], math.radians(180))
            
        # Calculate new center after rotation
        new_center = np.mean(grid_mesh.vectors.reshape(-1, 3), axis=0)
        
         # Calculate required translation to move back to original position
        translation = original_center - new_center
        
        # Apply translation to vectors (which automatically updates points)
        grid_mesh.vectors += translation
        
        # Save the STL file
        if file_path:
            grid_mesh.save(file_path)
            self.exported_stls[view] = file_path


    def export_openscad(self):
        if not self.preferences.get('openscad_binary'):
            messagebox.showerror("Error", "OpenSCAD binary path not set. Please set it in Preferences.")
            return
        
        if not self.current_project_path:
            messagebox.showerror("Error", "Please save the project first")
            return

        
        # Create the file path within the project directory
        file_path = os.path.join(self.project_directory, f"{self.project_name}.stl")
        
        try:
            # Create temporary SCAD file
            temp_scad = os.path.join(os.path.dirname(file_path), "temp.scad")
            self.generate_openscad_file(temp_scad)
            
            # Run OpenSCAD to generate STL
            cmd = [self.preferences['openscad_binary'], '-o', file_path, temp_scad]
            subprocess.run(cmd, check=True)
            
            # Clean up temporary file
            os.remove(temp_scad)
            
            messagebox.showinfo("Success", f"Exported STL to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export STL:\n{str(e)}")        

            

    def generate_openscad_file(self, temp_scad):
        cell_size = self.preferences.get('cell_size', 3)
        border_thickness = self.preferences.get('border_thickness', 0.4)
        number_of_cells = self.grid_size
        pocket_depth = self.preferences.get('pocket_depth', 2)

        def pocket(row, col):
            # First pocket
            p1 = translate([cell_size*row+border_thickness, 
                        cell_size*col+border_thickness, 
                        0])(
                cube([cell_size-2*border_thickness, 
                    cell_size-2*border_thickness, 
                    cell_size*pocket_depth])
            )
            
            # Pocket on opposite side
            p2 = translate([cell_size*row+border_thickness, 
                        cell_size*col+border_thickness, 
                        cell_size*number_of_cells-cell_size*pocket_depth])(
                cube([cell_size-2*border_thickness, 
                    cell_size-2*border_thickness, 
                    cell_size*pocket_depth])
            )
            
            return p1 + p2

        def through_hole(row, col):
            return translate([cell_size*row+border_thickness, 
                            cell_size*col+border_thickness, 
                            0])(
                cube([cell_size-2*border_thickness, 
                    cell_size-2*border_thickness, 
                    cell_size*number_of_cells])
            )

        def cube_side(view):
            holes = union()
            for i in range(1, number_of_cells-1):
                for j in range(1, number_of_cells-1):
                    if (self.grid_cells[view][i][j]):
                        holes += through_hole(i, j)
                    else:
                        holes += pocket(i, j)
            return holes

        # Main construction
        main_shape = (
            translate([0, 0, number_of_cells*cell_size])(
                rotate([0, 90, 0])(
                    translate([0, number_of_cells*cell_size, 0])(
                        rotate([90, 0, 0])(
                            difference()(
                                cube(cell_size*number_of_cells),
                                cube_side("Top")  # top
                            )
                        )
                    ) - cube_side("Front")  # front
                )
            ) - cube_side("Side")  # side
        )
        
        scad_render_to_file(main_shape, temp_scad)
        



if __name__ == "__main__":
    app = ShadowCubeGenerator()
    app.mainloop()
