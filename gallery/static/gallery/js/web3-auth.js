/**
 * Web3 Authentication for Arbius Gallery
 * Handles wallet connection, authentication, and session management
 */

class Web3Auth {
    constructor() {
        this.isConnected = false;
        this.walletAddress = null;
        this.userProfile = null;
        this.selectedProvider = null;
        this.availableProviders = {};
        this.init();
    }

    async init() {
        console.log('Web3Auth: Initializing...');
        await this.detectWalletProviders();
        await this.setupEventListeners();
        
        // Check server-side authentication state from page elements
        this.syncWithServerState();
        console.log('Web3Auth: Server state synced, isConnected:', this.isConnected, 'walletAddress:', this.walletAddress);
        
        // If not authenticated on server, check localStorage
        if (!this.isConnected) {
            this.checkExistingConnection();
            console.log('Web3Auth: LocalStorage checked, isConnected:', this.isConnected, 'walletAddress:', this.walletAddress);
        }
        
        // Initial UI update
        this.updateUI();
        console.log('Web3Auth: Initialization complete');
    }

    detectWalletProviders() {
        this.availableProviders = {};

        // MetaMask
        if (window.ethereum?.isMetaMask) {
            this.availableProviders.metamask = {
                name: 'MetaMask',
                provider: window.ethereum,
                icon: '🦊'
            };
        }

        // Rabby
        if (window.ethereum?.isRabby) {
            this.availableProviders.rabby = {
                name: 'Rabby',
                provider: window.ethereum,
                icon: '🐰'
            };
        }

        // Other providers
        if (window.ethereum && !window.ethereum.isMetaMask && !window.ethereum.isRabby) {
            this.availableProviders.ethereum = {
                name: 'Ethereum Wallet',
                provider: window.ethereum,
                icon: '⚡'
            };
        }

        // WalletConnect or other providers
        if (window.ethereum?.providers) {
            window.ethereum.providers.forEach((provider, index) => {
                if (provider.isMetaMask && !this.availableProviders.metamask) {
                    this.availableProviders.metamask = {
                        name: 'MetaMask',
                        provider: provider,
                        icon: '🦊'
                    };
                } else if (provider.isRabby && !this.availableProviders.rabby) {
                    this.availableProviders.rabby = {
                        name: 'Rabby',
                        provider: provider,
                        icon: '🐰'
                    };
                } else if (!provider.isMetaMask && !provider.isRabby) {
                    this.availableProviders[`provider_${index}`] = {
                        name: provider.constructor.name || `Wallet ${index + 1}`,
                        provider: provider,
                        icon: '💳'
                    };
                }
            });
        }
    }

    checkExistingConnection() {
        // Check if wallet address exists in session/localStorage
        const savedAddress = localStorage.getItem('connectedWallet');
        const savedProvider = localStorage.getItem('selectedWalletProvider');
        
        if (savedAddress && savedProvider && this.availableProviders[savedProvider]) {
            this.walletAddress = savedAddress;
            this.selectedProvider = this.availableProviders[savedProvider].provider;
            this.isConnected = true;
        }
    }

    setupEventListeners() {
        // Connect wallet button
        const connectBtn = document.getElementById('connect-wallet-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.showWalletSelection());
        }

        // Disconnect wallet button
        const disconnectBtn = document.getElementById('disconnect-wallet-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => this.disconnectWallet());
        }

        // Listen for account changes
        if (window.ethereum) {
            window.ethereum.on('accountsChanged', (accounts) => {
                if (accounts.length === 0) {
                    this.disconnectWallet();
                } else if (accounts[0] !== this.walletAddress) {
                    this.connectWallet();
                }
            });

            window.ethereum.on('chainChanged', () => {
                window.location.reload();
            });
        }
    }

    showWalletSelection() {
        const providers = Object.keys(this.availableProviders);
        
        if (providers.length === 0) {
            this.showAlert('No Ethereum wallets detected. Please install MetaMask, Rabby, or another Ethereum wallet.', 'warning');
            return;
        }

        if (providers.length === 1) {
            // Only one wallet available, connect directly
            this.connectWithProvider(providers[0]);
            return;
        }

        // Multiple wallets available, show selection modal
        this.createWalletSelectionModal();
    }

    createWalletSelectionModal() {
        // Remove existing modal if any
        const existingModal = document.getElementById('wallet-selection-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal HTML
        const modalHTML = `
            <div class="modal fade" id="wallet-selection-modal" tabindex="-1" style="z-index: 10000;">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content" style="background: var(--card-bg); border: 1px solid var(--card-border);">
                        <div class="modal-header" style="border-bottom: 1px solid var(--card-border);">
                            <h5 class="modal-title" style="color: var(--text-primary);">Choose Your Wallet</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Select which wallet you'd like to connect:</p>
                            <div class="wallet-options">
                                ${Object.entries(this.availableProviders).map(([key, wallet]) => `
                                    <button class="wallet-option-btn" data-provider="${key}">
                                        <span class="wallet-icon">${wallet.icon}</span>
                                        <span class="wallet-name">${wallet.name}</span>
                                    </button>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal styles
        const modalStyles = `
            <style>
                .wallet-option-btn {
                    width: 100%;
                    padding: 1rem;
                    margin-bottom: 0.5rem;
                    background: var(--card-bg);
                    border: 1px solid var(--card-border);
                    border-radius: 8px;
                    color: var(--text-primary);
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                    transition: all 0.3s ease;
                    cursor: pointer;
                }
                .wallet-option-btn:hover {
                    background: var(--primary-gradient);
                    color: white;
                    transform: translateY(-2px);
                }
                .wallet-icon {
                    font-size: 1.5rem;
                }
                .wallet-name {
                    font-weight: 500;
                }
            </style>
        `;

        // Add to page
        document.head.insertAdjacentHTML('beforeend', modalStyles);
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Add click event listeners
        const modal = document.getElementById('wallet-selection-modal');
        const walletOptions = modal.querySelectorAll('.wallet-option-btn');
        
        walletOptions.forEach(btn => {
            btn.addEventListener('click', () => {
                const provider = btn.getAttribute('data-provider');
                bootstrap.Modal.getInstance(modal).hide();
                this.connectWithProvider(provider);
            });
        });

        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Clean up when modal is hidden
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    async connectWithProvider(providerKey) {
        const walletInfo = this.availableProviders[providerKey];
        if (!walletInfo) {
            this.showAlert('Selected wallet not available', 'error');
            return;
        }

        this.selectedProvider = walletInfo.provider;

        try {
            // Request account access
            const accounts = await this.selectedProvider.request({
                method: 'eth_requestAccounts'
            });

            if (accounts.length === 0) {
                throw new Error('No accounts found');
            }

            const walletAddress = accounts[0].toLowerCase();

            // Create message to sign for authentication
            const message = `Welcome to Arbius Gallery!\n\nConnect your wallet to interact with images.\n\nWallet: ${walletAddress}\nTimestamp: ${Date.now()}`;

            // Request signature
            const signature = await this.selectedProvider.request({
                method: 'personal_sign',
                params: [message, walletAddress],
            });

            // Send to backend
            const response = await fetch('/gallery/api/connect-wallet/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    wallet_address: walletAddress,
                    signature: signature,
                    message: message
                })
            });

            const data = await response.json();

            if (data.success) {
                this.walletAddress = walletAddress;
                this.userProfile = data.profile;
                this.isConnected = true;

                // Save to localStorage
                localStorage.setItem('connectedWallet', walletAddress);
                localStorage.setItem('selectedWalletProvider', providerKey);

                this.showAlert(`Connected with ${walletInfo.name}!`, 'success');
                this.updateUI();

                // Don't reload page, let JavaScript handle the state update
                // setTimeout(() => window.location.reload(), 1000);
            } else {
                throw new Error(data.error || 'Failed to connect wallet');
            }

        } catch (error) {
            console.error('Error connecting wallet:', error);
            this.showAlert(`Failed to connect wallet: ${error.message}`, 'error');
        }
    }

    async connectWallet() {
        // This method is kept for backward compatibility
        this.showWalletSelection();
    }

    async disconnectWallet() {
        try {
            const response = await fetch('/gallery/api/disconnect-wallet/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                }
            });

            if (response.ok) {
                this.walletAddress = null;
                this.userProfile = null;
                this.isConnected = false;
                this.selectedProvider = null;

                localStorage.removeItem('connectedWallet');
                localStorage.removeItem('selectedWalletProvider');

                this.showAlert('Wallet disconnected', 'info');
                this.updateUI();

                // Don't reload page, let JavaScript handle the state update
                // setTimeout(() => window.location.reload(), 1000);
            }

        } catch (error) {
            console.error('Error disconnecting wallet:', error);
        }
    }

    updateUI() {
        // Update connect/disconnect buttons
        const connectBtn = document.getElementById('connect-wallet-btn');
        const disconnectBtn = document.getElementById('disconnect-wallet-btn');
        const profileLink = document.getElementById('profile-link') || document.querySelector('[href*="/gallery/profile/"]');

        if (this.isConnected && this.walletAddress) {
            // Show connected state
            if (connectBtn) {
                connectBtn.style.display = 'none';
                if (connectBtn.parentElement) connectBtn.parentElement.style.display = 'none';
            }
            if (disconnectBtn) {
                disconnectBtn.style.display = 'inline-block';
                if (disconnectBtn.parentElement) disconnectBtn.parentElement.style.display = 'block';
            }
            if (profileLink) {
                if (!profileLink.href.includes(this.walletAddress)) {
                    profileLink.href = `/gallery/profile/${this.walletAddress}/`;
                }
                profileLink.style.display = 'inline-block';
                if (profileLink.parentElement) profileLink.parentElement.style.display = 'block';
            }

            // Show authenticated features
            this.showAuthenticatedFeatures();
        } else {
            // Show disconnected state
            if (connectBtn) {
                connectBtn.style.display = 'inline-block';
                if (connectBtn.parentElement) connectBtn.parentElement.style.display = 'block';
            }
            if (disconnectBtn) {
                disconnectBtn.style.display = 'none';
                if (disconnectBtn.parentElement) disconnectBtn.parentElement.style.display = 'none';
            }
            if (profileLink) {
                profileLink.style.display = 'none';
                if (profileLink.parentElement) profileLink.parentElement.style.display = 'none';
            }

            // Hide authenticated features
            this.hideAuthenticatedFeatures();
        }
    }

    showAuthenticatedFeatures() {
        // Add authenticated class to body for CSS targeting
        document.body.classList.add('authenticated');
        
        const authElements = document.querySelectorAll('.auth-required');
        authElements.forEach(el => {
            el.style.display = 'block';
            // For form elements, also remove disabled state
            if (el.tagName === 'BUTTON' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.disabled = false;
                // Also remove any "Connect wallet" titles
                if (el.title && el.title.includes('Connect wallet')) {
                    el.removeAttribute('title');
                }
            }
        });

        const unauthElements = document.querySelectorAll('.unauth-only');
        unauthElements.forEach(el => el.style.display = 'none');
        
        console.log('Authentication state: AUTHENTICATED - Elements updated');
    }

    hideAuthenticatedFeatures() {
        // Remove authenticated class from body
        document.body.classList.remove('authenticated');
        
        const authElements = document.querySelectorAll('.auth-required');
        authElements.forEach(el => {
            el.style.display = 'none';
            // For form elements, also add disabled state
            if (el.tagName === 'BUTTON' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.disabled = true;
                // Add helpful title for buttons
                if (el.tagName === 'BUTTON' && el.dataset.imageId) {
                    el.title = 'Connect wallet to upvote';
                }
            }
        });

        const unauthElements = document.querySelectorAll('.unauth-only');
        unauthElements.forEach(el => el.style.display = 'block');
        
        console.log('Authentication state: NOT AUTHENTICATED - Elements updated');
    }

    formatAddress(address) {
        if (!address) return '';
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    showAlert(message, type = 'info') {
        // Create alert element
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.style.position = 'fixed';
        alert.style.top = '20px';
        alert.style.right = '20px';
        alert.style.zIndex = '9999';
        alert.style.minWidth = '300px';
        
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alert);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }

    // Public methods for other scripts to use
    isAuthenticated() {
        return this.isConnected && this.walletAddress;
    }

    getWalletAddress() {
        return this.walletAddress;
    }

    getUserProfile() {
        return this.userProfile;
    }

    syncWithServerState() {
        // Use Django authentication state if available
        if (window.DJANGO_AUTH_STATE) {
            if (window.DJANGO_AUTH_STATE.isAuthenticated && window.DJANGO_AUTH_STATE.walletAddress) {
                this.isConnected = true;
                this.walletAddress = window.DJANGO_AUTH_STATE.walletAddress;
                this.userProfile = window.DJANGO_AUTH_STATE.userProfile;
                
                // Save to localStorage for consistency
                localStorage.setItem('connectedWallet', this.walletAddress);
                return;
            }
        }
        
        // Fallback: check if server rendered authentication state
        const disconnectBtn = document.getElementById('disconnect-wallet-btn');
        const profileLink = document.querySelector('[href*="/gallery/profile/"]');
        
        // If disconnect button is visible, we're connected on server side
        if (disconnectBtn && disconnectBtn.offsetParent !== null) {
            this.isConnected = true;
            
            // Extract wallet address from profile link if available
            if (profileLink) {
                const profileUrl = profileLink.getAttribute('href');
                const addressMatch = profileUrl.match(/\/gallery\/profile\/([^\/]+)\//);
                if (addressMatch) {
                    this.walletAddress = addressMatch[1];
                }
            }
            
            // Save to localStorage for consistency
            if (this.walletAddress) {
                localStorage.setItem('connectedWallet', this.walletAddress);
            }
        }
    }
}

// Initialize Web3Auth when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.web3Auth = new Web3Auth();
});

// Make it available globally
window.Web3Auth = Web3Auth; 