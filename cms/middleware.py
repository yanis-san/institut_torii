"""
Analytics middleware — Logs every public page view to the database.

Only tracks GET requests on public-facing pages.
Ignores: admin, CMS, static files, media, API endpoints, bots (optional).
"""
import logging

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from .models import PageView

logger = logging.getLogger(__name__)

# Paths to never track
IGNORED_PREFIXES = (
    f'/{settings.ADMIN_URL_PREFIX}/',
    f'/{settings.CMS_URL_PREFIX}/',
    '/static/',
    '/media/',
    '/__reload__/',
    '/favicon.ico',
)


class AnalyticsMiddleware(MiddlewareMixin):
    """
    Server-side analytics. Records each public GET request as a PageView.

    Placed AFTER SessionMiddleware and AuthenticationMiddleware so we have
    access to request.session and request.user.
    """

    def process_response(self, request, response):
        try:
            self._track(request, response)
        except Exception:
            logger.debug('Analytics tracking failed', exc_info=True)
        return response

    def _track(self, request, response):
        # Only track GET requests
        if request.method != 'GET':
            return

        path = request.path

        # Skip ignored paths
        if any(path.startswith(prefix) for prefix in IGNORED_PREFIXES):
            return

        # Skip AJAX / htmx partial requests (they're not real page loads)
        if request.headers.get('HX-Request'):
            return

        # Get visitor info
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip = self._get_client_ip(request)
        referrer = request.META.get('HTTP_REFERER', '')

        # Parse UTM parameters
        utm_source = request.GET.get('utm_source', '')
        utm_medium = request.GET.get('utm_medium', '')
        utm_campaign = request.GET.get('utm_campaign', '')

        # Build full URL
        full_url = request.build_absolute_uri()

        # Session key (create session if needed)
        session_key = ''
        if hasattr(request, 'session'):
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key or ''

        PageView.objects.create(
            path=path[:500],
            full_url=full_url[:1000],
            method='GET',
            status_code=response.status_code,
            visitor_hash=PageView.make_visitor_hash(ip, user_agent),
            session_key=session_key[:40],
            is_authenticated=getattr(request, 'user', None)
                and request.user.is_authenticated,
            referrer=referrer[:1000],
            referrer_domain=PageView.extract_domain(referrer)[:255],
            utm_source=utm_source[:200],
            utm_medium=utm_medium[:200],
            utm_campaign=utm_campaign[:200],
            user_agent=user_agent,
            device_type=PageView.parse_device_type(user_agent),
            browser=PageView.parse_browser(user_agent),
            os=PageView.parse_os(user_agent),
        )

    @staticmethod
    def _get_client_ip(request):
        """Get client IP, respecting X-Forwarded-For for proxied requests."""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
