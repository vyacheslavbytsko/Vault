from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address
from pathlib import Path
from secrets import token_urlsafe

from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate

from config import get_config

JWT_SECRET_PATH = get_config().data_directory+"/security/jwt/v1/secret.txt"

class JWTSettings:
    def __init__(self):
        self.jwt_issuer = "com.beshence.vault"
        self.jwt_secret = open(JWT_SECRET_PATH, "r").read()

        if len(self.jwt_secret) == 0:
            raise Exception

        self.jwt_lifetime_seconds = 60 * 60 * 24 * 365  # one year
        self.jwt_algorithm = "HS256"


__cached_jwt_settings: JWTSettings = None

def get_jwt_settings() -> JWTSettings:
    global __cached_jwt_settings
    if __cached_jwt_settings is not None:
        return __cached_jwt_settings

    Path(get_config().data_directory+"/security/jwt/v1").mkdir(parents=True, exist_ok=True)
    if not Path(JWT_SECRET_PATH).is_file():
        with open(JWT_SECRET_PATH, "w") as f:
            f.write(token_urlsafe(128))
    __cached_jwt_settings = JWTSettings()
    return __cached_jwt_settings


SSL_ROOT_KEY_PATH = get_config().data_directory+"/security/ssl/v1/rootkey.pem"
SSL_ROOT_CERT_PATH = get_config().data_directory+"/security/ssl/v1/rootcert.pem"
SSL_SERVER_KEY_PATH = get_config().data_directory+"/security/ssl/v1/serverkey.pem"
SSL_SERVER_CERT_PATH = get_config().data_directory+"/security/ssl/v1/servercert.pem"


def generate_ssl_certs_if_needed():
    Path(get_config().data_directory+"/security/ssl/v1").mkdir(parents=True, exist_ok=True)

    # generating root key
    if not Path(SSL_ROOT_KEY_PATH).is_file():
        root_key = ec.generate_private_key(ec.SECP384R1())
        with open(SSL_ROOT_KEY_PATH, "wb") as f:
            f.write(root_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

    def generate_root_cert():
        root_key = load_pem_private_key(open(SSL_ROOT_KEY_PATH, "rb").read(), password=None)
        # TODO: rename everything
        root_subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Company"),
            x509.NameAttribute(NameOID.COMMON_NAME, "PyCA Docs Root CA"),
        ])

        root_cert = (x509.CertificateBuilder()
                     .subject_name(root_subject)
                     .issuer_name(issuer)
                     .public_key(root_key.public_key())
                     .serial_number(x509.random_serial_number())
                     .not_valid_before(datetime.now(timezone.utc))
                     .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365 * 10))
                     .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True)
                     .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True)
                     .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()),
            critical=False)
                     .sign(root_key, hashes.SHA256()))

        with open(SSL_ROOT_CERT_PATH, "wb") as f:
            f.write(root_cert.public_bytes(serialization.Encoding.PEM))

    if not Path(SSL_ROOT_CERT_PATH).is_file():
        generate_root_cert()

    root_cert = load_pem_x509_certificate(open(SSL_ROOT_CERT_PATH, "rb").read())
    if datetime.now(timezone.utc) > root_cert.not_valid_after_utc - timedelta(days=365):
        generate_root_cert()

    if not Path(SSL_SERVER_KEY_PATH).is_file():
        server_key = ec.generate_private_key(ec.SECP384R1())
        with open(SSL_SERVER_KEY_PATH, "wb") as f:
            f.write(server_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

    def generate_server_cert():
        root_key = load_pem_private_key(open(SSL_ROOT_KEY_PATH, "rb").read(), password=None)
        root_cert = load_pem_x509_certificate(open(SSL_ROOT_CERT_PATH, "rb").read())
        server_key = load_pem_private_key(open(SSL_SERVER_KEY_PATH, "rb").read(), password=None)
        server_subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Company"),
        ])
        server_cert = x509.CertificateBuilder().subject_name(
            server_subject
        ).issuer_name(
            root_cert.subject
        ).public_key(
            server_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=10)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(IPv4Address("127.0.0.1"))
            ]),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.ExtendedKeyUsageOID.CLIENT_AUTH,
                x509.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=False,
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                root_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
            ),
            critical=False,
        ).sign(root_key, hashes.SHA256())

        with open(SSL_SERVER_CERT_PATH, "wb") as f:
            f.write(server_cert.public_bytes(serialization.Encoding.PEM))

    if not Path(SSL_SERVER_CERT_PATH).is_file():
        generate_server_cert()

    server_cert = load_pem_x509_certificate(open(SSL_SERVER_CERT_PATH, "rb").read())
    if datetime.now(timezone.utc) > server_cert.not_valid_after_utc - timedelta(days=3):
        generate_server_cert()