# Arbius Gallery

A Django web application that scans the Arbitrum blockchain for AI-generated images created through the Arbius protocol and displays them in a beautiful gallery interface.

## Features

- 🖼️ **Image Gallery**: Browse AI-generated images mined on Arbitrum
- 🔍 **Blockchain Scanner**: Automatically discovers new Arbius images
- 📊 **Statistics Dashboard**: View analytics about image generation
- 🎨 **Modern UI**: Beautiful, responsive design with dark theme
- 🔗 **IPFS Integration**: Direct links to IPFS-hosted content
- 📱 **Mobile Friendly**: Responsive design works on all devices

## Tech Stack

- **Backend**: Django 5.2.2
- **Frontend**: Bootstrap 5.3, Font Awesome
- **Database**: SQLite (easily configurable to PostgreSQL/MySQL)
- **Blockchain**: Arbitrum One (via Arbiscan API)
- **Storage**: IPFS for images

## Installation

### Prerequisites

- Python 3.8+
- pip
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd arbius_gallery
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv arbius_env
   source arbius_env/bin/activate  # On Windows: arbius_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Visit the application**
   Open your browser and go to `http://127.0.0.1:8000/`

## Configuration

The application is pre-configured with:

- **Arbiscan API Key**: `RSUGKSAPR7RXWF6U1S7FHYF7VSAY1I9M6D`
- **Engine Contract**: `0x9b51Ef044d3486A1fB0A2D55A6e0CeeAdd323E66`
- **Router Contract**: `0xecAba4E6a4bC1E3DE3e996a8B2c89e8B0626C9a1`
- **IPFS Gateway**: `https://ipfs.arbius.org/ipfs`

These can be modified in `arbius_gallery/settings.py`.

## Usage

### Web Interface

1. **Gallery View**: Browse all discovered Arbius images
2. **Image Details**: Click on any image to view detailed information
3. **Statistics**: View analytics about the gallery and scanning status
4. **Manual Scan**: Use the "Scan Blockchain" button to trigger discovery

### Command Line

**Scan for new images:**
```bash
python manage.py scan_arbius
```

**Scan specific number of blocks:**
```bash
python manage.py scan_arbius --blocks 500
```

**Force scan (bypass in-progress check):**
```bash
python manage.py scan_arbius --force
```

### Admin Interface

Access the Django admin at `http://127.0.0.1:8000/admin/` to:
- View and manage discovered images
- Monitor scan status
- Manually edit image metadata

## How It Works

1. **Transaction Discovery**: The scanner queries the Arbiscan API for transactions to the Arbius Engine contract
2. **Data Extraction**: Each transaction is analyzed to identify `submitSolution` calls
3. **CID Extraction**: The Content Identifier (CID) is extracted from transaction data
4. **Image URLs**: IPFS URLs are constructed using the CID pattern
5. **Database Storage**: Image metadata is stored in the SQLite database
6. **Gallery Display**: The web interface displays images with pagination

## Arbius Protocol Integration

The application integrates with the Arbius decentralized AI network:

- **Router Contract**: Handles task submissions
- **Engine Contract**: Processes miner solutions containing image CIDs
- **IPFS Storage**: Images are stored on IPFS with standard naming (`out-1.png`)
- **Arbitrum Blockchain**: All transactions are recorded on Arbitrum One

## API Endpoints

- `GET /api/scan-status/` - Get current scanning status
- `POST /api/scan/` - Trigger blockchain scan

## Development

### Project Structure

```
arbius_gallery/
├── arbius_gallery/          # Django project settings
├── gallery/                 # Main application
│   ├── models.py           # Database models
│   ├── views.py            # Web views
│   ├── services.py         # Blockchain scanning logic
│   ├── admin.py            # Admin interface
│   └── management/         # Custom Django commands
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
└── requirements.txt        # Python dependencies
```

### Key Models

- **ArbiusImage**: Stores image metadata and blockchain data
- **ScanStatus**: Tracks scanning progress and status

### Customization

- Modify `GALLERY_IMAGES_PER_PAGE` in settings for pagination
- Update CSS variables in `base.html` for custom styling
- Extend scanner logic in `gallery/services.py`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
- Check the GitHub Issues
- Review the Arbius documentation: https://arbius.org
- Examine Arbiscan transaction data for debugging

---

**Note**: This application scans public blockchain data and displays images hosted on IPFS. All content is generated by the Arbius network participants. 