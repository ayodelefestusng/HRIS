from django.core.exceptions import ValidationError


# ✅ Valid Nigerian phone prefixes (4-digit only)
VALID_PREFIXES = {
    '0809', '0817', '0818', '0909', '0908',  # 9mobile
    '0701', '0708', '0802', '0808', '0812', '0901', '0902', '0904', '0907', '0912', '0911',  # Airtel
    '0705', '0805', '0807', '0811', '0815', '0905', '0915',  # Glo
    '0804',  # Mtel
    '0703', '0706', '0803', '0806', '0810', '0813', '0814', '0816', '0903', '0906', '0913', '0916', '0704', '0707'  # MTN
}

# 📞 Validator for Nigerian phone prefixes
def validate_nigerian_phone(value):
    if not value.isdigit():
        raise ValidationError("Phone number must contain only digits.")
    if len(value) != 11:
        raise ValidationError("Phone number must be exactly 11 digits.")
    if value[:4] not in VALID_PREFIXES:
        raise ValidationError(f"Phone number must start with a valid Nigerian prefix. Got '{value[:4]}'.")


