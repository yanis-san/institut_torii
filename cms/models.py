"""
CMS Models — Editable site content (singleton pattern) + Analytics.

HomePage: All editable content for the public homepage.
SiteSettings: Global settings (contact info, social links, etc.)
PageView: Server-side analytics for page visits.
"""
from io import BytesIO
from hashlib import sha256

from django.db import models
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _

from PIL import Image


# ──────────────────────────────────────────────
# Image optimization
# ──────────────────────────────────────────────

MAX_DIMENSIONS = (1920, 1080)
WEBP_QUALITY = 85


def optimize_image(image_field, *, max_size=MAX_DIMENSIONS):
    """Resize + convert to WebP. Modifies the field in-place."""
    if not image_field:
        return
    try:
        img = Image.open(image_field)
    except Exception:
        return

    if img.mode in ('RGBA', 'P', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail(max_size, Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format='WEBP', quality=WEBP_QUALITY)
    buffer.seek(0)

    name = image_field.name.rsplit('.', 1)[0] + '.webp'
    image_field.save(name, ContentFile(buffer.read()), save=False)


# ──────────────────────────────────────────────
# SiteSettings Singleton
# ──────────────────────────────────────────────

class SiteSettings(models.Model):
    """
    Paramètres globaux du site — singleton (pk=1 toujours).
    Contact, réseaux sociaux, configuration générale.
    """

    # --- Contact ---
    phone = models.CharField(_('téléphone'), max_length=30, blank=True)
    email = models.EmailField(_('email de contact'), blank=True)
    address = models.TextField(_('adresse'), blank=True)
    google_maps_url = models.URLField(_('lien Google Maps'), blank=True)

    # --- Réseaux sociaux ---
    facebook_url = models.URLField(_('Facebook'), blank=True)
    instagram_url = models.URLField(_('Instagram'), blank=True)
    tiktok_url = models.URLField(_('TikTok'), blank=True)
    youtube_url = models.URLField(_('YouTube'), blank=True)
    whatsapp_number = models.CharField(_('WhatsApp'), max_length=30, blank=True)

    # --- SEO général ---
    site_name = models.CharField(
        _('nom du site'), max_length=100, default='Institut Torii',
    )
    meta_description = models.TextField(
        _('description SEO par défaut'), blank=True,
        default="Institut Torii — Cours de japonais, chinois et coréen en Algérie.",
    )
    og_image = models.ImageField(
        _('image Open Graph'), upload_to='site/', blank=True,
        help_text=_("Image par défaut pour les partages (1200×630 recommandé)"),
    )

    # --- Horaires ---
    opening_hours = models.TextField(
        _("horaires d'ouverture"), blank=True,
        help_text=_("Ex: Dim-Jeu 09:00–18:00"),
    )

    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    class Meta:
        verbose_name = _('paramètres du site')
        verbose_name_plural = _('paramètres du site')

    def __str__(self):
        return 'Paramètres du site'

    def save(self, *args, **kwargs):
        self.pk = 1
        if self.og_image and hasattr(self.og_image, 'file'):
            optimize_image(self.og_image, max_size=(1200, 630))
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ──────────────────────────────────────────────
# HomePage Singleton
# ──────────────────────────────────────────────

class HomePage(models.Model):
    """
    Contenu éditable de la page d'accueil — singleton (pk=1 toujours).
    """

    # --- Hero ---
    hero_title = models.CharField(
        _('titre hero'), max_length=200,
        default="Découvrez les cultures d'Asie",
    )
    hero_subtitle = models.TextField(
        _('sous-titre hero'), blank=True,
        default="Japonais, Chinois, Coréen — formations et ateliers culturels en Algérie",
    )
    hero_image = models.ImageField(
        _('image hero'), upload_to='homepage/', blank=True,
    )
    hero_cta_text = models.CharField(
        _('texte bouton CTA'), max_length=100, default='Nous contacter',
    )
    hero_cta_url = models.CharField(
        _('lien bouton CTA'), max_length=200, default='/contact/',
    )

    # --- Section À propos ---
    about_title = models.CharField(
        _('titre à propos'), max_length=200, default='Notre Institut',
    )
    about_text = models.TextField(_('texte à propos'), blank=True)
    about_image = models.ImageField(
        _('image à propos'), upload_to='homepage/', blank=True,
    )

    # --- Section Statistiques ---
    stat_students = models.CharField(_('nombre étudiants'), max_length=20, default='500+')
    stat_students_label = models.CharField(_('label étudiants'), max_length=50, default='Étudiants formés')
    stat_teachers = models.CharField(_('nombre enseignants'), max_length=20, default='10+')
    stat_teachers_label = models.CharField(_('label enseignants'), max_length=50, default='Enseignants natifs')
    stat_languages = models.CharField(_('nombre langues'), max_length=20, default='3')
    stat_languages_label = models.CharField(_('label langues'), max_length=50, default='Langues enseignées')
    stat_years = models.CharField(_('nombre années'), max_length=20, default='5+')
    stat_years_label = models.CharField(_('label années'), max_length=50, default="Années d'expérience")

    # --- Témoignages ---
    testimonial_1_text = models.TextField(_('témoignage 1'), blank=True)
    testimonial_1_author = models.CharField(_('auteur 1'), max_length=100, blank=True)
    testimonial_1_role = models.CharField(_('rôle 1'), max_length=100, blank=True)
    testimonial_2_text = models.TextField(_('témoignage 2'), blank=True)
    testimonial_2_author = models.CharField(_('auteur 2'), max_length=100, blank=True)
    testimonial_2_role = models.CharField(_('rôle 2'), max_length=100, blank=True)
    testimonial_3_text = models.TextField(_('témoignage 3'), blank=True)
    testimonial_3_author = models.CharField(_('auteur 3'), max_length=100, blank=True)
    testimonial_3_role = models.CharField(_('rôle 3'), max_length=100, blank=True)

    # --- CTA final ---
    cta_title = models.CharField(
        _('titre CTA final'), max_length=200,
        default='Prêt à commencer votre aventure ?',
    )
    cta_text = models.TextField(_('texte CTA final'), blank=True)

    updated_at = models.DateTimeField(_('mis à jour le'), auto_now=True)

    _IMAGE_FIELDS = ['hero_image', 'about_image']

    class Meta:
        verbose_name = _("page d'accueil")
        verbose_name_plural = _("page d'accueil")

    def __str__(self):
        return "Page d'accueil"

    def save(self, *args, **kwargs):
        self.pk = 1
        for field_name in self._IMAGE_FIELDS:
            field = getattr(self, field_name)
            if field and hasattr(field, 'file'):
                optimize_image(field)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ──────────────────────────────────────────────
# Analytics — Server-side page tracking
# ──────────────────────────────────────────────

class PageView(models.Model):
    """
    Tracks each page visit on the public site.
    Logged automatically by cms.middleware.AnalyticsMiddleware.
    """

    class DeviceType(models.TextChoices):
        DESKTOP = 'desktop', _('Desktop')
        MOBILE = 'mobile', _('Mobile')
        TABLET = 'tablet', _('Tablette')
        BOT = 'bot', _('Bot')

    # --- Request data ---
    path = models.CharField(_('chemin'), max_length=500, db_index=True)
    full_url = models.CharField(_('URL complète'), max_length=1000, blank=True)
    method = models.CharField(_('méthode HTTP'), max_length=10, default='GET')
    status_code = models.PositiveSmallIntegerField(
        _('code de réponse'), default=200,
    )

    # --- Visitor identification ---
    visitor_hash = models.CharField(
        _('hash visiteur'), max_length=64, db_index=True,
        help_text=_('SHA-256 anonymisé : IP + User-Agent'),
    )
    session_key = models.CharField(
        _('clé session'), max_length=40, blank=True, db_index=True,
    )
    is_authenticated = models.BooleanField(_('authentifié'), default=False)

    # --- Source & referrer ---
    referrer = models.URLField(_('referrer'), max_length=1000, blank=True)
    referrer_domain = models.CharField(
        _('domaine referrer'), max_length=255, blank=True, db_index=True,
    )
    utm_source = models.CharField(_('utm_source'), max_length=200, blank=True)
    utm_medium = models.CharField(_('utm_medium'), max_length=200, blank=True)
    utm_campaign = models.CharField(_('utm_campaign'), max_length=200, blank=True)

    # --- Device & browser ---
    user_agent = models.TextField(_('user agent'), blank=True)
    device_type = models.CharField(
        _('type appareil'), max_length=10,
        choices=DeviceType.choices, default=DeviceType.DESKTOP,
    )
    browser = models.CharField(_('navigateur'), max_length=100, blank=True)
    os = models.CharField(_('système'), max_length=100, blank=True)

    # --- Timestamps ---
    timestamp = models.DateTimeField(_('horodatage'), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('page vue')
        verbose_name_plural = _('pages vues')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['path', 'timestamp']),
            models.Index(fields=['visitor_hash', 'timestamp']),
            models.Index(fields=['device_type', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.path} — {self.timestamp:%d/%m %H:%M}'

    @staticmethod
    def make_visitor_hash(ip, user_agent):
        """Create a privacy-friendly hash from IP + User-Agent."""
        raw = f'{ip}:{user_agent}'.encode()
        return sha256(raw).hexdigest()

    @staticmethod
    def parse_device_type(user_agent):
        """Simple device detection from User-Agent string."""
        ua = user_agent.lower()
        bot_keywords = ['bot', 'crawl', 'spider', 'slurp', 'mediapartners', 'wget', 'curl']
        if any(kw in ua for kw in bot_keywords):
            return PageView.DeviceType.BOT
        if 'tablet' in ua or 'ipad' in ua:
            return PageView.DeviceType.TABLET
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipod', 'opera mini', 'opera mobi']
        if any(kw in ua for kw in mobile_keywords):
            return PageView.DeviceType.MOBILE
        return PageView.DeviceType.DESKTOP

    @staticmethod
    def parse_browser(user_agent):
        """Extract browser name from User-Agent."""
        ua = user_agent
        if 'Edg/' in ua:
            return 'Edge'
        if 'OPR/' in ua or 'Opera' in ua:
            return 'Opera'
        if 'Chrome/' in ua and 'Safari/' in ua:
            return 'Chrome'
        if 'Firefox/' in ua:
            return 'Firefox'
        if 'Safari/' in ua:
            return 'Safari'
        if 'MSIE' in ua or 'Trident/' in ua:
            return 'IE'
        return 'Autre'

    @staticmethod
    def parse_os(user_agent):
        """Extract OS from User-Agent."""
        ua = user_agent
        if 'Windows' in ua:
            return 'Windows'
        if 'Mac OS' in ua or 'Macintosh' in ua:
            return 'macOS'
        if 'iPhone' in ua or 'iPad' in ua:
            return 'iOS'
        if 'Android' in ua:
            return 'Android'
        if 'Linux' in ua:
            return 'Linux'
        return 'Autre'

    # Known AI platform referrer domains
    AI_REFERRER_DOMAINS = {
        'chatgpt.com': 'ChatGPT',
        'chat.openai.com': 'ChatGPT',
        'gemini.google.com': 'Gemini',
        'perplexity.ai': 'Perplexity',
        'www.perplexity.ai': 'Perplexity',
        'claude.ai': 'Claude',
        'copilot.microsoft.com': 'Copilot',
        'you.com': 'You.com',
        'www.you.com': 'You.com',
        'phind.com': 'Phind',
        'www.phind.com': 'Phind',
        'poe.com': 'Poe',
        'www.poe.com': 'Poe',
        'huggingface.co': 'HuggingFace',
        'bard.google.com': 'Gemini',
        'chat.deepseek.com': 'DeepSeek',
        'deepseek.com': 'DeepSeek',
        'www.deepseek.com': 'DeepSeek',
    }

    # Known search engine referrer domains
    SEARCH_ENGINE_DOMAINS = {
        'google.com': 'Google',
        'www.google.com': 'Google',
        'google.fr': 'Google',
        'www.google.fr': 'Google',
        'google.dz': 'Google',
        'www.google.dz': 'Google',
        'google.co.jp': 'Google',
        'www.google.co.jp': 'Google',
        'google.co.kr': 'Google',
        'www.google.co.kr': 'Google',
        'bing.com': 'Bing',
        'www.bing.com': 'Bing',
        'yahoo.com': 'Yahoo',
        'www.yahoo.com': 'Yahoo',
        'search.yahoo.com': 'Yahoo',
        'yahoo.co.jp': 'Yahoo',
        'duckduckgo.com': 'DuckDuckGo',
        'www.duckduckgo.com': 'DuckDuckGo',
        'ecosia.org': 'Ecosia',
        'www.ecosia.org': 'Ecosia',
        'qwant.com': 'Qwant',
        'www.qwant.com': 'Qwant',
        'baidu.com': 'Baidu',
        'www.baidu.com': 'Baidu',
        'yandex.com': 'Yandex',
        'www.yandex.com': 'Yandex',
        'naver.com': 'Naver',
        'www.naver.com': 'Naver',
        'search.naver.com': 'Naver',
    }

    # Known social media referrer domains
    SOCIAL_MEDIA_DOMAINS = {
        'facebook.com': 'Facebook',
        'www.facebook.com': 'Facebook',
        'm.facebook.com': 'Facebook',
        'l.facebook.com': 'Facebook',
        'lm.facebook.com': 'Facebook',
        'instagram.com': 'Instagram',
        'www.instagram.com': 'Instagram',
        'l.instagram.com': 'Instagram',
        'twitter.com': 'X (Twitter)',
        'www.twitter.com': 'X (Twitter)',
        'x.com': 'X (Twitter)',
        't.co': 'X (Twitter)',
        'linkedin.com': 'LinkedIn',
        'www.linkedin.com': 'LinkedIn',
        'tiktok.com': 'TikTok',
        'www.tiktok.com': 'TikTok',
        'youtube.com': 'YouTube',
        'www.youtube.com': 'YouTube',
        'm.youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'reddit.com': 'Reddit',
        'www.reddit.com': 'Reddit',
        'old.reddit.com': 'Reddit',
        'pinterest.com': 'Pinterest',
        'www.pinterest.com': 'Pinterest',
        'pinterest.fr': 'Pinterest',
        'snapchat.com': 'Snapchat',
        'www.snapchat.com': 'Snapchat',
        'whatsapp.com': 'WhatsApp',
        'web.whatsapp.com': 'WhatsApp',
        'wa.me': 'WhatsApp',
        'telegram.org': 'Telegram',
        't.me': 'Telegram',
        'threads.net': 'Threads',
        'www.threads.net': 'Threads',
    }

    @classmethod
    def classify_ai_referrer(cls, domain):
        """Return the AI platform name if domain is a known AI, else ''."""
        if not domain:
            return ''
        d = domain.lower()
        return cls.AI_REFERRER_DOMAINS.get(d, '')

    @classmethod
    def classify_search_engine(cls, domain):
        """Return the search engine name if domain is a known SE, else ''."""
        if not domain:
            return ''
        d = domain.lower()
        return cls.SEARCH_ENGINE_DOMAINS.get(d, '')

    @classmethod
    def classify_social_media(cls, domain):
        """Return the social media name if domain is known, else ''."""
        if not domain:
            return ''
        d = domain.lower()
        return cls.SOCIAL_MEDIA_DOMAINS.get(d, '')

    @classmethod
    def classify_referrer(cls, domain):
        """Classify a referrer domain into a category: 'ai', 'search', 'social', or 'other'."""
        if not domain:
            return 'direct'
        if cls.classify_ai_referrer(domain):
            return 'ai'
        if cls.classify_search_engine(domain):
            return 'search'
        if cls.classify_social_media(domain):
            return 'social'
        return 'other'

    @staticmethod
    def extract_domain(url):
        """Extract domain from a URL."""
        if not url:
            return ''
        try:
            from urllib.parse import urlparse
            return urlparse(url).hostname or ''
        except Exception:
            return ''
