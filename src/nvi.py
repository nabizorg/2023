import requests
from lxml import etree

TURKISH_ALPHABET: str = "abcçdefgğhıijklmnoöprsştüuvyz"

SOAP_HEADERS = {"Content-Type": "application/soap+xml; charset=utf-8"}
REQUEST_TEMPLATE = b"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <TCKimlikNoDogrula xmlns="http://tckimlik.nvi.gov.tr/WS">
      <TCKimlikNo>%b</TCKimlikNo>
      <Ad>%b</Ad>
      <Soyad>%b</Soyad>
      <DogumYili>%b</DogumYili>
    </TCKimlikNoDogrula>
  </soap12:Body>
</soap12:Envelope>"""


def validate_tckn(tckn: str) -> bool:
    """Validates a TCKN to be in the valid format and for the parity digits to be correct. Does not check if that TCKN actually exists."""
    if len(tckn) != 11:
        return False

    if not tckn.isdigit():
        return False

    digits: list[int] = list(map(int, tckn))

    if sum(digits[:10]) % 10 != digits[10]:
        return False

    first_sum: int = sum(digits[:9:2])
    second_sum: int = sum(digits[1:8:2])

    if (first_sum * 7 + second_sum * 9) % 10 != digits[9]:
        return False

    if (first_sum * 8) % 10 != digits[10]:
        return False

    return True


def verify_tckn(tckn: str, name: str, surname: str, birth_year: str) -> bool:
    resp = requests.post("https://tckimlik.nvi.gov.tr/Service/KPSPublic.asmx", headers=SOAP_HEADERS, data=REQUEST_TEMPLATE % (tckn.encode("utf-8"), name.encode("utf-8"),
                                                                                                                              surname.encode("utf-8"), birth_year.encode("utf-8")))
    if resp.status_code != 200:
        # TODO: Proper logging.
        print("TCKN check API returned non-200 return code!", file=sys.stderr)
        return False

    root = etree.fromstring(resp.content)

    try:
        return root.getchildren()[0].getchildren()[0].getchildren()[0].text == "true"
    except IndexError:
        # TODO: Proper logging.
        print("TCKN check API returned invalid response data.", file=sys.stderr)
        return False

