# Shadow Cube Generator

A tool for creating and exporting grid-based designs for 3D printing shadow cubes. This application allows users to design shadow cubes that cast different shadows when light is projected from different angles.

## Features

- Interactive grid-based design interface
- Three simultaneous views (Top, Front, Side)
- Export to STL format
- OpenSCAD integration for advanced 3D model generation

## Requirements

- Python 3.x
- Required Python packages:
  - numpy
  - solid2
  - numpy-stl
  - tkinter (usually comes with Python)

## Installation

1. Clone this repository: 
```bash
git clone https://github.com/flurl/shadow_cube_generator.git
```

2. Install required packages:
```bash
pip install numpy solid2 numpy-stl
```

3. (Optional) Install OpenSCAD if you want to use the OpenSCAD export feature:
   - Download from [OpenSCAD.org](https://openscad.org/)
   - Set the OpenSCAD binary path in the application preferences

## Usage

1. Run the application:
```bash
python cube_gen.py
```

2. Create a new project:
   - Enter a grid size (8-64)
   - Click "Generate Grid"
   - Design your shadow patterns in each view

3. Save your project:
   - File → Save Project
   - Choose a location and filename

4. Export your design:
   - File → Export STL files... (for individual view STLs)
   - File → Export with OpenSCAD... (for combined model)

## Controls

- Left-click to toggle cells
- Use the menu bar for all major functions
- Common keyboard shortcuts:
  - Ctrl+N: New Project
  - Ctrl+O: Open Project
  - Ctrl+S: Save Project
  - Ctrl+Shift+S: Save Project As
  - Ctrl+E: Export STL
  - Ctrl+L: Clear Grid
  - Ctrl+I: Invert Selection
  - Ctrl+P: Preferences
  - F1: About

## Preferences

Configure the following settings in Tools → Preferences:
- Cell Size (mm)
- Border Thickness (mm)
- Pocket Depth (in number of cells)
- Maximum Recent Files
- OpenSCAD Binary Path

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

## Author

Florian Klug-Göri (2024)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

