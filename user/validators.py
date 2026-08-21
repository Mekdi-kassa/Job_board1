# user/validators.py
import re
import os
import bleach
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

try:
    import magic
except ImportError:
    magic = None


# ============================================================
# SQL INJECTION PROTECTION
# ============================================================
class SQLInjectionValidator:
    """Validate input against SQL injection attacks"""
    
    SQL_PATTERNS = [
        r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b',
        r'\b(UNION|JOIN|WHERE|HAVING|GROUP BY|ORDER BY)\b',
        r'--\s*.*$',
        r';\s*.*$',
        r'\b(OR|AND)\s+\d+\s*=\s*\d+\b',
        r'\b(EXEC|EXECUTE)\b',
        r'\b(SLEEP|BENCHMARK)\b',
    ]
    
    @staticmethod
    def validate(value):
        """Check for SQL injection patterns"""
        if not isinstance(value, str):
            return value
        
        value_upper = value.upper()
        for pattern in SQLInjectionValidator.SQL_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                raise ValidationError(
                    _('Invalid input: SQL pattern detected.')
                )
        
        if re.search(r"'\s*(OR|AND)\s*'\s*=", value, re.IGNORECASE):
            raise ValidationError(_('Invalid input: SQL pattern detected.'))
        
        return value


# ============================================================
# XSS PROTECTION
# ============================================================
class XSSValidator:
    """Validate and sanitize input against XSS attacks"""
    
    ALLOWED_TAGS = ['p', 'br', 'b', 'i', 'u', 'em', 'strong', 'ul', 'ol', 'li', 'a', 'span', 'div']
    ALLOWED_ATTRIBUTES = {'a': ['href', 'title', 'target'], 'span': ['class']}
    
    @staticmethod
    def sanitize_html(value):
        """Sanitize HTML content"""
        if not isinstance(value, str):
            return value
        
        return bleach.clean(
            value,
            tags=XSSValidator.ALLOWED_TAGS,
            attributes=XSSValidator.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def validate_no_script(value):
        """Block JavaScript injection"""
        if not isinstance(value, str):
            return value
        
        if re.search(r'<script.*?>.*?</script>', value, re.IGNORECASE | re.DOTALL):
            raise ValidationError(_('Script tags are not allowed.'))
        
        if re.search(r'on\w+\s*=', value, re.IGNORECASE):
            raise ValidationError(_('Event handlers are not allowed.'))
        
        if re.search(r'javascript:', value, re.IGNORECASE):
            raise ValidationError(_('JavaScript protocol is not allowed.'))
        
        if re.search(r'data:text/html', value, re.IGNORECASE):
            raise ValidationError(_('Data protocol is not allowed.'))
        
        return value
    
    @staticmethod
    def validate_no_html(value):
        """Remove ALL HTML tags"""
        if not isinstance(value, str):
            return value
        
        cleaned = bleach.clean(value, tags=[], strip=True)
        if cleaned != value:
            raise ValidationError(_('HTML tags are not allowed.'))
        
        return value


# ============================================================
# FILE UPLOAD SECURITY
# ============================================================
class FileValidator:
    """Validate file uploads for security"""
    
    ALLOWED_MIME_TYPES = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    @staticmethod
    def validate_file_type(value):
        """Validate file type using magic numbers"""
        if not value:
            return value
        
        if value.size > FileValidator.MAX_FILE_SIZE:
            raise ValidationError(
                _('File size exceeds 5MB limit.')
            )
        
        ext = os.path.splitext(value.name)[1][1:].lower()
        if ext not in FileValidator.ALLOWED_MIME_TYPES:
            raise ValidationError(
                _('File type .%(ext)s is not allowed. Allowed: %(allowed)s'),
                params={'ext': ext, 'allowed': ', '.join(FileValidator.ALLOWED_MIME_TYPES.keys())}
            )
        
        if magic:
            try:
                file_content = value.read(1024)
                mime_type = magic.from_buffer(file_content, mime=True)
                value.seek(0)
                
                expected_mime = FileValidator.ALLOWED_MIME_TYPES.get(ext)
                if mime_type != expected_mime:
                    raise ValidationError(
                        _('File content does not match file extension. Security risk detected.')
                    )
            except Exception:
                pass
        
        return value


# ============================================================
# COMBINED VALIDATORS
# ============================================================
def validate_safe_input(value):
    """Combined validator for SQL + XSS protection"""
    if not isinstance(value, str):
        return value
    
    SQLInjectionValidator.validate(value)
    value = XSSValidator.validate_no_html(value)
    XSSValidator.validate_no_script(value)
    
    return value


def validate_rich_text(value):
    """For fields that allow HTML"""
    if not isinstance(value, str):
        return value
    
    SQLInjectionValidator.validate(value)
    XSSValidator.validate_no_script(value)
    value = XSSValidator.sanitize_html(value)
    
    return value


def validate_password_strength(value):
    """Ensure strong passwords"""
    if len(value) < 8:
        raise ValidationError(_('Password must be at least 8 characters long.'))
    
    if not any(char.isdigit() for char in value):
        raise ValidationError(_('Password must contain at least one digit.'))
    
    if not any(char.isupper() for char in value):
        raise ValidationError(_('Password must contain at least one uppercase letter.'))
    
    if not any(char.islower() for char in value):
        raise ValidationError(_('Password must contain at least one lowercase letter.'))
    
    if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?' for char in value):
        raise ValidationError(_('Password must contain at least one special character.'))
    
    return value