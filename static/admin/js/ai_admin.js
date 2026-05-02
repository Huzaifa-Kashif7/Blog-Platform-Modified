/**
 * AI Features for Django Admin
 * Works with Django's jQuery
 */
(function($) {
    'use strict';
    
    // Wait for DOM and ensure jQuery is ready
    $(document).ready(function() {
        console.log('AI Admin JS loaded');
        
        // Get CSRF token
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
        
        function getCsrfToken() {
            const csrftoken = getCookie('csrftoken');
            if (!csrftoken) {
                // Try Django's method
                const cookieName = window.django ? 'csrftoken' : 'csrftoken';
                return getCookie(cookieName) || '';
            }
            return csrftoken;
        }
        
        const csrftoken = getCsrfToken();
        console.log('CSRF token found:', !!csrftoken);
        
        function getStatusDiv() {
            return document.getElementById('ai-status');
        }
        
        function showStatus(message, type = 'info') {
            const statusDiv = getStatusDiv();
            if (statusDiv) {
                const colors = {
                    'info': '#0066cc',
                    'success': '#28a745',
                    'error': '#dc3545'
                };
                statusDiv.style.color = colors[type] || colors.info;
                statusDiv.textContent = message;
                statusDiv.style.display = 'block';
                setTimeout(function() {
                    if (statusDiv.textContent === message) {
                        statusDiv.textContent = '';
                    }
                }, 5000);
            } else {
                console.log('Status message:', message);
            }
        }
        
        // Generate Tags & Category
        $(document).on('click', '.btn-ai-tags', function(e) {
            e.preventDefault();
            console.log('Generate Tags clicked');
            
            const contentField = document.getElementById('id_content');
            const titleField = document.getElementById('id_title');
            
            if (!contentField || !contentField.value.trim()) {
                showStatus('Please enter content first!', 'error');
                return false;
            }
            
            const content = (titleField && titleField.value ? titleField.value + '\n\n' : '') + contentField.value;
            
            showStatus('Generating tags and category...', 'info');
            
            $.ajax({
                url: '/admin/blog/post/ai-tags/',
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
                data: JSON.stringify({
                    content: content
                }),
                success: function(data) {
                    console.log('Tags response:', data);
                    if (data.success) {
                        // Fill category
                        const categoryField = document.getElementById('id_category');
                        if (categoryField && data.category) {
                            categoryField.value = data.category;
                            console.log('Category filled:', data.category);
                        }
                        
                        // Fill tags (as JSON array string)
                        const tagsField = document.getElementById('id_tags');
                        if (tagsField && data.tags && Array.isArray(data.tags)) {
                            tagsField.value = JSON.stringify(data.tags);
                            console.log('Tags filled:', data.tags);
                        }
                        
                        showStatus('✅ Tags and category generated successfully!', 'success');
                    } else {
                        showStatus('❌ Error: ' + (data.error || 'Failed to generate'), 'error');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX error:', xhr, status, error);
                    let errorMsg = 'Network error';
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        errorMsg = xhr.responseJSON.error;
                    } else if (xhr.responseText) {
                        try {
                            const err = JSON.parse(xhr.responseText);
                            errorMsg = err.error || errorMsg;
                        } catch(e) {
                            errorMsg = xhr.status + ': ' + error;
                        }
                    }
                    showStatus('❌ Error: ' + errorMsg, 'error');
                }
            });
            return false;
        });
        
        // Generate SEO Metadata
        $(document).on('click', '.btn-ai-seo', function(e) {
            e.preventDefault();
            console.log('Generate SEO clicked');
            
            const titleField = document.getElementById('id_title');
            const contentField = document.getElementById('id_content');
            
            if (!titleField || !titleField.value.trim()) {
                showStatus('Please enter title first!', 'error');
                return false;
            }
            
            if (!contentField || !contentField.value.trim()) {
                showStatus('Please enter content first!', 'error');
                return false;
            }
            
            showStatus('Generating SEO metadata...', 'info');
            
            $.ajax({
                url: '/admin/blog/post/ai-seo/',
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
                data: JSON.stringify({
                    title: titleField.value,
                    content: contentField.value
                }),
                success: function(data) {
                    console.log('SEO response:', data);
                    if (data.success) {
                        // Fill SEO title
                        const seoTitleField = document.getElementById('id_seo_title');
                        if (seoTitleField && data.seo_title) {
                            seoTitleField.value = data.seo_title;
                        }
                        
                        // Fill meta description
                        const metaDescField = document.getElementById('id_meta_description');
                        if (metaDescField && data.meta_description) {
                            metaDescField.value = data.meta_description;
                        }
                        
                        // Fill slug
                        const slugField = document.getElementById('id_slug');
                        if (slugField && data.slug_suggestion) {
                            slugField.value = data.slug_suggestion;
                        }
                        
                        // Fill SEO keywords (as JSON array string)
                        const seoKeywordsField = document.getElementById('id_seo_keywords');
                        if (seoKeywordsField && data.seo_keywords && Array.isArray(data.seo_keywords)) {
                            seoKeywordsField.value = JSON.stringify(data.seo_keywords);
                        }
                        
                        showStatus('✅ SEO metadata generated successfully!', 'success');
                    } else {
                        showStatus('❌ Error: ' + (data.error || 'Failed to generate'), 'error');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX error:', xhr, status, error);
                    let errorMsg = 'Network error';
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        errorMsg = xhr.responseJSON.error;
                    }
                    showStatus('❌ Error: ' + errorMsg, 'error');
                }
            });
            return false;
        });
        
        // Generate Summary
        $(document).on('click', '.btn-ai-summary', function(e) {
            e.preventDefault();
            console.log('Generate Summary clicked');
            
            const contentField = document.getElementById('id_content');
            
            if (!contentField || !contentField.value.trim()) {
                showStatus('Please enter content first!', 'error');
                return false;
            }
            
            showStatus('Generating summary...', 'info');
            
            $.ajax({
                url: '/admin/blog/post/ai-summary/',
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
                data: JSON.stringify({
                    content: contentField.value
                }),
                success: function(data) {
                    console.log('Summary response:', data);
                    if (data.success) {
                        const summaryField = document.getElementById('id_summary');
                        if (summaryField && data.summary) {
                            summaryField.value = data.summary;
                            showStatus('✅ Summary generated successfully!', 'success');
                        }
                    } else {
                        showStatus('❌ Error: ' + (data.error || 'Failed to generate'), 'error');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX error:', xhr, status, error);
                    let errorMsg = 'Network error';
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        errorMsg = xhr.responseJSON.error;
                    }
                    showStatus('❌ Error: ' + errorMsg, 'error');
                }
            });
            return false;
        });
        
        console.log('AI Admin event handlers registered');
    });
    
    // Also try without jQuery ready in case jQuery loads later
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).ready(function($) {
            console.log('AI Admin JS loaded via django.jQuery');
        });
    }
    
})(django.jQuery || jQuery);
