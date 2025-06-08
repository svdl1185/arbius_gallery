/**
 * Web3 Authentication for Arbius Gallery
 * Handles wallet connection, authentication, and session management
 */

class Web3Auth {
    constructor() {
        this.isConnected = false;
        this.walletAddress = null;
        this.userProfile = null;
        this.init();
    }

    async init() {
        // Check if user is already connected
        this.checkExistingConnection();
        this.setupEventListeners();
        this.updateUI();
    }

    checkExistingConnection() {
        // Check if wallet address exists in session/localStorage
        const savedAddress = localStorage.getItem('connectedWallet');
        if (savedAddress) {
            this.walletAddress = savedAddress;
            this.isConnected = true;
        }
    }

    setupEventListeners() {
        // Connect wallet button
        const connectBtn = document.getElementById('connect-wallet-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.connectWallet());
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

    async connectWallet() {
        if (typeof window.ethereum === 'undefined') {
            this.showAlert('Please install MetaMask or another Ethereum wallet to continue.', 'warning');
            return;
        }

        try {
            // Request account access
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });

            if (accounts.length === 0) {
                throw new Error('No accounts found');
            }

            const walletAddress = accounts[0].toLowerCase();

            // Create message to sign for authentication
            const message = `Welcome to Arbius Gallery!\n\nConnect your wallet to interact with images.\n\nWallet: ${walletAddress}\nTimestamp: ${Date.now()}`;

            // Request signature
            const signature = await window.ethereum.request({
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

                this.showAlert('Wallet connected successfully!', 'success');
                this.updateUI();

                // Reload page to update all content
                setTimeout(() => window.location.reload(), 1000);
            } else {
                throw new Error(data.error || 'Failed to connect wallet');
            }

        } catch (error) {
            console.error('Error connecting wallet:', error);
            this.showAlert(`Failed to connect wallet: ${error.message}`, 'error');
        }
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

                localStorage.removeItem('connectedWallet');

                this.showAlert('Wallet disconnected', 'info');
                this.updateUI();

                // Reload page to update all content
                setTimeout(() => window.location.reload(), 1000);
            }

        } catch (error) {
            console.error('Error disconnecting wallet:', error);
        }
    }

    updateUI() {
        // Update connect/disconnect buttons
        const connectBtn = document.getElementById('connect-wallet-btn');
        const disconnectBtn = document.getElementById('disconnect-wallet-btn');
        const walletInfo = document.getElementById('wallet-info');

        if (this.isConnected && this.walletAddress) {
            if (connectBtn) connectBtn.style.display = 'none';
            if (disconnectBtn) disconnectBtn.style.display = 'inline-block';
            
            if (walletInfo) {
                walletInfo.innerHTML = `
                    <span class="wallet-address">
                        ${this.formatAddress(this.walletAddress)}
                    </span>
                `;
                walletInfo.style.display = 'inline-block';
            }

            // Show authenticated features
            this.showAuthenticatedFeatures();
        } else {
            if (connectBtn) connectBtn.style.display = 'inline-block';
            if (disconnectBtn) disconnectBtn.style.display = 'none';
            if (walletInfo) walletInfo.style.display = 'none';

            // Hide authenticated features
            this.hideAuthenticatedFeatures();
        }
    }

    showAuthenticatedFeatures() {
        const authElements = document.querySelectorAll('.auth-required');
        authElements.forEach(el => el.style.display = 'block');

        const unauthElements = document.querySelectorAll('.unauth-only');
        unauthElements.forEach(el => el.style.display = 'none');
    }

    hideAuthenticatedFeatures() {
        const authElements = document.querySelectorAll('.auth-required');
        authElements.forEach(el => el.style.display = 'none');

        const unauthElements = document.querySelectorAll('.unauth-only');
        unauthElements.forEach(el => el.style.display = 'block');
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
}

// Initialize Web3Auth when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.web3Auth = new Web3Auth();
});

// Make it available globally
window.Web3Auth = Web3Auth; 