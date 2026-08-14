import secrets
import string

characters = string.ascii_letters + string.digits

secret_key = ''.join(
    secrets.choice(characters)
    for _ in range(32)
)

print(secret_key)