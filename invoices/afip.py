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
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Optional, Tuple

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from zeep import Client
from zeep.exceptions import Fault
from zeep.transports import Transport

LOGGER = logging.getLogger(__name__)


DEFAULT_WSAA_URL = "https://wsaa.afip.gov.ar/ws/services/LoginCms"
DEFAULT_WSFE_WSDL = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
DEFAULT_VAT_RATE = Decimal("0.21")
DEFAULT_VAT_CODE = 5  # AlicIva 21%
DEFAULT_DOC_TYPE = 80  # CUIT
DEFAULT_CBTE_TYPE = 6  # Factura B
DEFAULT_POINT_OF_SALE = 1
DEFAULT_CONCEPT = 1  # Productos
DEFAULT_CURRENCY = "PES"


def _get_int_setting(name: str, default: Optional[int] = None, *, required: bool = False) -> int:
    value = getattr(settings, name, default)

    if value is None:
        if required or default is None:
            raise ImproperlyConfigured(f"Missing required setting {name}")
        return default

    try:
        return int(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ImproperlyConfigured(f"Setting {name} must be an integer") from exc


def _get_decimal_setting(name: str, default: Decimal) -> Decimal:
    raw_value = getattr(settings, name, default)

    try:
        return raw_value if isinstance(raw_value, Decimal) else Decimal(str(raw_value))
    except (InvalidOperation, TypeError) as exc:  # pragma: no cover - defensive
        raise ImproperlyConfigured(f"Setting {name} must be a decimal value") from exc


def _get_str_setting(name: str, default: Optional[str] = None, *, required: bool = False) -> str:
    value = getattr(settings, name, default)
    if value in (None, ""):
        if required:
            raise ImproperlyConfigured(f"Missing required setting {name}")
        return ""
    return str(value)


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


def _load_cached_credentials(paths: AfipPaths) -> Tuple[str, str]:
    """Return the cached token/sign pair if available."""

    token = paths.token.read_text(encoding="utf-8").strip() if paths.token.exists() else ""
    sign = paths.sign.read_text(encoding="utf-8").strip() if paths.sign.exists() else ""

    if token and sign:
        return token, sign

    if paths.ta.exists():
        try:
            ticket = ET.parse(paths.ta)
        except ET.ParseError as exc:  # pragma: no cover - defensive
            raise RuntimeError("AFIP TA file could not be parsed") from exc

        token = (ticket.findtext(".//token") or "").strip()
        sign = (ticket.findtext(".//sign") or "").strip()

        if token and sign:
            return token, sign

    raise RuntimeError("AFIP WSAA credentials are not available")


def _ensure_wsaa_credentials(*, min_validity: dt.timedelta | None = dt.timedelta(minutes=5)) -> Tuple[str, str]:
    """Ensure there is a valid WSAA token and return the token/sign pair."""

    service = _get_service_name()
    paths = _get_afip_paths()
    _ensure_directories(paths)

    refresh_wsaa_token_if_needed(service=service, min_validity=min_validity)

    if not paths.ta.exists() or not paths.token.exists() or not paths.sign.exists():
        request_wsaa_token(service=service)

    return _load_cached_credentials(paths)


def _write_credentials(paths: AfipPaths, token: str, sign: str, ticket_xml: str) -> None:
    paths.token.write_text(token, encoding="utf-8")
    paths.sign.write_text(sign, encoding="utf-8")
    paths.ta.write_text(ticket_xml, encoding="utf-8")


def _only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _parse_invoice_number(number: str, *, default_pos: int) -> tuple[int, Optional[int]]:
    if not number:
        return default_pos, None

    cleaned = number.strip()
    match = re.match(r"^(\d{1,5})\s*-\s*(\d{1,8})$", cleaned)
    if match:
        return int(match.group(1)), int(match.group(2))

    digits = _only_digits(cleaned)
    if len(digits) >= 5:
        point_of_sale = int(digits[:4])
        remaining = digits[4:]
        cbte = int(remaining) if remaining else None
        return point_of_sale, cbte

    return default_pos, None


def _format_invoice_number(point_of_sale: int, cbte_number: int) -> str:
    return f"{point_of_sale:04d}-{cbte_number:08d}"


def _sanitize_tax_id(tax_id: str) -> int:
    digits = _only_digits(str(tax_id))
    if not digits:
        raise ValueError("Client tax ID must contain digits")
    return int(digits)


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
    """Emitir un comprobante electrónico ante AFIP usando los datos de la factura."""

    if invoice.client is None:
        raise ValueError("Invoice must be associated with a client to contact AFIP")

    token, sign = _ensure_wsaa_credentials()

    wsdl = _get_str_setting("AFIP_WSFE_WSDL", DEFAULT_WSFE_WSDL) or DEFAULT_WSFE_WSDL
    company_cuit = _get_int_setting("AFIP_CUIT", required=True)
    point_of_sale_default = _get_int_setting("AFIP_POINT_OF_SALE", DEFAULT_POINT_OF_SALE)
    cbte_type = _get_int_setting("AFIP_CBTE_TYPE", DEFAULT_CBTE_TYPE)
    doc_type = _get_int_setting("AFIP_DOC_TYPE", DEFAULT_DOC_TYPE)
    concept = _get_int_setting("AFIP_CONCEPT", DEFAULT_CONCEPT)
    vat_code = _get_int_setting("AFIP_VAT_CODE", DEFAULT_VAT_CODE)
    vat_rate = _get_decimal_setting("AFIP_VAT_RATE", DEFAULT_VAT_RATE)
    currency = _get_str_setting("AFIP_CURRENCY", DEFAULT_CURRENCY) or DEFAULT_CURRENCY

    try:
        client_tax_id = _sanitize_tax_id(invoice.client.tax_id)
    except (AttributeError, ValueError) as exc:
        raise ValueError("Client tax ID is required to request AFIP authorization") from exc

    total_amount = Decimal(invoice.total)
    quantize = Decimal("0.01")

    if vat_rate > 0:
        net_amount = (total_amount / (Decimal("1") + vat_rate)).quantize(quantize, rounding=ROUND_HALF_UP)
        vat_amount = (total_amount - net_amount).quantize(quantize, rounding=ROUND_HALF_UP)
    else:
        net_amount = total_amount.quantize(quantize, rounding=ROUND_HALF_UP)
        vat_amount = Decimal("0.00")

    total_amount = total_amount.quantize(quantize, rounding=ROUND_HALF_UP)

    issue_date = getattr(invoice, "issued_at", None) or timezone.localdate()
    if not isinstance(issue_date, dt.date):
        issue_date = timezone.localdate()
    issue_date_str = issue_date.strftime("%Y%m%d")

    point_of_sale, requested_number = _parse_invoice_number(invoice.number or "", default_pos=point_of_sale_default)

    session = requests.Session()
    timeout = getattr(settings, "AFIP_TIMEOUT", 60)
    transport = Transport(session=session, timeout=timeout)
    client = Client(wsdl, transport=transport)

    auth = {"Token": token, "Sign": sign, "Cuit": company_cuit}

    try:
        if requested_number is None:
            ultimo = client.service.FECompUltimoAutorizado(Auth=auth, PtoVta=point_of_sale, CbteTipo=cbte_type)
            next_number = int(ultimo.CbteNro) + 1
        else:
            next_number = int(requested_number)
    except (AttributeError, Fault, requests.RequestException) as exc:
        raise RuntimeError("Unable to determine next AFIP invoice number") from exc

    detail = {
        "Concepto": concept,
        "DocTipo": doc_type,
        "DocNro": client_tax_id,
        "CbteDesde": next_number,
        "CbteHasta": next_number,
        "CbteFch": issue_date_str,
        "ImpTotal": total_amount,
        "ImpTotConc": Decimal("0.00"),
        "ImpNeto": net_amount,
        "ImpOpEx": Decimal("0.00"),
        "ImpIVA": vat_amount,
        "ImpTrib": Decimal("0.00"),
        "MonId": currency,
        "MonCotiz": Decimal("1.00"),
    }

    if vat_amount > 0:
        detail["Iva"] = [{"Id": vat_code, "BaseImp": net_amount, "Importe": vat_amount}]
    else:
        detail["Iva"] = []

    fe_req = {
        "FeCabReq": {"CantReg": 1, "PtoVta": point_of_sale, "CbteTipo": cbte_type},
        "FeDetReq": {"FECAEDetRequest": [detail]},
    }

    try:
        response = client.service.FECAESolicitar(Auth=auth, FeCAEReq=fe_req)
    except Fault as exc:
        raise RuntimeError(f"AFIP rejected the invoice: {exc}") from exc
    except requests.RequestException as exc:
        raise RuntimeError("Unable to communicate with AFIP WSFE service") from exc

    errors = getattr(response, "Errors", None)
    if errors:
        err_list = getattr(errors, "Err", errors)
        if not isinstance(err_list, list):
            err_list = [err_list]
        message = "; ".join(f"{err.Code}: {err.Msg}" for err in err_list)
        raise RuntimeError(f"AFIP returned errors: {message}")

    det_resp = getattr(response, "FeDetResp", None)
    if not det_resp:
        raise RuntimeError("AFIP response did not include detail information")

    detail_response = getattr(det_resp, "FECAEDetResponse", None)
    if isinstance(detail_response, list):
        detail_response = detail_response[0] if detail_response else None

    if detail_response is None:
        raise RuntimeError("AFIP response was missing FECAEDetResponse data")

    cae = getattr(detail_response, "CAE", None)
    if not cae:
        raise RuntimeError("AFIP response did not include an authorization code")

    invoice.number = _format_invoice_number(point_of_sale, next_number)

    observations = getattr(detail_response, "Observaciones", None)
    if observations:
        obs_list = getattr(observations, "Obs", observations)
        if not isinstance(obs_list, list):
            obs_list = [obs_list]
        messages = "; ".join(f"{obs.Code}: {obs.Msg}" for obs in obs_list)
        LOGGER.warning("AFIP returned observations for invoice %s: %s", invoice.number, messages)

    return cae


__all__ = [
    "create_invoice_afip",
    "refresh_wsaa_token_if_needed",
    "request_wsaa_token",
]

