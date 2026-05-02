/**
 * AI Features JavaScript
 * Handles AJAX requests for AI-powered features:
 * - Generate Tags & Category
 * - Generate SEO Metadata
 */

// CSRF Token helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Show loading overlay
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'block';
    }
}

// Hide loading overlay
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const form = document.getElementById('postForm');
    form.parentNode.insertBefore(alertDiv, form);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function getContentValue() {
    if (window.simplemde) {
        return window.simplemde.value();
    }
    const contentField = document.getElementById('content');
    return contentField ? contentField.value : '';
}

// Generate Tags & Category
function generateTagsAndCategory() {
    const content = getContentValue().trim();
    const title = document.getElementById('title').value.trim();
    
    if (!content) {
        showAlert('Please enter post content first.', 'warning');
        return;
    }
    
    // Combine title and content for better analysis
    const fullContent = title + '\n\n' + content;
    
    showLoading();
    
    fetch('/ai-tags/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            content: fullContent
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            console.log('Tags Data received:', data);
            let filledFields = [];
            
            // Update category field
            if (data.category) {
                const categoryField = document.getElementById('category');
                if (categoryField) {
                    categoryField.value = data.category;
                    filledFields.push('Category');
                    console.log('✅ Filled Category:', data.category);
                } else {
                    console.error('❌ Category field not found');
                }
            }
            
            // Update tags field
            if (data.tags && Array.isArray(data.tags)) {
                const tagsField = document.getElementById('tags');
                if (tagsField) {
                    tagsField.value = data.tags.join(', ');
                    filledFields.push('Tags (' + data.tags.length + ')');
                    console.log('✅ Filled Tags:', data.tags);
                } else {
                    console.error('❌ Tags field not found');
                }
            }
            
            // Show success message with details
            if (filledFields.length > 0) {
                showAlert(`✅ Successfully generated! Filled: ${filledFields.join(', ')}`, 'success');
            } else {
                showAlert('⚠️ Data received but fields not found. Check browser console (F12).', 'warning');
            }
        } else {
            showAlert(`❌ Error: ${data.error || 'Failed to generate tags and category'}`, 'danger');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showAlert('❌ An error occurred. Please check your OpenAI API key and try again.', 'danger');
    });
}

// Generate SEO Metadata
function generateSEOMetadata() {
    const title = document.getElementById('title').value.trim();
    const content = getContentValue().trim();
    
    if (!title || !content) {
        showAlert('Please enter both title and content first.', 'warning');
        return;
    }
    
    showLoading();
    
    fetch('/ai-seo/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            title: title,
            content: content
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        
        if (data.success) {
            console.log('SEO Data received:', data);
            let filledFields = [];
            
            // Update SEO title
            if (data.seo_title) {
                const seoTitleField = document.getElementById('seo_title');
                if (seoTitleField) {
                    seoTitleField.value = data.seo_title;
                    filledFields.push('SEO Title');
                    console.log('✅ Filled SEO Title:', data.seo_title);
                } else {
                    console.error('❌ SEO Title field not found');
                }
            }
            
            // Update meta description
            if (data.meta_description) {
                const metaDescField = document.getElementById('meta_description');
                if (metaDescField) {
                    metaDescField.value = data.meta_description;
                    const countField = document.getElementById('meta_desc_count');
                    if (countField) {
                        countField.textContent = data.meta_description.length;
                    }
                    filledFields.push('Meta Description');
                    console.log('✅ Filled Meta Description:', data.meta_description);
                } else {
                    console.error('❌ Meta Description field not found');
                }
            }
            
            // Update slug suggestion
            if (data.slug_suggestion) {
                const slugField = document.getElementById('slug');
                if (slugField) {
                    slugField.value = data.slug_suggestion;
                    filledFields.push('Slug');
                    console.log('✅ Filled Slug:', data.slug_suggestion);
                } else {
                    console.error('❌ Slug field not found');
                }
            }
            
            // Display SEO keywords
            if (data.seo_keywords && Array.isArray(data.seo_keywords) && data.seo_keywords.length > 0) {
                const keywordsDisplay = document.getElementById('seoKeywordsDisplay');
                const keywordsPreview = document.getElementById('seoKeywordsPreview');
                const keywordsHidden = document.getElementById('seo_keywords');
                
                if (keywordsDisplay && keywordsPreview) {
                    keywordsDisplay.innerHTML = '';
                    data.seo_keywords.forEach(keyword => {
                        const badge = document.createElement('span');
                        badge.className = 'badge bg-secondary me-1 mb-1';
                        badge.textContent = keyword;
                        keywordsDisplay.appendChild(badge);
                    });
                    
                    keywordsPreview.style.display = 'block';
                    filledFields.push('Keywords (' + data.seo_keywords.length + ')');
                    console.log('✅ Displayed Keywords:', data.seo_keywords);
                } else {
                    console.error('❌ Keywords display elements not found');
                }
                
                if (keywordsHidden) {
                    keywordsHidden.value = JSON.stringify(data.seo_keywords);
                    console.log('✅ Stored keywords in hidden field');
                }
            }
            
            // Show success message with details
            if (filledFields.length > 0) {
                showAlert(`✅ Successfully generated SEO metadata! Filled: ${filledFields.join(', ')}`, 'success');
            } else {
                showAlert('⚠️ Data received but fields not found. Check browser console (F12).', 'warning');
            }
        } else {
            showAlert(`❌ Error: ${data.error || 'Failed to generate SEO metadata'}`, 'danger');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showAlert('❌ An error occurred. Please check your OpenAI API key and try again.', 'danger');
    });
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    const generateTagsBtn = document.getElementById('generateTagsBtn');
    const generateSeoBtn = document.getElementById('generateSeoBtn');
    
    if (generateTagsBtn) {
        generateTagsBtn.addEventListener('click', generateTagsAndCategory);
    }
    
    if (generateSeoBtn) {
        generateSeoBtn.addEventListener('click', generateSEOMetadata);
    }
});

