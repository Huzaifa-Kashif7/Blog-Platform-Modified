"""
Blog Post Model with AI-enhanced fields
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from .validators import validate_image_upload


class Category(models.Model):
    """Organize posts into high-level categories."""
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Free-form tagging for posts."""
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    """
    Blog Post Model with AI-powered features:
    - Semantic search via embeddings
    - Auto-generated summaries
    - AI-generated tags and categories
    - SEO metadata
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    # Basic fields
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    cover_image = models.ImageField(upload_to='post_covers/', blank=True, null=True, validators=[validate_image_upload])
    view_count = models.PositiveIntegerField(default=0)

    # SEO fields
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    meta_description = models.CharField(max_length=150, blank=True)
    seo_title = models.CharField(max_length=200, blank=True)
    seo_keywords = models.JSONField(default=list, blank=True, help_text="List of SEO keywords")

    # AI-generated fields (legacy)
    summary = models.TextField(blank=True, help_text="AI-generated summary of the post")
    category = models.CharField(max_length=100, blank=True, help_text="AI-suggested category")
    tags = models.JSONField(default=list, blank=True, help_text="AI-suggested tags (list)")

    # Manual taxonomy
    primary_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        help_text="Manually selected primary category"
    )
    manual_tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='posts',
        help_text="Author-selected tags"
    )

    # Semantic search field
    embedding = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Vector embedding for semantic search"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """
        Auto-generate slug if not provided.
        AI features (summary, embedding) are handled in views/utils.
        """
        if not self.slug:
            self.slug = slugify(self.title)

        # Ensure slug uniqueness
        original_slug = self.slug
        counter = 1
        while Post.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('post_detail', kwargs={'slug': self.slug})

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.filter(is_active=True).count()

    @property
    def bookmark_count(self):
        return self.bookmarks.count()

    def delete(self, *args, **kwargs):
        if self.cover_image:
            self.cover_image.delete(save=False)
        super().delete(*args, **kwargs)


class PostImage(models.Model):
    """Additional gallery images per post."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='post_gallery/', validators=[validate_image_upload])
    caption = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"Image for {self.post.title}"

    def delete(self, *args, **kwargs):
        storage = self.image.storage
        image_name = self.image.name
        super().delete(*args, **kwargs)
        if image_name:
            storage.delete(image_name)


class PostLike(models.Model):
    """Track which users like each post."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} likes {self.post.title}"


class Bookmark(models.Model):
    """Allow users to save posts for later."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} bookmarked {self.post.title}"


class Comment(models.Model):
    """Store comments for each post."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='deleted_comments',
        null=True,
        blank=True
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"

    def soft_delete(self, user=None):
        self.is_active = False
        self.deleted_by = user
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'deleted_by', 'deleted_at'])


class Notification(models.Model):
    """Notify users about interactions on their posts or system updates."""
    NOTIFICATION_TYPES = [
        ('comment', 'Comment'),
        ('like', 'Like'),
        ('bookmark', 'Bookmark'),
        ('system', 'System'),
        ('comment_removed', 'Comment Removed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='initiated_notifications',
        null=True,
        blank=True
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        related_name='notifications',
        null=True,
        blank=True
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"


class UserProfile(models.Model):
    """Extend Django user profile."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    short_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile for {self.user.username}"

    @property
    def display_name(self):
        if self.short_name:
            return self.short_name
        full_name = self.user.get_full_name()
        return full_name or self.user.username

    @property
    def joined_display(self):
        return self.user.date_joined or timezone.now()

