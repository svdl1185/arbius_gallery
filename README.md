# 🎨 Arbius Gallery

A beautiful web gallery for AI-generated images from the Arbius network on Arbitrum. This Django application scans the blockchain for `submitSolution` transactions and displays the resulting AI artwork.

## ✨ Features

- **🔍 Automatic Blockchain Scanning**: Continuously monitors Arbitrum for new Arbius images
- **🎯 Smart CID Extraction**: Decodes IPFS content identifiers from transaction data
- **🖼️ Beautiful Gallery Interface**: Modern, responsive design with dark theme
- **⚡ Real-time Updates**: Shows latest AI-generated images as they're created
- **📱 Mobile Responsive**: Works perfectly on all devices
- **🚀 One-click Heroku Deployment**: Easy deployment with automated setup

## 🚀 Quick Start with Heroku

1. **Clone and Deploy**:
   ```bash
   git clone [your-repo-url]
   cd arbius_gallery
   ./deploy.sh
   ```

2. **Set up 1-minute scanning**:
   ```bash
   ./setup_github.sh
   ```

## 🔄 Scanning Options

### Heroku Scheduler (10-minute intervals)
Heroku's built-in scheduler supports minimum 10-minute intervals:
1. Run: `heroku addons:open scheduler --app your-app-name`
2. Add job: `python3 manage.py scan_arbius --blocks 100 --quiet`

### GitHub Actions (1-minute intervals)
For more frequent scanning, use the included GitHub Actions workflow:
1. Push your code to GitHub
2. Add repository secrets:
   - `HEROKU_API_KEY`: Your Heroku API token
   - `HEROKU_APP_NAME`: Your Heroku app name
3. The workflow will automatically scan every minute!

## 🛠️ Manual Development Setup

1. **Create virtual environment**:
   ```bash
   python -m venv arbius_env
   source arbius_env/bin/activate  # On Windows: arbius_env\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up database**:
   ```bash
   python manage.py migrate
   ```

4. **Run development server**:
   ```bash
   python manage.py runserver
   ```

5. **Scan for images**:
   ```bash
   # Scan recent blocks
   python manage.py scan_arbius --blocks 100
   
   # Quiet mode for automation
   python manage.py scan_arbius --blocks 100 --quiet
   ```

## 📊 How It Works

1. **Blockchain Monitoring**: Scans Arbitrum blocks for `submitSolution` transactions
2. **Transaction Analysis**: Extracts solution data from contract interactions
3. **CID Decoding**: Decodes IPFS content identifiers using base58 encoding
4. **Image Verification**: Checks IPFS accessibility and caches metadata
5. **Gallery Display**: Shows images in a beautiful, responsive interface

## 🔧 Configuration

### Environment Variables
- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: PostgreSQL URL (auto-configured on Heroku)

### Blockchain Settings
- `ARBISCAN_API_KEY`: API key for Arbiscan
- `ENGINE_CONTRACT_ADDRESS`: Arbius engine contract
- `ROUTER_CONTRACT_ADDRESS`: Arbius router contract
- `ARBITRUM_RPC_URL`: Arbitrum RPC endpoint
- `IPFS_BASE_URL`: IPFS gateway URL

## 📁 Project Structure

```
arbius_gallery/
├── gallery/                    # Main Django app
│   ├── models.py              # Database models
│   ├── views.py               # View logic
│   ├── services.py            # Blockchain scanning logic
│   ├── templates/             # HTML templates
│   └── management/commands/   # Management commands
├── static/                    # Static files (CSS, JS)
├── .github/workflows/         # GitHub Actions
├── deploy.sh                  # Heroku deployment script
├── setup_github.sh           # GitHub setup script
└── requirements.txt          # Python dependencies
```

## 🔍 Management Commands

### scan_arbius
Scans the blockchain for new Arbius images:
```bash
python manage.py scan_arbius [--blocks N] [--quiet]
```

Options:
- `--blocks N`: Number of recent blocks to scan (default: 100)
- `--quiet`: Suppress output for automated runs

## 🚀 Deployment

### Heroku (Recommended)
1. Run the deployment script: `./deploy.sh`
2. Set up scanning with either:
   - Heroku Scheduler (10-min intervals)
   - GitHub Actions (1-min intervals)

### Manual Deployment
1. Set environment variables
2. Run migrations: `python manage.py migrate`
3. Collect static files: `python manage.py collectstatic`
4. Set up scheduled scanning

## 🐛 Troubleshooting

### 500 Server Error
- Check that all environment variables are set
- Ensure database migrations have run
- Verify ALLOWED_HOSTS includes your domain

### No Images Found
- Check API key validity
- Verify contract addresses
- Ensure RPC endpoint is accessible
- Try scanning more blocks

### GitHub Actions Not Working
- Verify repository secrets are set correctly
- Check HEROKU_API_KEY is valid
- Ensure HEROKU_APP_NAME matches your app

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **Arbius Team**: For creating the decentralized AI network
- **Arbitrum**: For the fast, low-cost blockchain infrastructure
- **Django Community**: For the excellent web framework

---

**🎉 Enjoy exploring the beautiful world of AI-generated art on Arbius!** 