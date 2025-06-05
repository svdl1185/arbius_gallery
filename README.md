# Arbius Gallery - AI Art on the Blockchain

A beautiful Django web application that automatically discovers and displays AI-generated artwork created through the Arbius protocol on the Arbitrum blockchain.

## Features

- 🎨 **Beautiful Modern UI** - Dark theme with gradient effects and smooth animations
- 🔍 **Automatic Discovery** - Scans the blockchain every 10 minutes for new AI artwork
- 🌐 **IPFS Integration** - Displays images stored on the decentralized IPFS network
- 📊 **Real-time Stats** - Live statistics and gallery insights
- 📱 **Responsive Design** - Works perfectly on desktop and mobile devices
- ⚡ **Fast Performance** - Optimized for speed with pagination and caching

## Live Demo

Visit the live gallery at: https://arbius-6cdb53a42247.herokuapp.com/

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd arbius_gallery
   ```

2. **Create virtual environment**
   ```bash
   python -m venv arbius_env
   source arbius_env/bin/activate  # On Windows: arbius_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

7. **Scan for images**
   ```bash
   python manage.py scan_arbius --blocks 1000
   ```

## Heroku Deployment

### Prerequisites
- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installed
- Git repository initialized

### Option 1: Automated Deployment
```bash
./deploy.sh
```
Just run this script and follow the prompts!

### Option 2: Manual Deployment

#### Step 1: Create Heroku App
```bash
heroku create your-app-name
```

#### Step 2: Add PostgreSQL Database
```bash
heroku addons:create heroku-postgresql:essential-0
```

#### Step 3: Set Environment Variables
```bash
heroku config:set SECRET_KEY="your-secret-key-here"
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS="your-app-name.herokuapp.com"
```

#### Step 4: Deploy
```bash
git branch -M main  # Ensure you're on main branch
git push heroku main
```

#### Step 5: Run Migrations
```bash
heroku run python manage.py migrate
```

#### Step 6: Initial Scan
```bash
heroku run "python manage.py scan_arbius --blocks 1000"
```

#### Step 7: Set Up Automatic Scanning

Add the **Heroku Scheduler** add-on for automatic image discovery:

```bash
heroku addons:create scheduler:standard
```

Then configure the scheduler:
```bash
heroku addons:open scheduler
```

Add this job to run **every 10 minutes** (minimum interval):
```bash
python manage.py scan_arbius --blocks 100 --quiet
```

⚠️ **Note**: Heroku Scheduler minimum interval is 10 minutes, not 1 minute.

This will automatically scan for new Arbius images every 10 minutes!

## Environment Variables

For production deployment, set these environment variables:

- `SECRET_KEY` - Django secret key (generate a new one for production)
- `DEBUG` - Set to `False` for production
- `ALLOWED_HOSTS` - Your domain name (e.g., `your-app.herokuapp.com`)
- `DATABASE_URL` - Automatically set by Heroku PostgreSQL

## Management Commands

### Scan for New Images
```bash
# Scan recent 100 blocks
python manage.py scan_arbius --blocks 100

# Quiet mode (for scheduled runs)
python manage.py scan_arbius --blocks 100 --quiet
```

### Recheck IPFS Accessibility
```bash
python manage.py recheck_ipfs
```

## How It Works

1. **Blockchain Scanning**: The app scans Arbitrum blockchain for `submitSolution` transactions
2. **CID Extraction**: Extracts IPFS Content Identifiers (CIDs) from transaction data
3. **IPFS Verification**: Checks if images are accessible on the IPFS network
4. **Database Storage**: Stores image metadata and accessibility status
5. **Gallery Display**: Shows images in a beautiful, responsive gallery interface

## Technical Details

- **Framework**: Django 5.2.2
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: Bootstrap 5.3 with custom CSS
- **Blockchain**: Arbitrum network via Arbiscan API
- **Storage**: IPFS decentralized storage
- **Deployment**: Heroku with automatic scaling
- **Scanning Frequency**: Every 10 minutes (Heroku Scheduler minimum)

## Contract Addresses

- **Engine Contract**: `0x9b51Ef044d3486A1fB0A2D55A6e0CeeAdd323E66`
- **Router Contract**: `0xecAba4E6a4bC1E3DE3e996a8B2c89e8B0626C9a1`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## About Arbius

Arbius is a decentralized AI network that enables anyone to generate AI content through blockchain transactions. Learn more at [arbius.org](https://arbius.org).

---

**Built with ❤️ for the decentralized AI community** 