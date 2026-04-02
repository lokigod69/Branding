# LAZART Signing Engine (LSE)

A powerful branding and signing engine built with FastAPI backend and React frontend.

## Features

- **Image Processing Engine**: Advanced image manipulation and branding capabilities
- **Real-time Analysis**: WebSocket-based real-time processing and analysis
- **Preset System**: Pre-configured filter presets for various effects
- **Multi-stage Processing**: Pipeline-based image processing workflow
- **Modern UI**: React-based frontend with intuitive controls

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/lokigod69/Branding.git
cd Branding
```

2. **Set up Python environment**
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

3. **Set up frontend**
```bash
cd frontend
npm install
cd ..
```

### Running the Application

**Option 1: Development Mode**
```bash
# Start backend and frontend in development mode
start_dev.bat
```

**Option 2: Production Mode**
```bash
# Run the production server
python main.py
```

The application will be available at:
- Backend API: http://localhost:5555
- Frontend UI: http://localhost:5555 (if static build exists)
- API Documentation: http://localhost:5555/docs

## Project Structure

```
Branding/
├── api/                 # FastAPI backend routes
├── engine/              # Core image processing engine
├── frontend/            # React frontend application
├── static/              # Built frontend assets
├── presets/             # Filter presets
├── uploads/             # User uploads (gitignored)
├── output/              # Generated outputs (gitignored)
├── fonts/               # Font files for text rendering
├── main.py              # Main application entry point
└── requirements.txt     # Python dependencies
```

## Usage

1. **Upload Images**: Use the frontend to upload images for processing
2. **Apply Presets**: Choose from various pre-configured presets or create custom ones
3. **Real-time Preview**: See changes in real-time as you adjust parameters
4. **Export Results**: Download processed images to your local machine

## Available Presets

- **Solarize**: Solarization effect
- **Duotone**: Two-tone color effect
- **High Contrast Burn**: High contrast with burn effect
- **Frosted Glass**: Glass-like distortion effect
- **Luma Invert**: Luminance-based inversion
- **Channel Invert**: Channel-specific inversion
- **Difference Effects**: Various difference-based filters

## Development

### Backend Development
The backend uses FastAPI with automatic API documentation. Run in development mode for hot reloading:

```bash
python main.py
```

### Frontend Development
The frontend uses React with Vite. For development:

```bash
cd frontend
npm run dev
```

## API Endpoints

- `GET /api/status` - Health check
- `POST /api/upload` - Upload images
- `POST /api/process` - Process images with filters
- `WebSocket /ws` - Real-time processing updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is proprietary software. All rights reserved.

## Support

For issues and questions, please contact the development team.
