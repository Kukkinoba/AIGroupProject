# Rural Pathfinder

A GUI application for finding optimal routes through a rural road network using Prolog-based pathfinding logic.

## Features

- **Route Finder**: Find paths between locations with various criteria:
  - Shortest path
  - Avoid unpaved roads
  - Avoid cistern roads
  - Avoid pothole roads

- **Admin Panel**: Manage road network data:
  - Add new roads
  - Edit existing roads
  - Delete roads
  - View all roads in the network

- **Import/Export**: 
  - Import road data from Prolog files (`.pl`)
  - Export road data to Prolog files

## Project Structure

```
Project/
├── app.py                 # Main GUI application (Tkinter)
├── prolog/
│   └── roads.pl          # Prolog knowledge base for road network
├── data/
│   └── roads_backup.pl   # Backup of road data
└── README.md             # This file
```

## Road Data Format

Roads are defined with the following properties:
- **Source**: Starting location
- **Destination**: Ending location
- **Distance**: Length in kilometers
- **Type**: `paved`, `unpaved`, `cistern`, or `potholes`
- **Status**: `open` or `closed`

## Requirements

- Python 3.x
- Tkinter (usually included with Python)
- PySwip (for Prolog integration)
- NetworkX (for graph operations)

## Usage

Run the application:
```bash
python app.py
```

## Status

Currently in development. The GUI shell is complete, and Prolog integration is being implemented.

