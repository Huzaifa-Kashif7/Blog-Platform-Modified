"""
Admin configuration for Blog app with AI features
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
import json
from .models import (
    Post,
    Comment,
    PostLike,
    UserProfile,
    Category,
    Tag,
    Bookmark,
    Notification,
    PostImage,
)
from .ai_utils import generate_tags_and_category, generate_seo_metadata, generate_summary, generate_embedding


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Post model with AI features"""
    
    list_display = ['title', 'author', 'category', 'created_at', 'has_summary', 'has_embedding']
    list_filter = ['category', 'created_at', 'author']
    search_fields = ['title', 'content', 'tags', 'category']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'author', 'content')
        }),
        ('AI-Powered Features', {
            'fields': ('ai_actions',),
            'description': 'Use the buttons below to generate AI content'
        }),
        ('AI-Generated Content', {
            'fields': ('summary', 'category', 'tags', 'embedding'),
            'classes': ('collapse',)
        }),
        ('SEO Metadata', {
            'fields': ('seo_title', 'meta_description', 'seo_keywords'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'ai_actions']
    
    class Media:
        css = {
            'all': ('admin/css/ai_admin.css',)
        }
        js = ('admin/js/ai_admin.js',)
    
    def ai_actions(self, obj):
        """Display AI action buttons with inline JavaScript"""
        return format_html(
            '''
            <div style="padding: 10px; background: #f8f9fa; border-radius: 5px; margin-bottom: 10px;">
                <button type="button" class="btn-ai-tags" style="margin: 5px; padding: 8px 15px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    ✨ Generate Tags & Category
                </button>
                <button type="button" class="btn-ai-seo" style="margin: 5px; padding: 8px 15px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    🔍 Generate SEO Metadata
                </button>
                <button type="button" class="btn-ai-summary" style="margin: 5px; padding: 8px 15px; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    📝 Generate Summary
                </button>
                <div id="ai-status" style="margin-top: 10px; color: #666; font-size: 12px; min-height: 20px;"></div>
            </div>
            <script>
            (function() {
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
                
                function showStatus(msg, type) {
                    const div = document.getElementById('ai-status');
                    if (div) {
                        div.textContent = msg;
                        div.style.color = type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#0066cc';
                    }
                }
                
                function makeRequest(url, data, successCallback) {
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', url, true);
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
                    xhr.onload = function() {
                        if (xhr.status === 200) {
                            const response = JSON.parse(xhr.responseText);
                            successCallback(response);
                        } else {
                            showStatus('❌ Error: ' + xhr.statusText, 'error');
                        }
                    };
                    xhr.onerror = function() {
                        showStatus('❌ Network error', 'error');
                    };
                    xhr.send(JSON.stringify(data));
                }
                
                // Helper function to find and set field value - enhanced
                function setFieldValue(fieldId, value) {
                    console.log('Looking for field:', fieldId, 'Value:', value);
                    
                    // Try direct ID lookup
                    let field = document.getElementById(fieldId);
                    
                    // If not found, try name attribute
                    if (!field) {
                        const fieldName = fieldId.replace('id_', '');
                        field = document.querySelector('[name="' + fieldName + '"]') || 
                                document.querySelector('[id*="' + fieldName + '"]');
                    }
                    
                    // If still not found, try case-insensitive search
                    if (!field) {
                        const allInputs = document.querySelectorAll('input, textarea');
                        for (let i = 0; i < allInputs.length; i++) {
                            if (allInputs[i].id && allInputs[i].id.toLowerCase().includes(fieldId.replace('id_', '').toLowerCase())) {
                                field = allInputs[i];
                                break;
                            }
                            if (allInputs[i].name && allInputs[i].name.toLowerCase().includes(fieldId.replace('id_', '').toLowerCase())) {
                                field = allInputs[i];
                                break;
                            }
                        }
                    }
                    
                    if (field) {
                        // For JSONField, Django admin might use JSON editor - try direct value first
                        field.value = value;
                        
                        // Try different ways to update
                        if (field.tagName === 'TEXTAREA') {
                            field.textContent = value;
                        }
                        
                        // Trigger events
                        field.dispatchEvent(new Event('input', { bubbles: true }));
                        field.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        // For JSON fields, might need to trigger JSON editor update
                        if (field.classList.contains('vLargeTextField') || field.name.includes('tags') || field.name.includes('keywords')) {
                            // Try to find and update JSON editor if exists
                            const jsonEditor = field.closest('.field-box') || field.parentElement;
                            if (jsonEditor) {
                                const jsonDisplay = jsonEditor.querySelector('.json-widget-display');
                                if (jsonDisplay) {
                                    jsonDisplay.textContent = typeof value === 'string' ? value : JSON.stringify(value);
                                }
                            }
                        }
                        
                        console.log('✅ Set ' + fieldId + ' (found as ' + field.id + ' or ' + field.name + ') to:', value);
                        return true;
                    } else {
                        console.error('❌ Field NOT found: ' + fieldId);
                        // List all available fields for debugging
                        console.log('Available fields:', Array.from(document.querySelectorAll('input, textarea')).map(el => ({
                            id: el.id,
                            name: el.name,
                            type: el.type || el.tagName
                        })));
                        return false;
                    }
                }
                
                // Helper to expand collapsed sections
                function expandSection(sectionName) {
                    const sections = document.querySelectorAll('fieldset.collapse');
                    sections.forEach(function(section) {
                        const legend = section.querySelector('legend');
                        if (legend && legend.textContent.toLowerCase().includes(sectionName.toLowerCase())) {
                            if (section.classList.contains('collapsed')) {
                                const toggle = legend.querySelector('a');
                                if (toggle) toggle.click();
                            }
                        }
                    });
                }
                
                document.addEventListener('click', function(e) {
                    if (e.target.classList.contains('btn-ai-tags')) {
                        e.preventDefault();
                        const content = document.getElementById('id_content').value;
                        const title = document.getElementById('id_title').value || '';
                        if (!content) {
                            showStatus('Please enter content first!', 'error');
                            return;
                        }
                        showStatus('Generating tags and category...', 'info');
                        makeRequest('/admin/blog/post/ai-tags/', {content: title + '\\n\\n' + content}, function(data) {
                            console.log('AI Tags Response:', data);
                            if (data.success) {
                                expandSection('AI-Generated Content');
                                setTimeout(function() {
                                    let filled = [];
                                    if (data.category) {
                                        if (setFieldValue('id_category', data.category)) {
                                            filled.push('Category');
                                        }
                                    }
                                    if (data.tags && Array.isArray(data.tags)) {
                                        // Try both JSON string and comma-separated
                                        const tagsJson = JSON.stringify(data.tags);
                                        const tagsComma = data.tags.join(', ');
                                        if (setFieldValue('id_tags', tagsJson) || setFieldValue('id_tags', tagsComma)) {
                                            filled.push('Tags (' + data.tags.length + ')');
                                        }
                                    }
                                    if (filled.length > 0) {
                                        showStatus('✅ Generated! Filled: ' + filled.join(', ') + '. Check collapsed sections.', 'success');
                                    } else {
                                        showStatus('⚠️ Generated but fields not found. Check console (F12) for details.', 'error');
                                    }
                                }, 500);
                            } else {
                                showStatus('❌ ' + (data.error || 'Failed'), 'error');
                            }
                        });
                    } else if (e.target.classList.contains('btn-ai-seo')) {
                        e.preventDefault();
                        const title = document.getElementById('id_title').value;
                        const content = document.getElementById('id_content').value;
                        if (!title || !content) {
                            showStatus('Please enter title and content first!', 'error');
                            return;
                        }
                        showStatus('Generating SEO metadata...', 'info');
                        makeRequest('/admin/blog/post/ai-seo/', {title: title, content: content}, function(data) {
                            console.log('AI SEO Response:', data);
                            if (data.success) {
                                expandSection('SEO Metadata');
                                setTimeout(function() {
                                    let filled = [];
                                    if (data.seo_title) {
                                        if (setFieldValue('id_seo_title', data.seo_title)) {
                                            filled.push('SEO Title');
                                        }
                                    }
                                    if (data.meta_description) {
                                        if (setFieldValue('id_meta_description', data.meta_description)) {
                                            filled.push('Meta Description');
                                        }
                                    }
                                    if (data.slug_suggestion) {
                                        if (setFieldValue('id_slug', data.slug_suggestion)) {
                                            filled.push('Slug');
                                        }
                                    }
                                    if (data.seo_keywords && Array.isArray(data.seo_keywords)) {
                                        const keywordsJson = JSON.stringify(data.seo_keywords);
                                        const keywordsComma = data.seo_keywords.join(', ');
                                        if (setFieldValue('id_seo_keywords', keywordsJson) || setFieldValue('id_seo_keywords', keywordsComma)) {
                                            filled.push('Keywords (' + data.seo_keywords.length + ')');
                                        }
                                    }
                                    if (filled.length > 0) {
                                        showStatus('✅ Generated! Filled: ' + filled.join(', ') + '. Check collapsed sections.', 'success');
                                    } else {
                                        showStatus('⚠️ Generated but fields not found. Check console (F12).', 'error');
                                    }
                                }, 500);
                            } else {
                                showStatus('❌ ' + (data.error || 'Failed'), 'error');
                            }
                        });
                    } else if (e.target.classList.contains('btn-ai-summary')) {
                        e.preventDefault();
                        const content = document.getElementById('id_content').value;
                        if (!content) {
                            showStatus('Please enter content first!', 'error');
                            return;
                        }
                        showStatus('Generating summary...', 'info');
                        makeRequest('/admin/blog/post/ai-summary/', {content: content}, function(data) {
                            if (data.success && data.summary) {
                                expandSection('AI-Generated Content');
                                setTimeout(function() {
                                    if (setFieldValue('id_summary', data.summary)) {
                                        showStatus('✅ Summary generated! Check "AI-Generated Content" section.', 'success');
                                    } else {
                                        showStatus('✅ Summary generated but field not found. Check "AI-Generated Content" section.', 'info');
                                    }
                                }, 300);
                            } else {
                                showStatus('❌ ' + (data.error || 'Failed'), 'error');
                            }
                        });
                    }
                });
            })();
            </script>
            '''
        )
    ai_actions.short_description = 'AI Actions'
    
    def has_summary(self, obj):
        """Check if post has AI-generated summary"""
        return bool(obj.summary)
    has_summary.boolean = True
    has_summary.short_description = 'Has Summary'
    
    def has_embedding(self, obj):
        """Check if post has embedding"""
        return bool(obj.embedding and len(obj.embedding) > 0)
    has_embedding.boolean = True
    has_embedding.short_description = 'Has Embedding'
    
    def save_model(self, request, obj, form, change):
        """Auto-generate summary and embedding if content exists"""
        super().save_model(request, obj, form, change)
        
        # Auto-generate summary if missing and content exists
        if not obj.summary and obj.content:
            try:
                obj.summary = generate_summary(obj.content)
                if obj.summary:
                    obj.save(update_fields=['summary'])
            except Exception as e:
                print(f"Error generating summary: {e}")
        
        # Auto-generate embedding if missing
        if (not obj.embedding or len(obj.embedding) == 0) and obj.content:
            try:
                embedding_text = f"{obj.title} {obj.content}"
                embedding = generate_embedding(embedding_text)
                if embedding:
                    obj.embedding = embedding
                    obj.save(update_fields=['embedding'])
            except Exception as e:
                print(f"Error generating embedding: {e}")
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ai-tags/', self.admin_site.admin_view(self.ai_tags_view), name='admin_ai_tags'),
            path('ai-seo/', self.admin_site.admin_view(self.ai_seo_view), name='admin_ai_seo'),
            path('ai-summary/', self.admin_site.admin_view(self.ai_summary_view), name='admin_ai_summary'),
        ]
        return custom_urls + urls
    
    def ai_tags_view(self, request):
        """Admin view for generating tags and category"""
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                content = data.get('content', '').strip()
                
                if not content:
                    return JsonResponse({'success': False, 'error': 'Content is required'}, status=400)
                
                result = generate_tags_and_category(content)
                
                return JsonResponse({
                    'success': True,
                    'category': result.get('category', ''),
                    'tags': result.get('tags', [])
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    def ai_seo_view(self, request):
        """Admin view for generating SEO metadata"""
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                title = data.get('title', '').strip()
                content = data.get('content', '').strip()
                
                if not title or not content:
                    return JsonResponse({'success': False, 'error': 'Title and content are required'}, status=400)
                
                result = generate_seo_metadata(title, content)
                
                return JsonResponse({
                    'success': True,
                    'seo_title': result.get('seo_title', ''),
                    'meta_description': result.get('meta_description', ''),
                    'seo_keywords': result.get('seo_keywords', []),
                    'slug_suggestion': result.get('slug_suggestion', '')
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    def ai_summary_view(self, request):
        """Admin view for generating summary"""
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                content = data.get('content', '').strip()
                
                if not content:
                    return JsonResponse({'success': False, 'error': 'Content is required'}, status=400)
                
                summary = generate_summary(content)
                
                return JsonResponse({
                    'success': True,
                    'summary': summary
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('post__title', 'author__username', 'content')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created_at')
    search_fields = ('post__title', 'user__username')
    list_filter = ('created_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_name', 'location', 'email_verified', 'created_at')
    search_fields = ('user__username', 'short_name', 'location')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('user__username', 'post__title')
    autocomplete_fields = ('user', 'post')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'message')
    autocomplete_fields = ('user', 'actor', 'post')


@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ('post', 'display_order')
    autocomplete_fields = ('post',)
