// Entity types of the NER model (LiquidAI/LFM2.5-Encoder-350M-PII-Detector), grouped for the rule form
export const PII_ENTITY_GROUPS = [
  { name: 'Identity', types: [
    ['identity.person_name', 'Person name'],
    ['identity.national_id', 'National ID'],
    ['identity.passport', 'Passport'],
    ['identity.drivers_license', "Driver's license"],
    ['identity.date_of_birth', 'Date of birth'],
    ['identity.ssn', 'SSN'],
    ['identity.tax_id', 'Tax ID'],
  ] },
  { name: 'Contact', types: [
    ['contact.email', 'Email'],
    ['contact.phone', 'Phone'],
    ['contact.address', 'Address'],
    ['contact.postal_code', 'Postal code'],
    ['contact.ip_address', 'IP address'],
  ] },
  { name: 'Financial', types: [
    ['financial.credit_card', 'Credit card'],
    ['financial.bank_account', 'Bank account'],
    ['financial.iban', 'IBAN'],
    ['financial.swift_bic', 'SWIFT / BIC'],
    ['financial.crypto_wallet', 'Crypto wallet'],
    ['financial.amount', 'Amount'],
  ] },
  { name: 'Credentials', types: [
    ['credential.password', 'Password'],
    ['credential.api_key', 'API key'],
    ['credential.private_key', 'Private key'],
    ['credential.jwt', 'JWT'],
    ['credential.connection_string', 'Connection string'],
    ['developer.login_credentials', 'Login credentials'],
  ] },
  { name: 'Online & devices', types: [
    ['online.username', 'Username'],
    ['online.url', 'URL'],
    ['device.mac_address', 'MAC address'],
    ['device.imei', 'IMEI'],
    ['developer.device_id', 'Device ID'],
    ['location.gps_coordinates', 'GPS coordinates'],
  ] },
  { name: 'Health & sensitive', types: [
    ['healthcare.condition', 'Medical condition'],
    ['healthcare.medication', 'Medication'],
    ['healthcare.medical_record', 'Medical record'],
    ['healthcare.health_plan_id', 'Health plan ID'],
    ['special.health_status', 'Health status'],
    ['special.religion', 'Religion'],
    ['special.political', 'Political opinion'],
    ['special.orientation', 'Sexual orientation'],
  ] },
  { name: 'Organisation & legal', types: [
    ['org.company_name', 'Company name'],
    ['legal.case_number', 'Case number'],
  ] },
]

export const PII_ENTITY_LABELS = Object.fromEntries(PII_ENTITY_GROUPS.flatMap((group) => group.types))
