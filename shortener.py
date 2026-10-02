import shortuuid

def generate_short_code(length: int = 7) -> str:
    return shortuuid.ShortUUID().random(length=length)