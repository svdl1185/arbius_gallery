/**
 * Social Features for Arbius Gallery
 * Handles upvoting, commenting, and user interactions
 */

class SocialFeatures {
    constructor() {
        this.init();
    }

    init() {
        this.setupUpvoteButtons();
        this.setupCommentForms();
        this.setupProfileForms();
    }

    setupUpvoteButtons() {
        // Handle traditional upvote buttons (on detail pages)
        const upvoteButtons = document.querySelectorAll('.upvote-btn:not(.clickable-upvote)');
        upvoteButtons.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleUpvote(e));
        });

        // Handle clickable upvote buttons on image tiles
        const clickableUpvoteButtons = document.querySelectorAll('.clickable-upvote');
        clickableUpvoteButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();  // Prevent navigation to image detail
                this.handleUpvote(e);
            });
        });
    }

    setupCommentForms() {
        const commentForms = document.querySelectorAll('.comment-form');
        commentForms.forEach(form => {
            form.addEventListener('submit', (e) => this.handleComment(e));
        });
    }

    setupProfileForms() {
        const profileForm = document.getElementById('profile-form');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => this.handleProfileUpdate(e));
        }
    }

    async handleUpvote(event) {
        event.preventDefault();
        
        if (!window.web3Auth || !window.web3Auth.isAuthenticated()) {
            this.showAlert('Please connect your wallet to upvote', 'warning');
            return;
        }

        const button = event.currentTarget;
        const imageId = button.dataset.imageId;
        
        if (!imageId) {
            console.error('No image ID found');
            return;
        }

        // Disable button during request
        button.disabled = true;
        const originalContent = button.innerHTML;
        const isClickableTile = button.classList.contains('clickable-upvote');
        
        // Show loading state
        if (isClickableTile) {
            const heartIcon = button.querySelector('i');
            const countSpan = button.querySelector('.upvote-count');
            heartIcon.className = 'fas fa-spinner fa-spin text-danger';
        } else {
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }

        try {
            const response = await fetch(`/gallery/api/image/${imageId}/upvote/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                }
            });

            const data = await response.json();

            if (data.success) {
                // Update button state and count
                const countElement = button.querySelector('.upvote-count') || 
                                   button.parentNode.querySelector('.upvote-count') ||
                                   document.querySelector(`[data-image-id="${imageId}"] .upvote-count`);
                
                if (isClickableTile) {
                    const heartIcon = button.querySelector('i');
                    if (data.upvoted) {
                        button.classList.add('upvoted');
                        heartIcon.className = 'fas fa-heart';
                    } else {
                        button.classList.remove('upvoted');
                        heartIcon.className = 'fas fa-heart text-danger';
                    }
                } else {
                    // Detail page button
                    if (data.upvoted) {
                        button.classList.add('upvoted');
                        button.innerHTML = '<i class="fas fa-heart"></i> Upvoted';
                    } else {
                        button.classList.remove('upvoted');
                        button.innerHTML = '<i class="far fa-heart"></i> Upvote';
                    }
                }

                // Update count
                if (countElement) {
                    countElement.textContent = data.upvote_count;
                }

                // Show animation
                this.animateUpvote(button);

            } else {
                throw new Error(data.error || 'Failed to upvote');
            }

        } catch (error) {
            console.error('Error upvoting:', error);
            this.showAlert(`Failed to upvote: ${error.message}`, 'error');
            button.innerHTML = originalContent;
        } finally {
            button.disabled = false;
        }
    }

    async handleComment(event) {
        event.preventDefault();
        
        if (!window.web3Auth || !window.web3Auth.isAuthenticated()) {
            this.showAlert('Please connect your wallet to comment', 'warning');
            return;
        }

        const form = event.target;
        const imageId = form.dataset.imageId;
        const textArea = form.querySelector('textarea[name="content"]');
        const content = textArea.value.trim();

        if (!content) {
            this.showAlert('Please enter a comment', 'warning');
            return;
        }

        if (content.length > 1000) {
            this.showAlert('Comment must be less than 1000 characters', 'warning');
            return;
        }

        // Disable form during request
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Posting...';

        try {
            const response = await fetch(`/gallery/api/image/${imageId}/comment/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({ content: content })
            });

            const data = await response.json();

            if (data.success) {
                // Clear form
                textArea.value = '';

                // Add comment to list
                this.addCommentToList(data.comment, imageId);

                // Update comment count
                const countElement = document.querySelector('.comment-count');
                if (countElement) {
                    countElement.textContent = data.comment_count;
                }

                this.showAlert('Comment posted successfully!', 'success');

            } else {
                throw new Error(data.error || 'Failed to post comment');
            }

        } catch (error) {
            console.error('Error posting comment:', error);
            this.showAlert(`Failed to post comment: ${error.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    async handleProfileUpdate(event) {
        event.preventDefault();
        
        if (!window.web3Auth || !window.web3Auth.isAuthenticated()) {
            this.showAlert('Please connect your wallet to update profile', 'warning');
            return;
        }

        const form = event.target;
        const formData = new FormData(form);
        
        const profileData = {
            display_name: formData.get('display_name'),
            bio: formData.get('bio'),
            website: formData.get('website'),
            twitter_handle: formData.get('twitter_handle'),
        };

        // Disable form during request
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Updating...';

        try {
            const response = await fetch('/gallery/api/profile/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify(profileData)
            });

            const data = await response.json();

            if (data.success) {
                this.showAlert('Profile updated successfully!', 'success');
                
                // Update displayed profile info if present
                this.updateProfileDisplay(data.profile);
                
            } else {
                throw new Error(data.error || 'Failed to update profile');
            }

        } catch (error) {
            console.error('Error updating profile:', error);
            this.showAlert(`Failed to update profile: ${error.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    addCommentToList(comment, imageId) {
        const commentsList = document.getElementById(`comments-list-${imageId}`) || 
                            document.querySelector('.comments-list');
        
        if (!commentsList) return;

        const commentElement = document.createElement('div');
        commentElement.className = 'comment mb-3 p-3 border rounded';
        commentElement.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${this.formatAddress(comment.wallet_address)}</strong>
                    <small class="text-muted ms-2">${this.formatDate(comment.created_at)}</small>
                </div>
            </div>
            <p class="mt-2 mb-0">${this.escapeHtml(comment.content)}</p>
        `;

        // Add to top of comments list
        commentsList.insertBefore(commentElement, commentsList.firstChild);

        // Animate in
        commentElement.style.opacity = '0';
        commentElement.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            commentElement.style.transition = 'all 0.3s ease';
            commentElement.style.opacity = '1';
            commentElement.style.transform = 'translateY(0)';
        }, 10);
    }

    updateProfileDisplay(profile) {
        // Update display name
        const displayNameEl = document.querySelector('.profile-display-name');
        if (displayNameEl) {
            displayNameEl.textContent = profile.display_name || 'Anonymous';
        }

        // Update bio
        const bioEl = document.querySelector('.profile-bio');
        if (bioEl) {
            bioEl.textContent = profile.bio || '';
        }

        // Update website
        const websiteEl = document.querySelector('.profile-website');
        if (websiteEl && profile.website) {
            websiteEl.href = profile.website;
            websiteEl.style.display = 'inline';
        } else if (websiteEl) {
            websiteEl.style.display = 'none';
        }

        // Update Twitter
        const twitterEl = document.querySelector('.profile-twitter');
        if (twitterEl && profile.twitter_handle) {
            twitterEl.href = `https://twitter.com/${profile.twitter_handle}`;
            twitterEl.style.display = 'inline';
        } else if (twitterEl) {
            twitterEl.style.display = 'none';
        }
    }

    animateUpvote(button) {
        // Create heart animation
        const heart = document.createElement('div');
        heart.innerHTML = '❤️';
        heart.style.position = 'absolute';
        heart.style.fontSize = '20px';
        heart.style.pointerEvents = 'none';
        heart.style.zIndex = '1000';
        
        const rect = button.getBoundingClientRect();
        heart.style.left = rect.left + rect.width / 2 + 'px';
        heart.style.top = rect.top + 'px';

        document.body.appendChild(heart);

        // Animate
        let opacity = 1;
        let y = 0;
        const animate = () => {
            y -= 2;
            opacity -= 0.02;
            heart.style.transform = `translateY(${y}px)`;
            heart.style.opacity = opacity;

            if (opacity > 0) {
                requestAnimationFrame(animate);
            } else {
                document.body.removeChild(heart);
            }
        };
        requestAnimationFrame(animate);
    }

    formatAddress(address) {
        if (!address) return 'Anonymous';
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
}

// Initialize Social Features when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.socialFeatures = new SocialFeatures();
});

// Make it available globally
window.SocialFeatures = SocialFeatures; 