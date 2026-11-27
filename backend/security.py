import hashlib
import hmac
import re
import secrets

ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'


def verify_password(password, stored):
    try:
        method, iterations, salt, digest = stored.split('$')
        if method != 'pbkdf2_sha256':
            return False
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


# A conservative quarantine signal, not a complete prompt-injection detector.
INJECTION = re.compile(
    r'ignore\s+(?:all\s+)?(?:previous|prior|above|system)\s+(?:instructions|rules|prompts)|'
    r'(?:system|developer)\s*(?:prompt|message)\s*:|'
    r'<\|(?:im_start|system)|(?:reveal|print|exfiltrate)\s+(?:the\s+)?(?:api\s*key|secret|system\s*prompt)|'
    r'(?:give|award|assign)\s+(?:me\s+)?(?:full\s+(?:marks|credit)|100\s*%)', re.I)


def suspicious(text):
    return bool(INJECTION.search(text))
