# 🎨 Arbius Gallery

A beautiful Web3 social gallery for AI-generated images from the Arbius decentralized network on Arbitrum. This Django application features wallet authentication, social interactions, and comprehensive blockchain scanning.

## 🌟 Key Features

### 🖼️ **AI Image Gallery**
- **Automatic Blockchain Scanning**: Continuously monitors Arbitrum for new Arbius images
- **Smart Content Filtering**: Only displays high-quality images from whitelisted models
- **IPFS Integration**: Displays images stored permanently on IPFS
- **Advanced Search & Filtering**: Search by prompt, model, creator, or transaction
- **Multiple Sorting Options**: Sort by upvotes, comments, newest, or oldest

### 🔐 **Web3 Authentication**
- **MetaMask Integration**: Connect with popular Web3 wallets
- **Signature-based Authentication**: Secure wallet-based login system
- **Persistent Sessions**: Remembers wallet connections across browser sessions
- **Auto-profile Creation**: Automatic profile generation for wallet holders

### 👥 **Social Features**
- **Upvote System**: Like your favorite AI creations (wallet required)
- **Comment System**: Discuss images with the community (wallet required)
- **User Profiles**: Public profiles for all creators showing stats and images
- **Creator Statistics**: Track images created, upvotes received, and engagement
- **Public Profile Access**: View any creator's profile without connecting wallet

### 📊 **Analytics & Statistics**
- **Live Statistics Dashboard**: Real-time network analytics and charts
- **Image Generation Trends**: Daily and cumulative creation charts
- **Creator Leaderboards**: Top contributors and their statistics
- **Model Analytics**: Usage statistics for different AI models
- **Community Metrics**: Total upvotes, comments, and active users

### 🎯 **Special Features**
- **Telegram Bot Integration**: Special naming for Arbius Telegram Bot images
- **Upvote Status Indicators**: Visual feedback showing which images you've upvoted
- **Responsive Design**: Perfect experience on mobile, tablet, and desktop
- **Dark Theme**: Easy on the eyes with beautiful gradients
- **Real-time Updates**: Live data updates and statistics

## 🚀 Quick Deployment

### One-Click Heroku Deployment
1. **Clone and Deploy**:
   ```bash
   git clone https://github.com/svdl1185/arbius_gallery.git
   cd arbius_gallery
   ./deploy.sh
   ```

2. **Set up Continuous Scanning**:
   ```bash
   ./setup_github.sh
   ```

## 🛠️ Local Development Setup

1. **Environment Setup**:
   ```bash
   python -m venv arbius_env
   source arbius_env/bin/activate  # Windows: arbius_env\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Database Configuration**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser  # Optional: for admin access
   ```

3. **Start Development Server**:
   ```bash
   python manage.py runserver
   ```

4. **Initial Data Scan**:
   ```bash
   python manage.py scan_arbius --blocks 1000
   ```

## 🔧 Configuration

### Environment Variables

#### **Required for Production**
```bash
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=postgresql://username:password@host:port/database
```

#### **Blockchain Configuration**
```bash
ARBISCAN_API_KEY=your-arbiscan-api-key
ENGINE_CONTRACT_ADDRESS=0x...
ROUTER_CONTRACT_ADDRESS=0x...
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
IPFS_BASE_URL=https://gateway.pinata.cloud/ipfs/
```

#### **Social Features**
```bash
# These are handled automatically by the application
ENABLE_SOCIAL_FEATURES=True  # Default: True
REQUIRE_WALLET_FOR_VIEWING=False  # Public viewing enabled
```

## 🏗️ Architecture

### **Backend Structure**
```
arbius_gallery/
├── gallery/                      # Main Django application
│   ├── models.py                 # Database models (ArbiusImage, UserProfile, etc.)
│   ├── views.py                  # Web3 views, social features, gallery logic
│   ├── services.py               # Blockchain scanning and IPFS integration
│   ├── middleware.py             # Web3 authentication middleware
│   ├── admin.py                  # Django admin configuration
│   ├── urls.py                   # URL routing
│   ├── templates/gallery/        # HTML templates
│   │   ├── base.html            # Base layout with Web3 integration
│   │   ├── index.html           # Main gallery page
│   │   ├── image_detail.html    # Individual image view
│   │   ├── user_profile.html    # User profile pages
│   │   ├── search.html          # Search results
│   │   └── info.html           # Statistics dashboard
│   ├── static/gallery/          # Frontend assets
│   │   ├── css/                # Stylesheets
│   │   ├── js/                 # JavaScript (Web3, social features)
│   │   └── images/             # Static images
│   └── management/commands/     # Management commands
│       ├── scan_arbius.py      # Blockchain scanning
│       └── list_models.py      # Model analysis
├── .github/workflows/           # CI/CD and automated scanning
│   └── scheduled_scan.yml      # GitHub Actions for scanning
├── static/                     # Collected static files
├── deploy.sh                   # Heroku deployment script
├── setup_github.sh            # GitHub Actions setup
└── requirements.txt           # Python dependencies
```

### **Database Models**

#### **ArbiusImage**
```python
- transaction_hash: Unique blockchain transaction
- task_id: AI generation task identifier
- cid: IPFS content identifier
- model_id: AI model used for generation
- prompt: Text prompt used for generation
- task_submitter: Wallet address of image creator
- solution_provider: Wallet address of miner
- timestamp: Blockchain timestamp
- upvote_count: Calculated upvotes
- comment_count: Calculated comments
```

#### **UserProfile**
```python
- wallet_address: Ethereum wallet address (unique)
- display_name: User-chosen display name
- bio: User biography
- website: Personal website URL
- twitter_handle: Twitter handle
- total_images_created: Calculated statistic
- total_upvotes_received: Calculated statistic
```

#### **ImageUpvote & ImageComment**
```python
- Social interaction models linking wallets to images
- Prevents duplicate votes per wallet
- Tracks engagement timestamps
```

## 🔍 Management Commands

### **scan_arbius**
Primary blockchain scanning command:
```bash
python manage.py scan_arbius [options]

Options:
  --blocks N        Number of recent blocks to scan (default: 100)
  --quiet           Suppress output for automated runs
  --force           Force rescan of existing blocks
  --start-block N   Start scanning from specific block
  --end-block N     End scanning at specific block
```

### **identify_miners**
Automated miner identification system:
```bash
python manage.py identify_miners [options]

Options:
  --hours N         Number of hours back to scan for miner activity (default: 1)
  --quiet           Suppress output for automated runs
  --initial-scan    Perform initial 24-hour scan to populate miner database
  --mark-inactive   Mark miners as inactive if not seen for 7+ days (default: keep all miners active)

# Examples:
python manage.py identify_miners --hours 2             # Scan last 2 hours
python manage.py identify_miners --initial-scan        # Initial 24-hour scan
python manage.py identify_miners --quiet               # Scheduled run (no output)
python manage.py identify_miners --mark-inactive       # Also mark old miners as inactive
```

**🔒 Permanent Miner List**: By default, once a wallet is identified as a miner, it stays on the automine filter list permanently, even if it becomes inactive. This ensures consistent filtering of automated content.

### **list_models**
Analyze AI models in use:
```bash
python manage.py list_models
# Shows model statistics and usage patterns
```

## 🤖 Automated Miner Detection

### **Robust Miner Identification**
The system now automatically identifies miner wallets by monitoring blockchain activity:

- **Real-time Detection**: Scans for solution submissions and commitments to the engine contract
- **Dynamic Filtering**: Auto-updates the automine filter with newly discovered miners
- **Activity Tracking**: Monitors miner activity and marks inactive miners
- **Fallback Protection**: Maintains hardcoded list as backup if database is empty

### **How It Works**
1. **Blockchain Scanning**: Monitors engine contract for `submitSolution` transactions
2. **Miner Identification**: Records wallet addresses that submit solutions
3. **Activity Tracking**: Updates last-seen timestamps and solution counts
4. **Auto-filtering**: Dynamically excludes active miners from image pools
5. **Cleanup**: Automatically marks miners inactive after 7 days of no activity

### **Database Schema**
```python
class MinerAddress:
    wallet_address: str       # Unique miner wallet address
    first_seen: datetime      # When first identified as miner
    last_seen: datetime       # Last activity timestamp
    total_solutions: int      # Number of solutions submitted
    total_commitments: int    # Number of commitments submitted
    is_active: bool          # Whether currently active (last 7 days)
```

## 🔄 Automated Scanning

### **Heroku Scheduler Setup**
1. **Install Scheduler Add-on**:
   ```bash
   heroku addons:create scheduler:standard --app your-app-name
   heroku addons:open scheduler --app your-app-name
   ```

2. **Add Hourly Jobs**:
   ```bash
   # Image scanning (every 10 minutes)
   python manage.py scan_arbius --blocks 100 --quiet
   
   # Miner identification (every hour)
   python manage.py identify_miners --hours 1 --quiet
   ```

### **GitHub Actions (Recommended - 1-minute intervals)**
1. Push code to GitHub repository
2. Add repository secrets in GitHub Settings > Secrets:
   - `HEROKU_API_KEY`: Your Heroku API token
   - `HEROKU_APP_NAME`: Your Heroku application name
3. Automatic scanning runs every minute via GitHub Actions
4. Miner identification runs every hour automatically

### **Initial Setup**
After deployment, run these commands to populate the databases:
```bash
# Populate image database
heroku run python manage.py scan_arbius --blocks 1000 --app your-app-name

# Populate miner database  
heroku run python manage.py identify_miners --initial-scan --app your-app-name
```

## 🌐 Web3 Integration

### **Wallet Connection Flow**
1. User clicks "Connect Wallet" button
2. MetaMask prompts for connection
3. User signs authentication message
4. Session established with wallet address
5. Profile auto-created or retrieved
6. Social features become available

### **Social Interaction Flow**
1. **Upvoting**: Click heart icon → MetaMask signature → Database update
2. **Commenting**: Write comment → MetaMask signature → Comment stored
3. **Profile Viewing**: Public access to any creator's profile and statistics

### **Security Features**
- Signature-based authentication prevents spoofing
- Session management with secure tokens
- Public data access without wallet requirement
- Rate limiting on social actions

## 📊 API Endpoints

### **Public Endpoints (No Wallet Required)**
```
GET  /                          # Main gallery
GET  /search/                   # Search images
GET  /info/                     # Statistics dashboard
GET  /profile/<wallet_address>/ # User profiles
GET  /image/<id>/              # Image details
```

### **Web3 Endpoints (Wallet Required)**
```
POST /connect_wallet/           # Wallet authentication
POST /disconnect_wallet/        # Session termination
POST /image/<id>/upvote/       # Toggle upvote
POST /image/<id>/comment/      # Add comment
POST /update_profile/          # Update user profile
```

## 🎨 Frontend Features

### **Modern UI Components**
- Responsive CSS Grid layout
- Dark theme with gradient accents
- Smooth animations and transitions
- Mobile-optimized navigation
- Progressive loading for large galleries

### **JavaScript Features**
- Web3 wallet integration (MetaMask)
- Real-time upvote status updates
- Infinite scroll pagination
- Search and filter functionality
- Social interaction handlers

### **Accessibility**
- Semantic HTML structure
- Keyboard navigation support
- Screen reader compatibility
- High contrast color schemes

## 🚀 Production Deployment

### **Heroku Configuration**
```bash
# Required buildpacks
heroku buildpacks:add heroku/python

# Required add-ons
heroku addons:create heroku-postgresql:mini
heroku addons:create scheduler:standard

# Essential config vars
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=your-app.herokuapp.com
```

### **Performance Optimization**
- Database indexing on frequently queried fields
- IPFS gateway caching and fallbacks
- Efficient querysets with select_related/prefetch_related
- Static file compression and CDN-ready
- Pagination for large datasets

## 🐛 Troubleshooting

### **Common Issues**

#### **Wallet Connection Problems**
- Ensure MetaMask is installed and unlocked
- Check browser console for JavaScript errors
- Verify wallet is connected to correct network (Arbitrum)

#### **No Images Displaying**
- Run initial scan: `python manage.py scan_arbius --blocks 1000`
- Check database: `python manage.py shell` → `ArbiusImage.objects.count()`
- Verify IPFS gateways are accessible

#### **Automine Filter Not Working**
- Check miner database: `python manage.py shell` → `MinerAddress.objects.count()`
- Run initial miner scan: `python manage.py identify_miners --initial-scan`
- Verify miners are marked as active: `MinerAddress.objects.filter(is_active=True).count()`

#### **Social Features Not Working**
- Ensure wallet is connected
- Check for JavaScript errors in browser console
- Verify signatures are being generated correctly

#### **Deployment Issues**
- Confirm all environment variables are set
- Run migrations: `heroku run python manage.py migrate`
- Check logs: `heroku logs --tail`

#### **Scheduler Not Running**
- Verify scheduler add-on is installed: `heroku addons --app your-app-name`
- Check scheduled jobs: `heroku addons:open scheduler --app your-app-name`
- Review job logs in Heroku dashboard
- Test manually: `heroku run python manage.py identify_miners --quiet --app your-app-name`

## 🔍 Monitoring & Analytics

### **Built-in Statistics**
- Real-time image count and growth
- Creator activity and rankings  
- Model usage analytics
- Social engagement metrics
- IPFS accessibility monitoring
- **Miner Activity Tracking**: Monitor active/inactive miners and their solution counts

### **Miner Database Monitoring**
```bash
# Check miner statistics
python manage.py shell -c "
from gallery.models import MinerAddress;
total = MinerAddress.objects.count();
active = MinerAddress.objects.filter(is_active=True).count();
print(f'Total miners: {total}, Active: {active}, Inactive: {total-active}')
"

# View top miners by activity
python manage.py shell -c "
from gallery.models import MinerAddress;
[print(f'{m.wallet_address[:10]}... - {m.total_solutions} solutions') 
 for m in MinerAddress.objects.filter(is_active=True)[:10]]
"
```

### **Admin Interface**
Access Django admin at `/admin/` to:
- Monitor database health
- Review flagged content
- **Manage miner addresses and activity**
- **View automine filter effectiveness**
- Manage user profiles
- Analyze system performance

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test thoroughly
4. Ensure all tests pass: `python manage.py test`
5. Submit pull request with detailed description

### **Contribution Guidelines**
- Follow Django best practices
- Maintain Web3 security standards
- Add tests for new features
- Update documentation
- Respect user privacy and data protection

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 About & Acknowledgments

### **About This Project**

Arbius Gallery represents the intersection of decentralized AI and social Web3 applications. Built as a comprehensive showcase for the Arbius network, it demonstrates how blockchain technology can create transparent, community-driven platforms for AI-generated content.

The gallery serves multiple purposes:
- **Community Hub**: A central place for Arbius users to discover and interact with AI art
- **Technical Demo**: Showcasing integration between Django, Web3, and decentralized storage
- **Social Platform**: Enabling creators to build profiles and engage with their audience
- **Analytics Tool**: Providing insights into network usage and growth patterns

### **Technology Stack**
- **Backend**: Django 5.2.2 with PostgreSQL
- **Blockchain**: Arbitrum network integration
- **Storage**: IPFS for decentralized image storage
- **Frontend**: Vanilla JavaScript with Web3 integration
- **Authentication**: MetaMask wallet signatures
- **Deployment**: Heroku with GitHub Actions CI/CD

### **Acknowledgments**

- **Arbius Team**: For creating the revolutionary decentralized AI network that makes this gallery possible
- **Arbitrum**: For providing fast, low-cost blockchain infrastructure that enables smooth user experiences
- **MetaMask**: For creating the wallet infrastructure that powers Web3 authentication
- **IPFS Community**: For building the decentralized storage network that preserves AI art permanently
- **Django Community**: For the robust web framework that powers the backend
- **Open Source Contributors**: For the countless libraries and tools that make this project possible

### **The Vision**

This gallery embodies the vision of a decentralized creative economy where:
- Artists retain full ownership of their work
- Community members can engage and support creators directly
- Content is stored permanently and cannot be censored
- Innovation happens through open, transparent protocols
- Value flows directly to creators and contributors

---

**🎉 Explore the future of AI art at [Arbius Gallery](https://arbius-6cdb53a42247.herokuapp.com)**

*Built with ❤️ for the decentralized web*
