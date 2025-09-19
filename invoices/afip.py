"""Utilities for interacting with AFIP web services.

This module provides a minimal integration with AFIP's WSAA service in
order to obtain authentication tokens for the electronic invoicing SOAP
endpoint (``wsfev1``).  The helper is designed to be invoked when the
development server boots so that a fresh token is available once per day.

The implementation relies on OpenSSL being available on the system and
expects the AFIP certificate/key pair to be stored as PEM files.  Paths can
be customised through settings:

``AFIP_CERTIFICATE``
    Path to the signer certificate (default: ``BASE_DIR / "certificado.pem"``).
``AFIP_PRIVATE_KEY``
    Path to the private key (default: ``BASE_DIR / "jdmkey.key"``).
``AFIP_CREDENTIALS_DIR``
    Directory where temporary/login files are stored (default: ``BASE_DIR / "afip"``).
``AFIP_SERVICE``
    AFIP service name.  Defaults to ``"wsfev1"``.
``AFIP_WSAA_URL``
    URL for the WSAA login service.
"""

from __future__ import annotations

import base64
import datetime as dt
import logging
import subprocess
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

LOGGER = logging.getLogger(__name__)


DEFAULT_WSAA_URL = "https://wsaa.afip.gov.ar/ws/services/LoginCms"


@dataclass
class AfipPaths:
    """Convenience container with the paths used for AFIP credentials."""

    certificate: Path
    private_key: Path
    credentials_dir: Path

    @property
    def tra(self) -> Path:
        return self.credentials_dir / "login_ticket_request.xml"

    @property
    def cms(self) -> Path:
        return self.credentials_dir / "login.cms.der"

    @property
    def token(self) -> Path:
        return self.credentials_dir / "token.txt"

    @property
    def sign(self) -> Path:
        return self.credentials_dir / "sign.txt"

    @property
    def ta(self) -> Path:
        return self.credentials_dir / "ta.xml"


def _get_afip_paths() -> AfipPaths:
    """Return the configured AFIP credential paths."""

    certificate = Path(getattr(settings, "AFIP_CERTIFICATE", settings.BASE_DIR / "certificado.pem"))
    private_key = Path(getattr(settings, "AFIP_PRIVATE_KEY", settings.BASE_DIR / "jdmkey.key"))
    credentials_dir = Path(getattr(settings, "AFIP_CREDENTIALS_DIR", settings.BASE_DIR / "afip"))
    return AfipPaths(certificate=certificate, private_key=private_key, credentials_dir=credentials_dir)


def _get_service_name() -> str:
    return getattr(settings, "AFIP_SERVICE", "wsfev1")


def _get_wsaa_url() -> str:
    return getattr(settings, "AFIP_WSAA_URL", DEFAULT_WSAA_URL)


def _build_login_ticket_request(service: str) -> str:
    """Generate the XML login ticket request used by AFIP WSAA."""

    now_utc = timezone.now().astimezone(dt.timezone.utc)
    generation = now_utc - dt.timedelta(minutes=10)
    expiration = now_utc + dt.timedelta(minutes=10)
    unique_id = int(uuid.uuid4().int % 10_000_000_000)

    def _format(ts: dt.datetime) -> str:
        return ts.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    return (
        "<loginTicketRequest version=\"1.0\">\n"
        "  <header>\n"
        f"    <uniqueId>{unique_id}</uniqueId>\n"
        f"    <generationTime>{_format(generation)}</generationTime>\n"
        f"    <expirationTime>{_format(expiration)}</expirationTime>\n"
        "  </header>\n"
        f"  <service>{service}</service>\n"
        "</loginTicketRequest>"
    )


def _ensure_directories(paths: AfipPaths) -> None:
    if not paths.credentials_dir.exists():
        paths.credentials_dir.mkdir(parents=True, exist_ok=True)


def _sign_login_ticket(paths: AfipPaths) -> bytes:
    """Sign the login ticket request using OpenSSL and return CMS bytes."""

    if not paths.certificate.exists():
        raise FileNotFoundError(f"AFIP certificate not found at {paths.certificate}")

    if not paths.private_key.exists():
        raise FileNotFoundError(f"AFIP private key not found at {paths.private_key}")

    subprocess.run(
        [
            "openssl",
            "smime",
            "-sign",
            "-in",
            str(paths.tra),
            "-signer",
            str(paths.certificate),
            "-inkey",
            str(paths.private_key),
            "-out",
            str(paths.cms),
            "-outform",
            "DER",
            "-nodetach",
        ],
        check=True,
    )

    return paths.cms.read_bytes()


def _call_wsaa(cms_der: bytes) -> ET.Element:
    """Call the WSAA login service and return the parsed XML tree."""

    cms_b64 = base64.b64encode(cms_der).decode("ascii")
    envelope = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
  <soapenv:Header/>
  <soapenv:Body>
    <loginCms xmlns=\"http://wsaa.view.sua.dvadac.desein.afip.gov.ar\">
      <in0>{cms_b64}</in0>
    </loginCms>
  </soapenv:Body>
</soapenv:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "loginCms",
    }

    response = requests.post(_get_wsaa_url(), data=envelope.encode("utf-8"), headers=headers, timeout=60)
    response.raise_for_status()

    try:
        return ET.fromstring(response.text)
    except ET.ParseError as exc:  # pragma: no cover - defensive
        raise RuntimeError("WSAA response could not be parsed") from exc


def _extract_login_response(envelope: ET.Element) -> tuple[str, str, str]:
    """Extract token, sign and expiration from the WSAA SOAP envelope."""

    login_return: Optional[ET.Element] = None
    for element in envelope.iter():
        if element.tag.endswith("loginCmsReturn"):
            login_return = element
            break

    if login_return is None or login_return.text is None:
        raise RuntimeError("WSAA response did not contain loginCmsReturn")

    ticket = ET.fromstring(login_return.text)
    token = ticket.findtext(".//token")
    sign = ticket.findtext(".//sign")
    expiration = ticket.findtext(".//expirationTime")

    if not all([token, sign, expiration]):
        raise RuntimeError("WSAA response was missing token information")

    return token, sign, expiration


def _parse_timestamp(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None

    clean = value.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(clean)
    except ValueError:  # pragma: no cover - depends on AFIP format changes
        LOGGER.warning("Unable to parse AFIP timestamp: %s", value)
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)

    return parsed.astimezone(dt.timezone.utc)


def _existing_token_info(paths: AfipPaths) -> tuple[Optional[dt.datetime], Optional[dt.datetime]]:
    if not paths.ta.exists():
        return None, None

    try:
        tree = ET.parse(paths.ta)
    except ET.ParseError:
        LOGGER.warning("Existing AFIP TA file could not be parsed; ignoring")
        return None, None

    generation = _parse_timestamp(tree.findtext(".//generationTime"))
    expiration = _parse_timestamp(tree.findtext(".//expirationTime"))
    return generation, expiration


def _write_credentials(paths: AfipPaths, token: str, sign: str, ticket_xml: str) -> None:
    paths.token.write_text(token, encoding="utf-8")
    paths.sign.write_text(sign, encoding="utf-8")
    paths.ta.write_text(ticket_xml, encoding="utf-8")


def request_wsaa_token(service: Optional[str] = None) -> tuple[str, str, str]:
    """Request a new AFIP WSAA token/sign pair and persist auxiliary files."""

    service = service or _get_service_name()
    paths = _get_afip_paths()
    _ensure_directories(paths)

    tra_xml = _build_login_ticket_request(service)
    paths.tra.write_text(tra_xml, encoding="utf-8")

    cms_der = _sign_login_ticket(paths)
    envelope = _call_wsaa(cms_der)
    token, sign, expiration = _extract_login_response(envelope)

    login_return_xml = envelope.findtext(".//{http://wsaa.view.sua.dvadac.desein.afip.gov.ar}loginCmsReturn")
    if not login_return_xml:
        # The SOAP parsing loop above already ensures we have the ticket in
        # ``token`` and ``sign``.  Persist the serialized ticket nonetheless.
        login_return_xml = ET.tostring(envelope, encoding="unicode")

    _write_credentials(paths, token, sign, login_return_xml)

    LOGGER.info(
        "Generated new AFIP WSAA credentials for service %s (expires %s)",
        service,
        expiration,
    )

    return token, sign, expiration


def refresh_wsaa_token_if_needed(service: Optional[str] = None, *, min_validity: dt.timedelta | None = None) -> bool:
    """Ensure that a WSAA token exists and is still valid.

    Parameters
    ----------
    service:
        Optional AFIP service name. Defaults to ``AFIP_SERVICE``.
    min_validity:
        Optional ``timedelta`` representing how long the token should remain
        valid. If provided, a refresh is triggered whenever the existing token
        expires before ``now + min_validity``.

    Returns
    -------
    bool
        ``True`` if a new token was generated, ``False`` otherwise.
    """

    service = service or _get_service_name()
    paths = _get_afip_paths()
    _ensure_directories(paths)

    generation, expiration = _existing_token_info(paths)
    now = timezone.now().astimezone(dt.timezone.utc)

    if generation and generation.date() == now.date() and expiration and expiration > now:
        LOGGER.debug(
            "AFIP WSAA token for %s already generated today (%s)",
            service,
            generation,
        )
        return False

    if (
        expiration
        and expiration > now
        and min_validity is not None
        and expiration > now + min_validity
    ):
        LOGGER.debug(
            "Existing AFIP WSAA token for %s is valid until %s; skipping refresh",
            service,
            expiration,
        )
        return False

    if expiration and expiration > now and min_validity is None and generation:
        LOGGER.info(
            "Refreshing AFIP WSAA token for %s despite validity because it was generated on %s",
            service,
            generation.date(),
        )

    try:
        request_wsaa_token(service=service)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, requests.RequestException, RuntimeError) as exc:
        LOGGER.error("Unable to refresh AFIP WSAA token: %s", exc)
        return False


def create_invoice_afip(invoice):
    """Stub for sending invoice data to AFIP.

    This function remains as a placeholder for future integration that would
    make use of the generated token and sign to interact with AFIP's billing
    services.
    """

    # TODO: implement real AFIP integration
    return "DUMMY-CODE"


__all__ = [
    "create_invoice_afip",
    "refresh_wsaa_token_if_needed",
    "request_wsaa_token",
]

